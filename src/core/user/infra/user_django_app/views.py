from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
import logging
from .models import User
from .serializers import UserSerializer
from src.core.__seedwork__.infra import ControlIDSyncMixin
from src.core.control_Id.infra.control_id_django_app.models.device import Device
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated

from .permissions import IsAdminRole, IsAdminOrSisaeRole

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
            return [IsAdminOrSisaeRole()]
        return [IsAdminRole()]

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

        if instance.is_staff:
            role_resp = self.create_objects(
                "user_roles",
                [{"user_id": instance.id, "role": 1}],
            )
            if role_resp.status_code != status.HTTP_201_CREATED:
                raise RuntimeError(
                    f"Erro ao definir usuario administrador na catraca {device.name}: {role_resp.data}"
                )

    def _update_user_in_device(self, device, instance):
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

        if instance.is_staff:
            role_resp = self.update_objects(
                "user_roles",
                {"role": 1},
                {"user_roles": {"user_id": instance.id}},
            )
            if role_resp.status_code != status.HTTP_200_OK:
                role_resp = self.create_objects(
                    "user_roles",
                    [{"user_id": instance.id, "role": 1}],
                )
                if role_resp.status_code != status.HTTP_201_CREATED:
                    raise RuntimeError(
                        f"Erro ao atualizar papel administrativo na catraca {device.name}: {role_resp.data}"
                    )
        else:
            self.destroy_objects("user_roles", {"user_roles": {"user_id": instance.id}})

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
                    self._update_user_in_device(device, instance)
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
