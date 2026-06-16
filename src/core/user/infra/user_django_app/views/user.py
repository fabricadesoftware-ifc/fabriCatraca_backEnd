from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from src.core.__seedwork__.infra.api_errors import api_error_response
from src.core.control_id.infra.control_id_django_app.models.device import Device
from src.core.control_id.infra.control_id_django_app.services import (
    CardDeviceSyncService,
    CardEnrollmentError,
    CardEnrollmentService,
)

from ..models import User, Visitas
from ..permissions import (
    IsAdminRole,
    IsOperationalRole,
    IsAdminOrGuaritaRole,
)
from ..policies import UserModificationForbidden, UserModificationPolicy
from ..serializers import RoleAwareUserReadSerializer, UserSerializer, VisitasSerializer
from ..services import UserDeviceSyncService, VisitorService
from ..use_cases import (
    CreateUserUseCase,
    CreateVisitorWithCardUseCase,
    DeleteUserUseCase,
    UpdateUserUseCase,
)


@extend_schema(tags=["Users"])
class UserViewSet(viewsets.ModelViewSet):
    queryset = (
        User.objects.all()
        .filter(deleted_at__isnull=True)
        .order_by("id")
        .prefetch_related("usergroup_set", "selected_devices")
    )
    serializer_class = UserSerializer
    filterset_fields = [
        "id",
        "name",
        "registration",
        "user_type_id",
        "app_role",
        "panel_access_only",
        "device_scope",
    ]
    search_fields = ["name", "email", "registration"]
    ordering_fields = ["id", "name", "registration", "user_type_id", "app_role"]
    ordering = ["id"]
    depth = 1

    def get_permissions(self):
        if self.action == "me":
            return [IsAuthenticated()]
        if self.action in ("list", "retrieve"):
            return [IsOperationalRole()]
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsOperationalRole()]
        if self.action in ("enroll_card", "create_with_card"):
            return [IsAdminOrGuaritaRole()]
        return [IsAdminRole()]

    def _policy(self) -> UserModificationPolicy:
        return UserModificationPolicy()

    def _visitor_service(self) -> VisitorService:
        return VisitorService()

    def _user_sync_service(self) -> UserDeviceSyncService:
        return UserDeviceSyncService()

    def _card_enrollment_service(self) -> CardEnrollmentService:
        return CardEnrollmentService()

    def _card_sync_service(self) -> CardDeviceSyncService:
        return CardDeviceSyncService()

    def get_serializer_class(self):  # pyright: ignore[reportIncompatibleMethodOverride]
        if self.action == "me":
            return UserSerializer
        if self.action in ("list", "retrieve"):
            return RoleAwareUserReadSerializer
        return UserSerializer

    def _build_visitor_response(
        self, instance: User, visit: Visitas, reused_existing: bool
    ):
        payload = self.get_serializer(instance).data
        payload["visit"] = VisitasSerializer(
            visit, context={"request": self.request}
        ).data
        payload["reused_existing_user"] = reused_existing
        return payload

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.id = serializer.validated_data.get("registration")

        try:
            self._policy().assert_can_create(request.user, serializer.validated_data)
        except UserModificationForbidden as exc:
            return api_error_response(
                exc.message,
                code="user_modification_forbidden",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        try:
            result = CreateUserUseCase(
                visitor_service=self._visitor_service(),
                sync_service=self._user_sync_service(),
            ).execute(
                serializer,
                request.user,
                raw_data=request.data,
                serializer_factory=self.get_serializer,
            )
        except ValidationError:
            raise
        except Exception as exc:
            return api_error_response(
                "Erro ao sincronizar usuario na catraca.",
                code="user_device_sync_failed",
                details=str(exc),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if result.visit:
            return Response(
                self._build_visitor_response(
                    result.user,
                    result.visit,
                    result.reused_existing_user,
                ),
                status=status.HTTP_201_CREATED,
            )

        return Response(
            self.get_serializer(result.user).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        try:
            self._policy().assert_can_modify(request.user, instance)
        except UserModificationForbidden as exc:
            return api_error_response(
                exc.message,
                code="user_modification_forbidden",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            instance = UpdateUserUseCase(
                sync_service=self._user_sync_service(),
            ).execute(instance, serializer)
        except ValidationError:
            raise
        except Exception as exc:
            return api_error_response(
                "Erro ao sincronizar usuario na catraca.",
                code="user_device_sync_failed",
                details=str(exc),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return Response(self.get_serializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        try:
            self._policy().assert_can_modify(request.user, instance)
        except UserModificationForbidden as exc:
            return api_error_response(
                exc.message,
                code="user_modification_forbidden",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        try:
            DeleteUserUseCase(sync_service=self._user_sync_service()).execute(instance)
        except Exception as exc:
            return api_error_response(
                "Erro ao sincronizar usuario na catraca.",
                code="user_device_sync_failed",
                details=str(exc),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"])
    def sync(self, request):
        return api_error_response(
            "Sincronizacao de usuarios desativada.",
            code="legacy_user_sync_disabled",
            details="Esta funcao nao esta disponivel no momento.",
            status_code=status.HTTP_410_GONE,
        )

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request):
        if not request.user.is_authenticated:
            return Response(
                {"error": "Usuario nao autenticado"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], permission_classes=[IsAdminOrGuaritaRole])
    def enroll_card(self, request):
        """
        Executa remote_enroll para capturar valor de cartao.
        Nao cria usuario nem salva o cartao.
        Retorna o valor capturado da catraca.
        """
        enrollment_device_id: int = request.data.get("enrollment_device_id")
        if not enrollment_device_id:
            return api_error_response(
                "E necessario especificar uma catraca para captura do cartao",
                code="card_enrollment_device_required",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            device: Device = Device.objects.get(id=enrollment_device_id)
        except Device.DoesNotExist:
            return api_error_response(
                f"Catraca com ID {enrollment_device_id} nao encontrada",
                code="device_not_found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        try:
            captured_value = self._card_enrollment_service().capture_card(
                device,
                user_id=0,
            )
        except CardEnrollmentError as exc:
            return api_error_response(
                exc.message,
                code=exc.code,
                details=exc.details,
                status_code=exc.status_code,
            )

        return Response(
            {
                "device_id": device.pk,
                "device_name": device.name,
                "card_value": captured_value,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], permission_classes=[IsAdminOrGuaritaRole])
    def create_with_card(self, request):
        """
        Cria um usuario visitante e seu cartao em uma unica operacao.
        Fluxo:
        1. se card_value vier no payload, usa diretamente; caso contrario,
           faz remote_enroll na catraca para capturar
        2. salva o usuario
        3. salva o cartao vinculado
        """
        enrollment_device_id = request.data.get("enrollment_device_id")
        captured_value = request.data.get("card_value")

        if not enrollment_device_id:
            return api_error_response(
                "E necessario especificar uma catraca para captura do cartao",
                code="card_enrollment_device_required",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            enrollment_device = Device.objects.get(id=enrollment_device_id)
        except Device.DoesNotExist:
            return api_error_response(
                f"Catraca com ID {enrollment_device_id} nao encontrada",
                code="device_not_found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 1. Se nao veio card_value, faz remote enroll para capturar
        if not captured_value:
            try:
                captured_value = self._card_enrollment_service().capture_card(
                    enrollment_device,
                    user_id=0,
                )
            except CardEnrollmentError as exc:
                return api_error_response(
                    exc.message,
                    code=exc.code,
                    details=exc.details,
                    status_code=exc.status_code,
                )

        try:
            captured_value = int(captured_value)
        except (TypeError, ValueError):
            return api_error_response(
                "Valor do cartao invalido.",
                code="invalid_card_value",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 2. Cria o usuario (remove enrollment_device_id do data)
        user_data = {
            k: v
            for k, v in request.data.items()
            if k not in ("enrollment_device_id", "card_value")
        }
        # Garante que e visitante
        user_data["user_type_id"] = 1

        serializer = self.get_serializer(data=user_data)
        serializer.is_valid(raise_exception=True)

        try:
            result = CreateVisitorWithCardUseCase(
                visitor_service=self._visitor_service(),
                user_sync_service=self._user_sync_service(),
                card_sync_service=self._card_sync_service(),
            ).execute(
                serializer,
                request.user,
                raw_data=user_data,
                serializer_factory=self.get_serializer,
                captured_value=captured_value,
            )
        except ValidationError:
            raise
        except Exception as exc:
            return api_error_response(
                "Erro ao sincronizar usuario e cartao na catraca.",
                code="visitor_card_sync_failed",
                details=str(exc),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "user": self.get_serializer(result.user).data,
                "card": {"id": result.card.id, "value": result.card.value},
                "visit": VisitasSerializer(
                    result.visit,
                    context={"request": request},
                ).data,
                "reused_existing_user": result.reused_existing_user,
            },
            status=status.HTTP_201_CREATED,
        )
