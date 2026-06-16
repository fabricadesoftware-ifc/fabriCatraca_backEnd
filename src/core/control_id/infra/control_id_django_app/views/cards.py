from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from src.core.__seedwork__.infra.api_errors import api_error_response
from src.core.control_id.infra.control_id_django_app.models.cards import Card
from src.core.control_id.infra.control_id_django_app.models.device import Device
from src.core.control_id.infra.control_id_django_app.serializers.cards import (
    CardSerializer,
)
from src.core.control_id.infra.control_id_django_app.services import (
    CardDeviceSyncService,
    CardEnrollmentError,
    CardEnrollmentService,
)
from src.core.control_id.infra.control_id_django_app.use_cases import (
    CardOperationError,
    CreateCardUseCase,
    DeleteCardUseCase,
    UpdateCardUseCase,
)
from src.core.user.infra.user_django_app.models import User


@extend_schema(tags=["Cards"])
class CardViewSet(viewsets.ModelViewSet):
    queryset = Card.objects.all()
    serializer_class = CardSerializer
    filterset_fields = ["id", "user", "value"]
    search_fields = ["value", "user__name", "user__id", "user__registration"]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Compatibilidade com clientes que ainda enviam ?user_id=<id>
        user_id = self.request.query_params.get("user_id")
        if user_id not in (None, ""):
            queryset = queryset.filter(user_id=user_id)

        return queryset

    def _card_enrollment_service(self) -> CardEnrollmentService:
        return CardEnrollmentService()

    def _card_sync_service(self) -> CardDeviceSyncService:
        return CardDeviceSyncService()

    def create(self, request, *args, **kwargs):
        """
        Cria um cartao por captura remota na catraca.

        Fluxo:
        1. valida user_id + enrollment_device_id
        2. executa remote_enroll na catraca escolhida
        3. salva no banco com o valor retornado
        4. replica para as demais catracas ativas
        """
        enrollment_device_id = request.data.get("enrollment_device_id")
        if not enrollment_device_id:
            return api_error_response(
                "E necessario especificar uma catraca para cadastro (enrollment_device_id)",
                code="card_enrollment_device_required",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user_id = (
            request.data.get("user_id")
            or request.query_params.get("user_id")
            or request.data.get("user")
        )
        if not user_id:
            return api_error_response(
                "Usuario (user_id) e obrigatorio",
                code="card_user_required",
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

        try:
            user = User.objects.get(id=int(user_id))
        except (TypeError, ValueError):
            return api_error_response(
                "Usuario (user_id) invalido",
                code="invalid_user_id",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except User.DoesNotExist:
            return api_error_response(
                f"Usuario com ID {user_id} nao encontrado",
                code="user_not_found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(
            data={
                "user_id": user.id,
                "enrollment_device_id": enrollment_device.id,
            }
        )
        serializer.is_valid(raise_exception=True)

        try:
            result = CreateCardUseCase(
                enrollment_service=self._card_enrollment_service(),
                card_sync_service=self._card_sync_service(),
            ).execute(
                serializer,
                user=user,
                enrollment_device=enrollment_device,
            )
        except ValidationError:
            raise
        except CardEnrollmentError as exc:
            return api_error_response(
                exc.message,
                code=exc.code,
                details=exc.details,
                status_code=exc.status_code,
            )
        except CardOperationError as exc:
            return api_error_response(
                exc.message,
                code=exc.code,
                details=exc.details,
                status_code=exc.status_code,
            )
        except Exception as exc:
            return api_error_response(
                "Erro interno no servidor ao processar cartao",
                code="card_processing_failed",
                details=str(exc),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            self.get_serializer(result.card).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            result = UpdateCardUseCase(
                card_sync_service=self._card_sync_service(),
            ).execute(serializer)
        except ValidationError:
            raise
        except Exception as exc:
            return api_error_response(
                "Erro ao atualizar cartao na catraca.",
                code="card_sync_failed",
                details=str(exc),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return Response(self.get_serializer(result.card).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        try:
            DeleteCardUseCase(card_sync_service=self._card_sync_service()).execute(
                instance
            )
        except Exception as exc:
            return api_error_response(
                "Erro ao deletar cartao da catraca.",
                code="card_sync_failed",
                details=str(exc),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)
