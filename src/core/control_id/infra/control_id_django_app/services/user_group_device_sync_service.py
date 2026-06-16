from __future__ import annotations

from rest_framework import status

from src.core.__seedwork__.infra.catraca_sync import CatracaSyncError
from src.core.control_id.infra.control_id_django_app.gateways import ControlIDGateway
from src.core.control_id.infra.control_id_django_app.models.device import Device
from src.core.control_id.infra.control_id_django_app.models.user_groups import (
    UserGroup,
)
from src.core.user.infra.user_django_app.mappers import UserControlIDMapper


class UserGroupDeviceSyncError(RuntimeError):
    pass


class UserGroupDeviceSyncService:
    def __init__(
        self,
        gateway: ControlIDGateway | None = None,
        user_mapper: type[UserControlIDMapper] = UserControlIDMapper,
    ) -> None:
        self.gateway = gateway or ControlIDGateway()
        self.user_mapper = user_mapper

    @staticmethod
    def to_group_payload(instance: UserGroup) -> dict[str, int | str]:
        return {
            "id": instance.group.id,
            "name": instance.group.name,
        }

    @staticmethod
    def to_relation_payload(instance: UserGroup) -> dict[str, int]:
        return {
            "user_id": instance.user.id,
            "group_id": instance.group.id,
        }

    def get_target_devices(self, instance: UserGroup):
        return list(instance.user.get_target_devices(include_inactive=False))

    def ensure_parent_objects_on_current_device(
        self,
        instance: UserGroup,
        device: Device,
    ) -> None:
        group_response = self.gateway.create_or_update_objects(
            "groups",
            [self.to_group_payload(instance)],
            device_ids=[device.id],
        )
        if group_response.status_code != status.HTTP_200_OK:
            raise UserGroupDeviceSyncError(
                f"Erro ao sincronizar grupo pai: {group_response.data}"
            )

        user_response = self.gateway.create_or_update_objects(
            "users",
            [self.user_mapper.to_user_payload(instance.user)],
            device_ids=[device.id],
        )
        if user_response.status_code != status.HTTP_200_OK:
            raise UserGroupDeviceSyncError(
                f"Erro ao sincronizar usuario pai: {user_response.data}"
            )

    def create(self, instance: UserGroup) -> None:
        payload = self.to_relation_payload(instance)

        for device in self.get_target_devices(instance):
            self.gateway.set_device(device)
            self.ensure_parent_objects_on_current_device(instance, device)
            try:
                response = self.gateway.create_or_update_objects(
                    "user_groups",
                    [payload],
                    device_ids=[device.id],
                )
            except CatracaSyncError as exc:
                raise UserGroupDeviceSyncError(str(exc)) from exc

            if response.status_code != status.HTTP_200_OK:
                raise UserGroupDeviceSyncError(
                    f"Erro ao sincronizar vinculo: {response.data}"
                )

    def update(
        self,
        instance: UserGroup,
        *,
        previous_payload: dict[str, int] | None = None,
    ) -> None:
        payload = self.to_relation_payload(instance)
        where_payload = previous_payload or payload

        for device in self.get_target_devices(instance):
            self.gateway.set_device(device)
            self.ensure_parent_objects_on_current_device(instance, device)
            try:
                response = self.gateway.update_objects(
                    "user_groups",
                    payload,
                    {"user_groups": where_payload},
                    device_ids=[device.id],
                )
            except CatracaSyncError as exc:
                raise UserGroupDeviceSyncError(str(exc)) from exc

            if response.status_code != status.HTTP_200_OK:
                raise UserGroupDeviceSyncError(
                    f"Erro ao atualizar vinculo: {response.data}"
                )

    def delete(self, instance: UserGroup) -> None:
        payload = self.to_relation_payload(instance)

        for device in self.get_target_devices(instance):
            self.gateway.set_device(device)
            try:
                response = self.gateway.destroy_objects(
                    "user_groups",
                    {"user_groups": payload},
                    device_ids=[device.id],
                )
            except CatracaSyncError as exc:
                raise UserGroupDeviceSyncError(str(exc)) from exc

            if response.status_code != status.HTTP_204_NO_CONTENT:
                raise UserGroupDeviceSyncError(
                    f"Erro ao remover vinculo: {response.data}"
                )
