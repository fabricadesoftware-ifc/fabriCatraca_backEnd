from __future__ import annotations

from rest_framework import status

from src.core.__seedwork__.infra.catraca_sync import CatracaSyncError
from src.core.control_id.infra.control_id_django_app.gateways import ControlIDGateway
from src.core.control_id.infra.control_id_django_app.models.cards import Card
from src.core.control_id.infra.control_id_django_app.models.device import Device
from src.core.user.infra.user_django_app.models import User
from src.core.user.infra.user_django_app.services import UserDeviceSyncService


class CardDeviceSyncError(RuntimeError):
    pass


class CardDeviceSyncService:
    def __init__(self, gateway: ControlIDGateway | None = None) -> None:
        self.gateway = gateway or ControlIDGateway()

    @staticmethod
    def card_value_as_int(value) -> int:
        return int(value)

    def to_payload(self, card: Card) -> dict[str, int]:
        return {
            "id": card.id,
            "user_id": card.user_id,
            "value": self.card_value_as_int(card.value),
        }

    def get_target_devices_for_user(self, user: User) -> list[Device]:
        return list(user.get_target_devices(include_inactive=False))

    def ensure_user_on_device(
        self,
        device: Device,
        user: User,
        user_sync_service: UserDeviceSyncService,
    ) -> None:
        try:
            user_sync_service.upsert_user_in_device(device, user)
        except Exception as exc:
            raise CardDeviceSyncError(
                f"Usuario {user.id} ausente na catraca {device.name}: {exc}"
            ) from exc

    def create_card_in_device(self, device: Device, card: Card) -> None:
        self.gateway.set_device(device)
        try:
            response = self.gateway.create_objects(
                "cards",
                [self.to_payload(card)],
                device_ids=[device.id],
            )
        except CatracaSyncError as exc:
            raise CardDeviceSyncError(
                f"Erro ao criar cartao na catraca {device.name}: {exc}"
            ) from exc

        if response.status_code != status.HTTP_201_CREATED:
            raise CardDeviceSyncError(
                f"Erro ao criar cartao na catraca {device.name}: {response.data}"
            )

    def update_card_in_device(self, device: Device, card: Card) -> None:
        self.gateway.set_device(device)
        try:
            response = self.gateway.update_objects(
                "cards",
                self.to_payload(card),
                {"cards": {"id": card.id}},
                device_ids=[device.id],
            )
        except CatracaSyncError as exc:
            raise CardDeviceSyncError(
                f"Erro ao atualizar cartao na catraca {device.name}: {exc}"
            ) from exc

        if response.status_code != status.HTTP_200_OK:
            raise CardDeviceSyncError(
                f"Erro ao atualizar cartao na catraca {device.name}: {response.data}"
            )

    def delete_card_from_device(self, device: Device, card: Card) -> None:
        self.gateway.set_device(device)
        try:
            response = self.gateway.destroy_objects(
                "cards",
                {"cards": {"id": card.id}},
                device_ids=[device.id],
            )
        except CatracaSyncError as exc:
            raise CardDeviceSyncError(
                f"Erro ao deletar cartao da catraca {device.name}: {exc}"
            ) from exc

        if response.status_code != status.HTTP_204_NO_CONTENT:
            raise CardDeviceSyncError(
                f"Erro ao deletar cartao da catraca {device.name}: {response.data}"
            )

    def create_card_for_user_devices(
        self,
        card: Card,
        devices: list[Device],
        user_sync_service: UserDeviceSyncService,
    ) -> None:
        for device in devices:
            self.ensure_user_on_device(device, card.user, user_sync_service)
            self.create_card_in_device(device, card)

    def update_card_for_user_devices(
        self,
        card: Card,
        devices: list[Device],
        user_sync_service: UserDeviceSyncService,
    ) -> None:
        for device in devices:
            self.ensure_user_on_device(device, card.user, user_sync_service)
            self.update_card_in_device(device, card)

    def delete_card_for_user_devices(self, card: Card, devices: list[Device]) -> None:
        for device in devices:
            self.delete_card_from_device(device, card)
