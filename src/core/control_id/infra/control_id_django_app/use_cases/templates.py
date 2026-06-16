from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.db import transaction
from django.utils import timezone
from rest_framework import status

from src.core.control_id.infra.control_id_django_app.models import (
    BiometricCaptureSession,
    Device,
    Template,
)
from src.core.control_id.infra.control_id_django_app.services import (
    BiometricEnrollmentService,
    TemplateDeviceSyncService,
)
from src.core.user.infra.user_django_app.models import User


class TemplateOperationError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


@dataclass(frozen=True)
class TemplateUseCaseResult:
    template: Template
    replication_errors: list[dict] | None = None


class CreateRemoteTemplateUseCase:
    def __init__(
        self,
        enrollment_service: BiometricEnrollmentService | None = None,
        template_sync_service: TemplateDeviceSyncService | None = None,
    ) -> None:
        self.enrollment_service = enrollment_service or BiometricEnrollmentService()
        self.template_sync_service = template_sync_service or TemplateDeviceSyncService()

    def execute(
        self,
        serializer,
        *,
        user: User,
        enrollment_device: Device,
    ) -> TemplateUseCaseResult:
        devices = self.template_sync_service.get_target_devices_for_user(user)
        device_ids = {device.id for device in devices}

        if not device_ids:
            raise TemplateOperationError(
                "Usuario nao possui catracas alvo para biometria.",
                code="template_user_without_target_devices",
            )

        if enrollment_device.id not in device_ids:
            raise TemplateOperationError(
                "A catraca escolhida nao faz parte do escopo do usuario.",
                code="template_enrollment_device_out_of_scope",
            )

        captured_template = self.enrollment_service.capture_template(
            enrollment_device,
            user_id=user.id,
        )

        with transaction.atomic():
            template = serializer.save(template=captured_template)
            replication_errors = (
                self.template_sync_service.replicate_template_to_user_devices(template)
            )
            return TemplateUseCaseResult(
                template=template,
                replication_errors=replication_errors,
            )


class CompleteLocalCaptureSessionUseCase:
    def __init__(
        self,
        template_sync_service: TemplateDeviceSyncService | None = None,
    ) -> None:
        self.template_sync_service = template_sync_service or TemplateDeviceSyncService()

    def execute(
        self,
        serializer,
        *,
        session: BiometricCaptureSession,
        template_value: str,
        quality: int | None,
        attempts: list[dict],
    ) -> TemplateUseCaseResult:
        with transaction.atomic():
            template = serializer.save(template=template_value)
            replication_errors = (
                self.template_sync_service.replicate_template_to_user_devices(template)
            )

            session.template = template
            session.status = BiometricCaptureSession.STATUS_COMPLETED
            session.selected_quality = quality
            session.attempts = attempts
            session.error_message = ""
            session.finished_at = timezone.now()
            session.save(
                update_fields=[
                    "template",
                    "status",
                    "selected_quality",
                    "attempts",
                    "error_message",
                    "finished_at",
                    "updated_at",
                ]
            )

            return TemplateUseCaseResult(
                template=template,
                replication_errors=replication_errors,
            )


class UpdateTemplateUseCase:
    def __init__(
        self,
        template_sync_service: TemplateDeviceSyncService | None = None,
    ) -> None:
        self.template_sync_service = template_sync_service or TemplateDeviceSyncService()

    def execute(self, serializer) -> TemplateUseCaseResult:
        with transaction.atomic():
            template = serializer.save()
            self.template_sync_service.update_template_for_user_devices(template)
            return TemplateUseCaseResult(template=template)


class DeleteTemplateUseCase:
    def __init__(
        self,
        template_sync_service: TemplateDeviceSyncService | None = None,
    ) -> None:
        self.template_sync_service = template_sync_service or TemplateDeviceSyncService()

    def execute(self, template: Template) -> None:
        with transaction.atomic():
            self.template_sync_service.delete_template_for_user_devices(template)
            template.delete()
