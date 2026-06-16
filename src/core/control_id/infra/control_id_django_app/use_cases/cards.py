from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from rest_framework import status

from src.core.control_id.infra.control_id_django_app.models.cards import Card
from src.core.control_id.infra.control_id_django_app.models.device import Device
from src.core.control_id.infra.control_id_django_app.services import (
    CardDeviceSyncService,
    CardEnrollmentService,
)
from src.core.user.infra.user_django_app.models import User
from src.core.user.infra.user_django_app.services import UserDeviceSyncService


class CardOperationError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details=None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


@dataclass(frozen=True)
class CardUseCaseResult:
    card: Card


class CreateCardUseCase:
    def __init__(
        self,
        enrollment_service: CardEnrollmentService | None = None,
        card_sync_service: CardDeviceSyncService | None = None,
        user_sync_service: UserDeviceSyncService | None = None,
    ) -> None:
        self.enrollment_service = enrollment_service or CardEnrollmentService()
        self.card_sync_service = card_sync_service or CardDeviceSyncService()
        self.user_sync_service = user_sync_service or UserDeviceSyncService()

    def execute(
        self,
        serializer,
        *,
        user: User,
        enrollment_device: Device,
    ) -> CardUseCaseResult:
        devices = self.card_sync_service.get_target_devices_for_user(user)
        device_ids = {device.id for device in devices}

        if not device_ids:
            raise CardOperationError(
                "Usuario nao possui catracas alvo para cartao.",
                code="card_user_without_target_devices",
            )

        if enrollment_device.id not in device_ids:
            raise CardOperationError(
                "A catraca escolhida nao faz parte do escopo do usuario.",
                code="card_enrollment_device_out_of_scope",
            )

        captured_value = self.enrollment_service.capture_card(
            enrollment_device,
            user_id=user.id,
        )

        with transaction.atomic():
            card = serializer.save(value=str(captured_value))
            self.card_sync_service.create_card_for_user_devices(
                card,
                devices,
                self.user_sync_service,
            )
            return CardUseCaseResult(card=card)


class UpdateCardUseCase:
    def __init__(
        self,
        card_sync_service: CardDeviceSyncService | None = None,
        user_sync_service: UserDeviceSyncService | None = None,
    ) -> None:
        self.card_sync_service = card_sync_service or CardDeviceSyncService()
        self.user_sync_service = user_sync_service or UserDeviceSyncService()

    def execute(self, serializer) -> CardUseCaseResult:
        with transaction.atomic():
            card = serializer.save()
            devices = self.card_sync_service.get_target_devices_for_user(card.user)
            self.card_sync_service.update_card_for_user_devices(
                card,
                devices,
                self.user_sync_service,
            )
            return CardUseCaseResult(card=card)


class DeleteCardUseCase:
    def __init__(
        self,
        card_sync_service: CardDeviceSyncService | None = None,
    ) -> None:
        self.card_sync_service = card_sync_service or CardDeviceSyncService()

    def execute(self, card: Card) -> None:
        with transaction.atomic():
            devices = self.card_sync_service.get_target_devices_for_user(card.user)
            self.card_sync_service.delete_card_for_user_devices(card, devices)
            card.delete()
