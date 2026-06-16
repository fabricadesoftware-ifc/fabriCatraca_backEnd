from __future__ import annotations

import logging
from dataclasses import dataclass

from rest_framework import status

from src.core.__seedwork__.infra.catraca_sync import CatracaSyncError
from src.core.control_id.infra.control_id_django_app.gateways import ControlIDGateway
from src.core.control_id.infra.control_id_django_app.models.device import Device
from src.core.user.infra.user_django_app.mappers import UserControlIDMapper
from src.core.user.infra.user_django_app.models import User

logger = logging.getLogger(__name__)


class UserDeviceSyncError(RuntimeError):
    pass


@dataclass(frozen=True)
class UserDeviceSyncSnapshot:
    panel_access_only: bool
    device_admin: bool
    devices: tuple[Device, ...]

    @property
    def device_ids(self) -> set[int]:
        return {device.id for device in self.devices}

    @property
    def device_map(self) -> dict[int, Device]:
        return {device.id: device for device in self.devices}


class UserDeviceSyncService:
    def __init__(
        self,
        gateway: ControlIDGateway | None = None,
        mapper: type[UserControlIDMapper] = UserControlIDMapper,
    ) -> None:
        self.gateway = gateway or ControlIDGateway()
        self.mapper = mapper

    def snapshot(self, user: User) -> UserDeviceSyncSnapshot:
        return UserDeviceSyncSnapshot(
            panel_access_only=user.panel_access_only,
            device_admin=self.is_device_admin_user(user),
            devices=tuple(self.get_active_target_devices(user)),
        )

    def get_active_target_devices(self, user: User) -> list[Device]:
        return list(user.get_target_devices(include_inactive=False))

    @staticmethod
    def is_device_admin_user(user: User) -> bool:
        return bool(user.is_staff or user.is_superuser)

    @staticmethod
    def is_duplicate_user_error(error_or_response) -> bool:
        data = getattr(error_or_response, "data", None)
        if isinstance(data, dict):
            raw_text = " ".join(str(value) for value in data.values())
        else:
            raw_text = str(data or error_or_response)

        normalized = raw_text.lower()
        return "unique constraint failed" in normalized and "users.id" in normalized

    def create_or_upsert_user(self, user: User, *, created_new_user: bool) -> None:
        if user.panel_access_only:
            return

        for device in self.get_active_target_devices(user):
            if created_new_user:
                self.create_user_in_device(device, user)
            else:
                self.upsert_user_in_device(device, user)

    def apply_update(
        self,
        user: User,
        previous: UserDeviceSyncSnapshot,
        current: UserDeviceSyncSnapshot | None = None,
    ) -> None:
        current = current or self.snapshot(user)

        removed_ids = previous.device_ids - current.device_ids
        added_ids = current.device_ids - previous.device_ids
        common_ids = previous.device_ids & current.device_ids

        if previous.panel_access_only and user.panel_access_only:
            removed_ids = set()
            added_ids = set()
            common_ids = set()
        elif previous.panel_access_only and not user.panel_access_only:
            removed_ids = set()
            added_ids = current.device_ids
            common_ids = set()
        elif not previous.panel_access_only and user.panel_access_only:
            removed_ids = previous.device_ids
            added_ids = set()
            common_ids = set()

        for device_id in removed_ids:
            self.delete_user_from_device(previous.device_map[device_id], user)

        for device_id in added_ids:
            self.create_user_in_device(current.device_map[device_id], user)

        for device_id in common_ids:
            self.update_user_in_device(
                current.device_map[device_id],
                user,
                previous_device_admin=previous.device_admin,
            )

    def create_user_in_device(self, device: Device, user: User) -> None:
        self.gateway.set_device(device)
        try:
            response = self.gateway.create_objects(
                "users",
                [self.mapper.to_user_payload(user)],
                device_ids=[device.id],
            )
        except CatracaSyncError as exc:
            if self.is_duplicate_user_error(exc):
                self.update_user_in_device(
                    device,
                    user,
                    previous_device_admin=self.is_device_admin_user(user),
                )
                return
            raise UserDeviceSyncError(
                f"Erro ao criar usuario na catraca {device.name}: {exc}"
            ) from exc

        if response.status_code == status.HTTP_201_CREATED:
            self.sync_pin(device, user, allow_create=True)

            if self.is_device_admin_user(user):
                self.set_user_admin_on_device(device, user.id)
            return

        if self.is_duplicate_user_error(response):
            self.update_user_in_device(
                device,
                user,
                previous_device_admin=self.is_device_admin_user(user),
            )
            return

        raise UserDeviceSyncError(
            f"Erro ao criar usuario na catraca {device.name}: {response.data}"
        )

    def upsert_user_in_device(
        self,
        device: Device,
        user: User,
        previous_device_admin: bool = False,
    ) -> None:
        try:
            self.update_user_in_device(
                device,
                user,
                previous_device_admin=previous_device_admin,
            )
        except Exception:
            self.create_user_in_device(device, user)

    def update_user_in_device(
        self,
        device: Device,
        user: User,
        previous_device_admin: bool = False,
    ) -> None:
        self.gateway.set_device(device)
        response = self.gateway.update_objects(
            "users",
            self.mapper.to_user_payload(user),
            {"users": {"id": user.id}},
            device_ids=[device.id],
        )
        if response.status_code != status.HTTP_200_OK:
            raise UserDeviceSyncError(
                f"Erro ao atualizar usuario na catraca {device.name}: {response.data}"
            )

        self.sync_pin(device, user)

        current_admin = self.is_device_admin_user(user)
        if current_admin:
            self.set_user_admin_on_device(device, user.id)
        elif previous_device_admin:
            role_resp = self.gateway.destroy_objects(
                "user_roles",
                {"user_roles": {"user_id": user.id}},
                device_ids=[device.id],
            )
            if role_resp.status_code not in (
                status.HTTP_204_NO_CONTENT,
                status.HTTP_200_OK,
            ):
                raise UserDeviceSyncError(
                    "Erro ao remover papel administrativo na catraca "
                    f"{device.name}: {role_resp.data}"
                )

    def delete_user_from_device(self, device: Device, user: User) -> None:
        self.gateway.set_device(device)
        self.gateway.destroy_objects(
            "user_roles",
            {"user_roles": {"user_id": user.id}},
            device_ids=[device.id],
        )
        self.gateway.destroy_objects(
            "pins",
            {"pins": {"user_id": user.id}},
            device_ids=[device.id],
        )
        response = self.gateway.destroy_objects(
            "users",
            {"users": {"id": user.id}},
            device_ids=[device.id],
        )
        if response.status_code != status.HTTP_204_NO_CONTENT:
            raise UserDeviceSyncError(
                f"Erro ao deletar usuario da catraca {device.name}: {response.data}"
            )

    def sync_pin(self, device: Device, user: User, *, allow_create: bool = False) -> None:
        if not user.pin:
            return

        if allow_create:
            try:
                pin_resp = self.gateway.create_objects(
                    "pins",
                    [{"user_id": user.id, "value": user.pin}],
                    device_ids=[device.id],
                )
            except CatracaSyncError as exc:
                logger.warning(
                    "Falha ao criar PIN na catraca %s: %s",
                    device.name,
                    exc,
                )
                return

            if pin_resp.status_code != status.HTTP_201_CREATED:
                logger.warning(
                    "Falha ao criar PIN na catraca %s: %s",
                    device.name,
                    pin_resp.data,
                )
            return

        try:
            pin_resp = self.gateway.update_objects(
                "pins",
                {"value": user.pin},
                {"pins": {"user_id": user.id}},
                device_ids=[device.id],
            )
        except CatracaSyncError:
            pin_resp = None

        if pin_resp is None or pin_resp.status_code != status.HTTP_200_OK:
            try:
                self.gateway.create_objects(
                    "pins",
                    [{"user_id": user.id, "value": user.pin}],
                    device_ids=[device.id],
                )
            except CatracaSyncError as exc:
                logger.warning(
                    "Falha ao recriar PIN na catraca %s: %s",
                    device.name,
                    exc,
                )

    def set_user_admin_on_device(self, device: Device, user_id: int) -> None:
        self.gateway.set_device(device)
        payload = [{"user_id": user_id, "role": 1}]
        try:
            create_response = self.gateway.create_objects(
                "user_roles",
                payload,
                device_ids=[device.id],
            )
            if create_response.status_code == status.HTTP_201_CREATED:
                return
            create_error = create_response.data
        except CatracaSyncError as exc:
            create_error = str(exc)

        try:
            update_response = self.gateway.update_objects(
                "user_roles",
                {"user_id": user_id, "role": 1},
                {"user_roles": {"user_id": user_id}},
                device_ids=[device.id],
            )
        except CatracaSyncError as exc:
            raise UserDeviceSyncError(
                "Erro ao definir administrador na catraca "
                f"{device.name}: create {create_error} | update {exc}"
            ) from exc

        if update_response.status_code != status.HTTP_200_OK:
            raise UserDeviceSyncError(
                "Erro ao definir administrador na catraca "
                f"{device.name}: create {create_error} | "
                f"update {update_response.data}"
            )
