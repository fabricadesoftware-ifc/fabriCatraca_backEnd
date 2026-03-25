from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
import logging
import requests
from .models import User
from .serializers import RoleAwareUserReadSerializer, UserSerializer
from src.core.__seedwork__.infra import ControlIDSyncMixin
from src.core.control_Id.infra.control_id_django_app.models.device import Device
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated

from .permissions import IsAdminRole, IsOperationalRole

logger = logging.getLogger(__name__)


@extend_schema(tags=["Users"])
class UserViewSet(ControlIDSyncMixin, viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("id").prefetch_related("usergroup_set")
    serializer_class = UserSerializer
    filterset_fields = [
        "id",
        "name",
        "registration",
        "user_type_id",
        "app_role",
        "panel_access_only",
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
        return [IsAdminRole()]

    def get_serializer_class(self):  # pyright: ignore[reportIncompatibleMethodOverride]
        if self.action == "me":
            return UserSerializer
        if self.action in ("list", "retrieve"):
            return RoleAwareUserReadSerializer
        return UserSerializer

    def _normalize_user_type(self, instance):
        if instance.user_type_id in (0, "0"):
            instance.user_type_id = None
            instance.save(update_fields=["user_type_id"])

    def _build_user_payload(self, instance):
        payload = {
            "id": instance.id,
            "name": instance.name,
            "registration": instance.registration or "",
        }
        if instance.user_type_id is not None:
            payload["user_type_id"] = instance.user_type_id
        return payload

    @staticmethod
    def _is_device_admin_user(user: User) -> bool:
        """Admin no equipamento (user_roles.role=1): alinhado ao easy_setup e objetos.txt."""
        return bool(user.is_staff or user.is_superuser)

    def _set_user_admin_on_device(self, device, user_id: int):
        """
        Garante user_roles na catraca (user_id + role=1).
        create_objects quando a linha não existe; modify_objects quando já existe
        (evita modify só com {role:1}, que não bate com a API em vários firmwares).
        """
        self.set_device(device)
        sess = self.login()
        base_url = self.get_url
        payload_row = {"user_id": user_id, "role": 1}

        r_create = requests.post(
            base_url(f"create_objects.fcgi?session={sess}"),
            json={"object": "user_roles", "values": [payload_row]},
            timeout=30,
        )
        if r_create.status_code == 200:
            return

        r_mod = requests.post(
            base_url(f"modify_objects.fcgi?session={sess}"),
            json={
                "object": "user_roles",
                "values": payload_row,
                "where": {"user_roles": {"user_id": user_id}},
            },
            timeout=30,
        )
        if r_mod.status_code != 200:
            raise RuntimeError(
                f"Erro ao definir administrador na catraca {device.name}: "
                f"create HTTP {r_create.status_code} {r_create.text[:300]!r} | "
                f"modify HTTP {r_mod.status_code} {r_mod.text[:300]!r}"
            )

    def _create_user_in_device(self, device, instance):
        self.set_device(device)
        response = self.create_objects("users", [self._build_user_payload(instance)])
        if response.status_code != status.HTTP_201_CREATED:
            raise RuntimeError(
                f"Erro ao criar usuário na catraca {device.name}: {response.data}"
            )

        if instance.pin:
            pin_resp = self.create_objects(
                "pins",
                [{"user_id": instance.id, "value": instance.pin}],
            )
            if pin_resp.status_code != status.HTTP_201_CREATED:
                logger.warning(
                    "Falha ao criar PIN na catraca %s: %s",
                    device.name,
                    pin_resp.data,
                )

        if self._is_device_admin_user(instance):
            self._set_user_admin_on_device(device, instance.id)

    def _update_user_in_device(self, device, instance, previous_device_admin=False):
        self.set_device(device)
        response = self.update_objects(
            "users",
            {
                "name": instance.name,
                "registration": instance.registration or "",
                **(
                    {"user_type_id": instance.user_type_id}
                    if instance.user_type_id is not None
                    else {}
                ),
            },
            {"users": {"id": instance.id}},
        )
        if response.status_code != status.HTTP_200_OK:
            raise RuntimeError(
                f"Erro ao atualizar usuário na catraca {device.name}: {response.data}"
            )

        if instance.pin:
            pin_resp = self.update_objects(
                "pins",
                {"value": instance.pin},
                {"pins": {"user_id": instance.id}},
            )
            if pin_resp.status_code != status.HTTP_200_OK:
                self.create_objects(
                    "pins",
                    [{"user_id": instance.id, "value": instance.pin}],
                )

        current_admin = self._is_device_admin_user(instance)
        if current_admin:
            self._set_user_admin_on_device(device, instance.id)
        elif previous_device_admin:
            role_resp = self.destroy_objects(
                "user_roles",
                {"user_roles": {"user_id": instance.id}},
            )
            if role_resp.status_code not in (
                status.HTTP_204_NO_CONTENT,
                status.HTTP_200_OK,
            ):
                raise RuntimeError(
                    f"Erro ao remover papel administrativo na catraca {device.name}: {role_resp.data}"
                )

    def _delete_user_from_device(self, device, instance):
        self.set_device(device)
        self.destroy_objects("user_roles", {"user_roles": {"user_id": instance.id}})
        self.destroy_objects("pins", {"pins": {"user_id": instance.id}})
        response = self.destroy_objects("users", {"users": {"id": instance.id}})
        if response.status_code != status.HTTP_204_NO_CONTENT:
            raise RuntimeError(
                f"Erro ao deletar usuário da catraca {device.name}: {response.data}"
            )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.id = serializer.validated_data.get("registration")

        with transaction.atomic():
            instance = serializer.save()
            self._normalize_user_type(instance)

            if not instance.panel_access_only:
                devices = Device.objects.filter(is_active=True)
                try:
                    for device in devices:
                        self._create_user_in_device(device, instance)
                except Exception as exc:
                    instance.delete()
                    return Response(
                        {"error": str(exc)},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        previous_panel_access_only = instance.panel_access_only
        previous_device_admin = self._is_device_admin_user(instance)
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            instance = serializer.save()
            self._normalize_user_type(instance)

            devices = Device.objects.filter(is_active=True)
            try:
                for device in devices:
                    if previous_panel_access_only and instance.panel_access_only:
                        continue
                    if previous_panel_access_only and not instance.panel_access_only:
                        self._create_user_in_device(device, instance)
                        continue
                    if not previous_panel_access_only and instance.panel_access_only:
                        self._delete_user_from_device(device, instance)
                        continue
                    self._update_user_in_device(
                        device,
                        instance,
                        previous_device_admin=previous_device_admin,
                    )
            except Exception as exc:
                return Response(
                    {"error": str(exc)},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        with transaction.atomic():
            # Primeiro remove todas as relações
            instance.useraccessrule_set.all().delete()  # Regras de acesso
            instance.usergroup_set.all().delete()  # Grupos de usuário
            instance.templates.all().delete()  # Templates
            instance.cards.all().delete()  # Cartões

            # Remove relações ManyToMany
            instance.groups.clear()  # Grupos do Django
            instance.user_permissions.clear()  # Permissões do Django

            # Define o user como NULL nos logs de acesso (já que usa DO_NOTHING)
            from src.core.control_Id.infra.control_id_django_app.models.access_logs import (
                AccessLogs,
            )

            AccessLogs.objects.filter(user=instance).update(user=None)

            if not instance.panel_access_only:
                devices = Device.objects.filter(is_active=True)

                for device in devices:
                    try:
                        self._delete_user_from_device(device, instance)
                    except Exception as exc:
                        return Response(
                            {"error": str(exc)},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

            # Se removeu de todas as catracas, remove do banco
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"])
    def sync(self, request):
        """Sincroniza usuários de todas as catracas ativas"""
        try:
            with transaction.atomic():
                # Sincroniza com todas as catracas ativas
                devices = Device.objects.filter(is_active=True)

                for device in devices:
                    self.set_device(device)
                    catraca_objects = self.load_objects(
                        "users",
                        fields=["id", "name", "registration", "user_type_id"],
                        order_by=["id"],
                    )

                    # Atualiza/cria usuários no banco
                    for data in catraca_objects:
                        # A catraca Control iD retorna user_type_id para todos
                        # os usuários. Precisamos verificar se o usuário JÁ existe
                        # no banco antes de sobrescrever o tipo.
                        raw_type = data.get("user_type_id")

                        try:
                            existing_user = User.objects.get(id=data["id"])
                            # Usuário já existe: mantém o user_type_id do banco
                            # (a fonte de verdade para tipo é o nosso sistema)
                            user_type = existing_user.user_type_id
                        except User.DoesNotExist:
                            # Usuário novo vindo da catraca: só marca como
                            # visitante se a catraca disser explicitamente
                            user_type = (
                                raw_type if raw_type and int(raw_type) == 1 else None
                            )

                        user, created = User.objects.update_or_create(
                            id=data["id"],
                            defaults={
                                "name": data["name"],
                                "registration": data.get("registration", ""),
                                "user_type_id": user_type,
                            },
                        )
                        # Adiciona a relação com a catraca

                return Response(
                    {
                        "success": True,
                        "message": f"Sincronizados usuários de {len(devices)} catraca(s)",
                    }
                )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Retorna os dados do usuário autenticado"""
        if not request.user.is_authenticated:
            return Response(
                {"error": "Usuário não autenticado"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
