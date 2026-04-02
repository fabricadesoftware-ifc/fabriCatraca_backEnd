from __future__ import annotations

import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone

from src.core.__seedwork__.domain import BaseModel
from src.core.user.infra.user_django_app.models import User

from .device import Device
from .template import Template


def default_capture_session_expiration():
    return timezone.now() + timedelta(minutes=5)


class BiometricCaptureSession(BaseModel):
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_EXPIRED = "expired"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pendente"),
        (STATUS_PROCESSING, "Processando"),
        (STATUS_COMPLETED, "Concluida"),
        (STATUS_FAILED, "Falhou"),
        (STATUS_EXPIRED, "Expirada"),
        (STATUS_CANCELLED, "Cancelada"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="biometric_capture_sessions",
    )
    requested_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requested_biometric_capture_sessions",
    )
    extractor_device = models.ForeignKey(
        Device,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="biometric_capture_sessions",
    )
    template = models.ForeignKey(
        Template,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="capture_sessions",
    )
    sensor_identifier = models.CharField(max_length=100, default="local-default")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    attempts = models.JSONField(default=list, blank=True)
    selected_quality = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(default=default_capture_session_expiration)

    class Meta(BaseModel.Meta):
        db_table = "biometric_capture_sessions"
        verbose_name = "Sessao de Captura Biometrica"
        verbose_name_plural = "Sessoes de Captura Biometrica"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Captura biometrica #{self.pk} - {self.user.name} - {self.status}"

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at
