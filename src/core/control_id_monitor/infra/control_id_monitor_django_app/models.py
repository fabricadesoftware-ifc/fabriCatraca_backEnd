from django.conf import settings
from django.db import models
from django.utils import timezone

from src.core.control_id.infra.control_id_django_app.models import Device


class MonitorConfig(models.Model):
    """Configuracoes do monitor/push enviadas para a catraca."""

    device = models.OneToOneField(
        Device,
        on_delete=models.CASCADE,
        related_name="monitor_config",
        help_text="Dispositivo/catraca vinculada a esta configuração de monitor",
    )
    request_timeout = models.IntegerField(
        default=1000,
        help_text="Tempo em ms para timeout da request HTTP que a catraca envia",
    )
    hostname = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Hostname ou IP do servidor que vai receber notificações (ex: api.exemplo.com ou 192.168.1.100)",
    )
    port = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text="Porta do servidor de monitor (ex: 80, 443, 8000)",
    )
    path = models.CharField(
        max_length=255,
        blank=True,
        default="api/notifications",
        help_text="Endpoint/path do servidor onde a catraca vai enviar (ex: /api/monitor/events)",
    )
    heartbeat_timeout_seconds = models.PositiveIntegerField(
        default=300,
        help_text="Segundos sem sinais antes de considerar a catraca offline",
    )
    last_seen_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Ultimo instante em que o backend recebeu sinal da catraca",
    )
    last_payload_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Ultimo payload recebido do monitor da catraca",
    )
    last_signal_source = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Origem do ultimo sinal recebido (alive, dao, catra_event)",
    )
    offline_since = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Instante em que a catraca foi considerada offline",
    )
    offline_detection_paused_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Pausa temporaria da deteccao de offline durante manutencao/easy setup",
    )
    auto_disabled_due_to_offline = models.BooleanField(
        default=False,
        help_text="Indica se a catraca foi desativada automaticamente por ter ficado offline",
    )
    is_offline = models.BooleanField(
        default=False,
        help_text="Indica se a catraca esta atualmente sem sinais dentro do timeout",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração de Monitor"
        verbose_name_plural = "Configurações de Monitor"
        db_table = "control_id_monitor_config"

    def __str__(self):
        if self.hostname:
            return (
                f"Monitor {self.device.name} -> {self.hostname}:{self.port}/{self.path}"
            )
        return f"Monitor {self.device.name} (nao configurado)"

    @property
    def is_configured(self):
        return bool(self.hostname and self.hostname.strip())

    @property
    def full_url(self):
        if not self.is_configured:
            return None

        protocol = "https" if self.port == "443" else "http"
        port_str = (
            f":{self.port}" if self.port and self.port not in ["80", "443"] else ""
        )
        path_str = self.path if self.path.startswith("/") else f"/{self.path}"
        return f"{protocol}://{self.hostname}{port_str}{path_str}"

    @property
    def status(self):
        if self.is_offline:
            return "offline"
        if self.is_configured:
            return "configured"
        return "not_configured"


class MonitorAlert(models.Model):
    class AlertType(models.TextChoices):
        DEVICE_OFFLINE = "device_offline", "Catraca Offline"
        AUTHORIZED_EXIT_DELAY = "authorized_exit_delay", "Saida com atraso"
        GENERIC = "generic", "Generico"

    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"

    type = models.CharField(
        max_length=64, choices=AlertType.choices, default=AlertType.GENERIC
    )
    severity = models.CharField(
        max_length=16, choices=Severity.choices, default=Severity.WARNING
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    device = models.ForeignKey(
        Device,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="monitor_alerts",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="monitor_alerts",
    )
    dedupe_key = models.CharField(max_length=255, blank=True, default="", db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Alerta de Monitor"
        verbose_name_plural = "Alertas de Monitor"
        ordering = ("-is_active", "-started_at", "-created_at")

    def __str__(self):
        return self.title


class MonitorAlertRead(models.Model):
    alert = models.ForeignKey(
        MonitorAlert, on_delete=models.CASCADE, related_name="reads"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="monitor_alert_reads",
    )
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Leitura de Alerta"
        verbose_name_plural = "Leituras de Alertas"
        constraints = [
            models.UniqueConstraint(
                fields=("alert", "user"), name="unique_monitor_alert_read"
            ),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.alert_id}"
