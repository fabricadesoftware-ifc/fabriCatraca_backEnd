from django.db import models
from src.core.control_Id.infra.control_id_django_app.models import Device


class HardwareConfig(models.Model):
    """Configura??es de hardware da catraca"""

    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name="hardware_config")

    # Configura??es de som
    beep_enabled = models.BooleanField(default=True, help_text="Habilitar som de beep")
    bell_enabled = models.BooleanField(default=False, help_text="Habilitar campainha")
    bell_relay = models.IntegerField(default=2, help_text="Rel? da campainha")

    # Configura??es SSH
    ssh_enabled = models.BooleanField(default=False, help_text="Habilitar SSH")

    # Configura??es de rel?s
    relayN_enabled = models.BooleanField(default=False, help_text="Habilitar rel? N")
    relayN_timeout = models.IntegerField(default=5, help_text="Timeout do rel? N em segundos")
    relayN_auto_close = models.BooleanField(default=True, help_text="Fechar rel? automaticamente")

    # Configura??es de sensores de porta
    door_sensorN_enabled = models.BooleanField(default=False, help_text="Habilitar sensor de porta N")
    door_sensorN_idle = models.IntegerField(default=10, help_text="Tempo de inatividade do sensor em segundos")
    doorN_interlock = models.BooleanField(default=False, help_text="Intertravamento da porta N")

    # Configura??es de exce??o
    EXCEPTION_MODE_CHOICES = [
        ("none", "Normal"),
        ("emergency", "Emerg?ncia"),
        ("lock_down", "Lockdown"),
    ]
    exception_mode = models.CharField(
        max_length=20,
        choices=EXCEPTION_MODE_CHOICES,
        default="none",
        help_text="Modo de exce??o",
    )
    doorN_exception_mode = models.BooleanField(default=False, help_text="Modo de exce??o da porta N")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configura??o de Hardware"
        verbose_name_plural = "Configura??es de Hardware"

    def __str__(self):
        return f"Configura??o de Hardware - {self.device.name}"
