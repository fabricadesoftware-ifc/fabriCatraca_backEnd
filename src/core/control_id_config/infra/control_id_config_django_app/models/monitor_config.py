from django.db import models
from src.core.control_Id.infra.control_id_django_app.models import Device


class MonitorConfig(models.Model):
    """Parâmetros do bloco monitor conforme documentação Control iD."""
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name='monitor_config')

    # Campos do monitor (um por um)
    request_timeout = models.IntegerField(default=1000, help_text="Tempo em ms para timeout da request")
    hostname = models.CharField(max_length=255, blank=True, default="", help_text="Hostname/IP do servidor de monitor")
    port = models.CharField(max_length=10, blank=True, default="", help_text="Porta do servidor de monitor")
    path = models.CharField(max_length=255, blank=True, default="api/notifications", help_text="Endpoint de notificações do monitor")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração de Monitor"
        verbose_name_plural = "Configurações de Monitor"

    def __str__(self):
        return f"Configuração de Monitor - {self.device.name}"


