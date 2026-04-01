from django.conf import settings
from django.db import models
from src.core.__seedwork__.domain import BaseModel
from django.db.models import Q
from django.utils import timezone

from src.core.control_Id.infra.control_id_django_app.models import CustomGroup as Group

from .access_logs import AccessLogs
from .access_rule import AccessRule
from .group_access_rules import GroupAccessRule


class TemporaryGroupRelease(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        ACTIVE = "active", "Ativa"
        CONSUMED = "consumed", "Consumida"
        EXPIRED = "expired", "Expirada"
        CANCELLED = "cancelled", "Cancelada"
        FAILED = "failed", "Falhou"

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="temporary_group_releases",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_temporary_group_releases",
    )
    access_rule = models.ForeignKey(
        AccessRule,
        on_delete=models.PROTECT,
        related_name="temporary_group_releases",
    )
    group_access_rule = models.ForeignKey(
        GroupAccessRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="temporary_group_releases",
    )
    consumed_log = models.ForeignKey(
        AccessLogs,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consumed_temporary_group_releases",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField()
    activated_at = models.DateTimeField(null=True, blank=True)
    consumed_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    result_message = models.TextField(blank=True, default="")


    class Meta:
        db_table = "temporary_group_releases"
        verbose_name = "Liberação Temporária"
        verbose_name_plural = "Liberações Temporárias"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["group", "status"]),
            models.Index(fields=["valid_from", "status"]),
            models.Index(fields=["valid_until", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["group"],
                condition=Q(status__in=["pending", "active"]),
                name="unique_open_temporary_release_per_group",
            ),
        ]

    def __str__(self):
        return (
            f"Liberacao temporaria de {self.group} "
            f"({self.status}) ate {self.valid_until:%d/%m/%Y %H:%M:%S}"
        )
