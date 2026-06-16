from __future__ import annotations

from typing import Any

from rest_framework import status

from src.core.control_id.infra.control_id_django_app.gateways import ControlIDGateway
from src.core.control_id.infra.control_id_django_app.models.device import Device


class CardEnrollmentError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        details: Any = None,
        code: str = "card_enrollment_failed",
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details
        self.code = code


class CardEnrollmentService:
    def __init__(self, gateway: ControlIDGateway | None = None) -> None:
        self.gateway = gateway or ControlIDGateway()

    def capture_card(self, device: Device, *, user_id: int = 0) -> int:
        self.gateway.set_device(device)
        response = self.gateway.remote_enroll(
            user_id=user_id,
            enrollment_type="card",
            save=False,
            sync=True,
        )

        if response.status_code != status.HTTP_201_CREATED:
            raise CardEnrollmentError(
                "Erro no cadastro remoto do cartao",
                code="card_remote_enroll_failed",
                details=response.data,
                status_code=response.status_code,
            )

        card_data = response.data or {}
        captured_value = card_data.get("card_value")
        if not captured_value:
            raise CardEnrollmentError(
                "Catraca nao retornou o valor do cartao",
                code="card_value_missing",
                details=card_data,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return int(captured_value)
