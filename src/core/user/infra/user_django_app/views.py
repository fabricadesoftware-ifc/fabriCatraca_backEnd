import logging
from typing import cast

import requests
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from src.core.__seedwork__.infra import ControlIDSyncMixin
from src.core.__seedwork__.infra.types.catraca_sync import RemoteEnrollCardResponse
from src.core.control_Id.infra.control_id_django_app.models.device import Device

from .models import User
from .permissions import (
    IsAdminRole,
    IsOperationalRole,
    IsAdminOrGuaritaRole,
    IsAdminOrSisaeRole,
)
from .serializers import RoleAwareUserReadSerializer, UserSerializer

logger = logging.getLogger(__name__)


@extend_schema(tags=["Users"])
class UserViewSet(ControlIDSyncMixin, viewsets.ModelViewSet):
    queryset = (
        User.objects.all()
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
            return [IsAdminOrGuaritaRole(), IsAdminOrSisaeRole()]
        if self.action in ("enroll_card", "create_with_card"):
            return [IsAdminOrGuaritaRole(), IsAdminOrSisaeRole()]
        return [IsAdminRole()]

    def _is_visitor(self, user):
        return user.user_type_id == 1

    def _ensure_can_modify_user(self, request, instance):
        """Non-admin users can only create/edit/delete visitors (user_type_id=1)."""
        if (
            not request.user.is_superuser
            and request.user.effective_app_role != User.AppRole.ADMIN
        ):
            if not self._is_visitor(instance):
                return Response(
                    {
                        "error": "Apenas administradores podem modificar usuarios nao-visitantes."
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
        return None

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

    def _get_active_target_devices(self, user: User):
        return list(user.get_target_devices(include_inactive=False))

    @staticmethod
    def _is_device_admin_user(user: User) -> bool:
        return bool(user.is_staff or user.is_superuser)

    def _set_user_admin_on_device(self, device, user_id: int):
        self.set_device(device)
        sess = self.login()
        payload_row = {"user_id": user_id, "role": 1}

        r_create = requests.post(
            self.get_url(f"create_objects.fcgi?session={sess}"),
            json={"object": "user_roles", "values": [payload_row]},
            timeout=30,
        )
        if r_create.status_code == 200:
            return

        r_mod = requests.post(
            self.get_url(f"modify_objects.fcgi?session={sess}"),
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
                f"Erro ao criar usuario na catraca {device.name}: {response.data}"
            )

        if instance.pin:
            pin_resp = self.create_objects(
                "pins",
                [{"user_id": instance.id, "value": instance.pin}],
            )
            if pin_resp.status_code != status.HTTP_201_CREATED:
                logger.warning(
                    "Falha ao criar PIN na catraca %s: %s", device.name, pin_resp.data
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
                f"Erro ao atualizar usuario na catraca {device.name}: {response.data}"
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
                f"Erro ao deletar usuario da catraca {device.name}: {response.data}"
            )

    def create(self, request, *args, **kwargs):
        if (
            not request.user.is_superuser
            and request.user.effective_app_role != User.AppRole.ADMIN
        ):
            if request.data.get("user_type_id") != 1:
                return Response(
                    {
                        "error": "Apenas administradores podem criar usuarios nao-visitantes."
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.id = serializer.validated_data.get("registration")

        with transaction.atomic():
            instance = serializer.save()
            self._normalize_user_type(instance)

            if not instance.panel_access_only:
                devices = self._get_active_target_devices(instance)
                try:
                    for device in devices:
                        self._create_user_in_device(device, instance)
                except Exception as exc:
                    instance.delete()
                    return Response(
                        {"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST
                    )

        return Response(
            self.get_serializer(instance).data, status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        guard = self._ensure_can_modify_user(request, instance)
        if guard is not None:
            return guard
        previous_panel_access_only = instance.panel_access_only
        previous_device_admin = self._is_device_admin_user(instance)
        previous_devices = self._get_active_target_devices(instance)
        previous_device_ids = {device.id for device in previous_devices}
        previous_device_map = {device.id: device for device in previous_devices}
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            instance = serializer.save()
            self._normalize_user_type(instance)

            current_devices = self._get_active_target_devices(instance)
            current_device_ids = {device.id for device in current_devices}
            current_device_map = {device.id: device for device in current_devices}

            try:
                removed_ids = previous_device_ids - current_device_ids
                added_ids = current_device_ids - previous_device_ids
                common_ids = previous_device_ids & current_device_ids

                if previous_panel_access_only and instance.panel_access_only:
                    removed_ids = set()
                    added_ids = set()
                    common_ids = set()
                elif previous_panel_access_only and not instance.panel_access_only:
                    removed_ids = set()
                    added_ids = current_device_ids
                    common_ids = set()
                elif not previous_panel_access_only and instance.panel_access_only:
                    removed_ids = previous_device_ids
                    added_ids = set()
                    common_ids = set()

                for device_id in removed_ids:
                    self._delete_user_from_device(
                        previous_device_map[device_id], instance
                    )

                for device_id in added_ids:
                    self._create_user_in_device(current_device_map[device_id], instance)

                for device_id in common_ids:
                    self._update_user_in_device(
                        current_device_map[device_id],
                        instance,
                        previous_device_admin=previous_device_admin,
                    )
            except Exception as exc:
                return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(self.get_serializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        guard = self._ensure_can_modify_user(request, instance)
        if guard is not None:
            return guard

        with transaction.atomic():
            instance.useraccessrule_set.all().delete()
            instance.usergroup_set.all().delete()
            instance.templates.all().delete()
            instance.cards.all().delete()
            instance.groups.clear()
            instance.user_permissions.clear()

            from src.core.control_Id.infra.control_id_django_app.models.access_logs import (
                AccessLogs,
            )

            AccessLogs.objects.filter(user=instance).update(user=None)

            if not instance.panel_access_only:
                for device in self._get_active_target_devices(instance):
                    try:
                        self._delete_user_from_device(device, instance)
                    except Exception as exc:
                        return Response(
                            {"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST
                        )

            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"])
    def sync(self, request):
        try:
            with transaction.atomic():
                devices = Device.objects.filter(is_active=True)

                for device in devices:
                    self.set_device(device)
                    catraca_objects = self.load_objects(
                        "users",
                        fields=["id", "name", "registration", "user_type_id"],
                        order_by=["id"],
                    )

                    for data in catraca_objects:
                        raw_type = data.get("user_type_id")

                        try:
                            existing_user = User.objects.get(id=data["id"])
                            user_type = existing_user.user_type_id
                        except User.DoesNotExist:
                            user_type = (
                                raw_type if raw_type and int(raw_type) == 1 else None
                            )

                        User.objects.update_or_create(
                            id=data["id"],
                            defaults={
                                "name": data["name"],
                                "registration": data.get("registration", ""),
                                "user_type_id": user_type,
                            },
                        )

                return Response(
                    {
                        "success": True,
                        "message": f"Sincronizados usuarios de {len(devices)} catraca(s)",
                    }
                )
        except Exception as exc:
            return Response(
                {"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
            return Response(
                {
                    "error": "E necessario especificar uma catraca para captura do cartao"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            device: Device = Device.objects.get(id=enrollment_device_id)
        except Device.DoesNotExist:
            return Response(
                {"error": f"Catraca com ID {enrollment_device_id} nao encontrada"},
                status=status.HTTP_404_NOT_FOUND,
            )

        self.set_device(device)
        response = cast(
            Response,
            self.remote_enroll(
                user_id=0,
                type="card",
                save=False,
                sync=True,
            ),
        )

        if response.status_code != status.HTTP_201_CREATED:
            return response

        card_data = cast(RemoteEnrollCardResponse, response.data)
        captured_value: int = card_data.get("card_value")
        if not captured_value:
            return Response(
                {
                    "error": "Catraca nao retornou o valor do cartao",
                    "details": card_data,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
            return Response(
                {
                    "error": "E necessario especificar uma catraca para captura do cartao"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            enrollment_device = Device.objects.get(id=enrollment_device_id)
        except Device.DoesNotExist:
            return Response(
                {"error": f"Catraca com ID {enrollment_device_id} nao encontrada"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 1. Se nao veio card_value, faz remote enroll para capturar
        if not captured_value:
            self.set_device(enrollment_device)
            response = cast(
                Response,
                self.remote_enroll(user_id=0, type="card", save=False, sync=True),
            )

            if response.status_code != status.HTTP_201_CREATED:
                return response

            captured_value = cast(RemoteEnrollCardResponse, response.data).get(
                "card_value"
            )
            if not captured_value:
                return Response(
                    {"error": "Catraca nao retornou o valor do cartao"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        # 2. Cria o usuario (remove enrollment_device_id do data)
        user_data = {
            k: v for k, v in request.data.items() if k != "enrollment_device_id"
        }
        # Garante que e visitante
        user_data["user_type_id"] = 1

        serializer = self.get_serializer(data=user_data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            instance = serializer.save()
            self._normalize_user_type(instance)

            # 3. Salva o cartao no banco
            from src.core.control_Id.infra.control_id_django_app.models import Card

            card = Card.objects.create(user=instance, value=str(captured_value))

            # 4. Replica usuario para catracas alvo
            if not instance.panel_access_only:
                devices = self._get_active_target_devices(instance)
                try:
                    for device in devices:
                        self._create_user_in_device(device, instance)

                        # Cria cartao na catraca
                        self.set_device(device)
                        self.create_objects(
                            "cards",
                            [
                                {
                                    "id": card.id,
                                    "user_id": instance.id,
                                    "value": int(captured_value),
                                }
                            ],
                        )
                except Exception as exc:
                    instance.delete()
                    return Response(
                        {"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST
                    )

        return Response(
            {
                "user": self.get_serializer(instance).data,
                "card": {"id": card.id, "value": card.value},
            },
            status=status.HTTP_201_CREATED,
        )
