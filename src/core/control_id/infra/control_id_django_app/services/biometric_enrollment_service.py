from __future__ import annotations

from typing import Any

from rest_framework import status

from src.core.control_id.infra.control_id_django_app.gateways import ControlIDGateway
from src.core.control_id.infra.control_id_django_app.models.device import Device


class BiometricEnrollmentError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        details: Any = None,
        code: str = "biometric_enrollment_failed",
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details
        self.code = code


class BiometricEnrollmentService:
    def __init__(self, gateway: ControlIDGateway | None = None) -> None:
        self.gateway = gateway or ControlIDGateway()

    def capture_template(self, device: Device, *, user_id: int) -> str:
        self.gateway.set_device(device)
        response = self.gateway.remote_enroll(
            user_id=user_id,
            enrollment_type="biometry",
            save=False,
            sync=True,
        )

        if response.status_code != status.HTTP_201_CREATED:
            raise BiometricEnrollmentError(
                "Erro no cadastro remoto da biometria",
                code="biometric_remote_enroll_failed",
                details=response.data,
                status_code=response.status_code,
            )

        if not isinstance(response.data, dict):
            raise BiometricEnrollmentError(
                "Resposta invalida da catraca no cadastro remoto da biometria",
                code="biometric_remote_enroll_invalid_response",
                details=response.data,
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        captured_template = str(response.data.get("template") or "").strip()
        if not captured_template:
            raise BiometricEnrollmentError(
                "Catraca nao retornou o template biometrico",
                code="biometric_template_missing",
                details=response.data,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return captured_template
