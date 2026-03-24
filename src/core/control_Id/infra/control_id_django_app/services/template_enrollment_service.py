from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from django.db import transaction

from src.core.__seedwork__.infra.mixins import TemplateSyncMixin
from src.core.control_Id.infra.control_id_django_app.models.device import Device
from src.core.control_Id.infra.control_id_django_app.models.template import Template
from src.core.user.infra.user_django_app.models import User


class TemplateEnrollmentError(Exception):
    def __init__(self, message: str, status_code: int = 400, details=None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details


@dataclass
class EnrollmentResult:
    instance: Template
    enrollment_mode: str
    replication_errors: list[str]


class TemplateEnrollmentService(TemplateSyncMixin):
    def _replicate_template(self, instance: Template) -> list[str]:
        devices = Device.objects.filter(is_active=True)
        errors: list[str] = []

        for device in devices:
            self.set_device(device)
            create_response = self.create_in_catraca(cast(Any, instance))
            if create_response.status_code != 201:
                errors.append(f"{device.name}: {create_response.data}")

        return errors

    def _capture_remote_template(
        self, user_id: int, enrollment_device_id: int | None
    ) -> str:
        if not enrollment_device_id:
            raise TemplateEnrollmentError(
                "É necessário especificar uma catraca para cadastro remoto (enrollment_device_id)",
                status_code=400,
            )

        try:
            enrollment_device = Device.objects.get(id=enrollment_device_id)
        except Device.DoesNotExist as exc:
            raise TemplateEnrollmentError(
                f"Catraca com ID {enrollment_device_id} não encontrada",
                status_code=404,
            ) from exc

        self.set_device(enrollment_device)
        response = self.remote_enroll(
            user_id=user_id,
            type="biometry",
            save=False,
            sync=True,
        )

        if response.status_code != 201:
            raise TemplateEnrollmentError(
                "Erro no cadastro remoto da biometria",
                status_code=response.status_code,
                details=response.data,
            )

        template_data = response.data or {}
        captured_template = template_data.get("template")
        if not captured_template:
            raise TemplateEnrollmentError(
                "Catraca não retornou o template biométrico",
                status_code=500,
                details=template_data,
            )

        return captured_template

    def _capture_local_template(self, captured_template: str | None) -> str:
        if not captured_template:
            raise TemplateEnrollmentError(
                "No modo local, envie o template em 'captured_template'.",
                status_code=400,
            )
        return captured_template

    def _resolve_user(self, user_id: int | str) -> User:
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist as exc:
            raise TemplateEnrollmentError(
                f"Usuário com ID {user_id} não encontrado",
                status_code=404,
            ) from exc

    def enroll(
        self,
        *,
        user_id: int | str,
        enrollment_mode: str,
        enrollment_device_id: int | None = None,
        captured_template: str | None = None,
        finger_type: int = 0,
        finger_position: int = 0,
    ) -> EnrollmentResult:
        user = self._resolve_user(user_id)
        mode = (enrollment_mode or "remote").lower()

        if mode == "remote":
            template_value = self._capture_remote_template(
                user_id=int(user.pk),
                enrollment_device_id=enrollment_device_id,
            )
        elif mode == "local":
            template_value = self._capture_local_template(captured_template)
        else:
            raise TemplateEnrollmentError(
                "enrollment_mode inválido. Use 'remote' ou 'local'.",
                status_code=400,
            )

        with transaction.atomic():
            instance = Template.objects.create(
                user=user,
                template=template_value,
                finger_type=finger_type,
                finger_position=finger_position,
            )
            errors = self._replicate_template(instance)

        return EnrollmentResult(
            instance=instance,
            enrollment_mode=mode,
            replication_errors=errors,
        )
