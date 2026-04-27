from django.conf import settings
from django.db import models
from src.core.__seedwork__.domain import BaseModel
from django.db.models import Q
from django.utils import timezone

from src.core.user.infra.user_django_app.models import User, Visitas

from .access_logs import AccessLogs
from .access_rule import AccessRule
from .user_access_rule import UserAccessRule
from .portal_group import PortalGroup


class TemporaryUserRelease(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        ACTIVE = "active", "Ativa"
        CONSUMED = "consumed", "Consumida"
        EXPIRED = "expired", "Expirada"
        CANCELLED = "cancelled", "Cancelada"
        FAILED = "failed", "Falhou"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="temporary_user_releases",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_temporary_user_releases",
    )
    notified_server = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notified_temporary_user_releases",
        help_text="Servidor/professor que deve receber o e-mail desta liberacao.",
    )
    access_rule = models.ForeignKey(
        AccessRule,
        on_delete=models.PROTECT,
        related_name="temporary_user_releases",
    )
    portal_group = models.ForeignKey(
        PortalGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="temporary_user_releases",
        help_text=(
            "Se definido, a liberação se aplica apenas às catracas deste grupo."
        ),
    )
    visita = models.ForeignKey(
        Visitas,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="temporary_user_releases",
        help_text="Visita relacionada a esta liberacao temporaria, quando aplicavel.",
    )
    user_access_rule = models.ForeignKey(
        UserAccessRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="temporary_user_releases",
    )
    consumed_log = models.ForeignKey(
        AccessLogs,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consumed_temporary_user_releases",
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
    notes = models.TextField(default="Indefinido")
    notification_message = models.TextField(
        blank=True,
        default="",
        help_text="Mensagem completa do e-mail enviada ao servidor.",
    )
    notification_email = models.TextField(
        blank=True,
        default="",
        help_text="E-mails que devem receber a notificacao desta liberacao.",
    )
    result_message = models.TextField(blank=True, default="")

    class Meta(BaseModel.Meta):
        db_table = "temporary_user_releases"
        verbose_name = "Liberação Temporária"
        verbose_name_plural = "Liberações Temporárias"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["valid_from", "status"]),
            models.Index(fields=["valid_until", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(status__in=["pending", "active"]),
                name="unique_open_temporary_release_per_user",
            ),
        ]

    def __str__(self):
        return (
            f"Liberacao temporaria de {self.user} "
            f"({self.status}) ate {self.valid_until:%d/%m/%Y %H:%M:%S}"
        )
