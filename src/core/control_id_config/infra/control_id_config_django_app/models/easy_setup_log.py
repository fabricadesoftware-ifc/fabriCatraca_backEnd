from django.db import models
from django.utils import timezone

from src.core.control_id.infra.control_id_django_app.models import Device


class EasySetupLog(models.Model):
    """Registro de cada execução do Easy Setup, por device."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        RUNNING = "running", "Em execução"
        SUCCESS = "success", "Sucesso"
        PARTIAL = "partial", "Parcial (com avisos)"
        FAILED = "failed", "Falhou"

    # Agrupamento por execução (todas do mesmo POST compartilham o task_id)
    task_id = models.CharField(max_length=255, db_index=True)
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name="easy_setup_logs",
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    report = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "Easy Setup Log"
        verbose_name_plural = "Easy Setup Logs"

    def __str__(self):
        return f"[{self.status}] {self.device.name} — {self.started_at:%d/%m %H:%M}"
