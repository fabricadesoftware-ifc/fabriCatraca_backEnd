from django.conf import settings
from django.db import models


class ReleaseAudit(models.Model):
    class ReleaseType(models.TextChoices):
        DEVICE_EVENT = "device_event", "Liberação por evento"
        SINGLE_TURN = "single_turn", "Giro único"
        SCHEDULED_USER_RELEASE = "scheduled_user_release", "Liberação agendada"
        TEMPORARY_USER_RELEASE = "temporary_user_release", "Liberação temporária"

    class Status(models.TextChoices):
        REQUESTED = "requested", "Solicitada"
        SENT = "sent", "Enviada"
        ACTIVE = "active", "Ativa"
        CONSUMED = "consumed", "Consumida"
        EXPIRED = "expired", "Expirada"
        CANCELLED = "cancelled", "Cancelada"
        FAILED = "failed", "Falhou"

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="release_audits_requested",
    )
    requested_by_name = models.CharField(max_length=255, blank=True, default="")
    requested_by_role = models.CharField(max_length=50, blank=True, default="")
    requested_by_email = models.EmailField(blank=True, default="")

    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="release_audits_targeted",
    )
    target_user_name = models.CharField(max_length=255, blank=True, default="")
    target_user_registration = models.CharField(max_length=50, blank=True, default="")

    device = models.ForeignKey(
        "control_id_django_app.Device",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="release_audits",
    )
    portal = models.ForeignKey(
        "control_id_django_app.Portal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="release_audits",
    )
    temporary_release = models.OneToOneField(
        "control_id_django_app.TemporaryUserRelease",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="release_audit",
    )
    access_log = models.ForeignKey(
        "control_id_django_app.AccessLogs",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="release_audits",
    )

    release_type = models.CharField(max_length=40, choices=ReleaseType.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.REQUESTED,
    )
    notes = models.TextField(blank=True, default="")
    error_message = models.TextField(blank=True, default="")
    request_payload = models.JSONField(default=dict, blank=True)
    response_payload = models.JSONField(default=dict, blank=True)

    requested_at = models.DateTimeField(auto_now_add=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "release_audits"
        verbose_name = "Auditoria de Liberação"
        verbose_name_plural = "Auditorias de Liberação"
        ordering = ["-requested_at", "-id"]
        indexes = [
            models.Index(fields=["release_type", "status"]),
            models.Index(fields=["requested_by", "requested_at"]),
            models.Index(fields=["target_user", "requested_at"]),
            models.Index(fields=["device", "requested_at"]),
            models.Index(fields=["scheduled_for"]),
        ]

    def __str__(self):
        return (
            f"{self.get_release_type_display()} - {self.requested_by_name or self.requested_by_id}"
        )
