from django.db import models
from src.core.control_Id.infra.control_id_django_app.models import Device


class HardwareConfig(models.Model):
    """Configurações de hardware da catraca"""
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name='hardware_config')
    
    # Configurações de som
    beep_enabled = models.BooleanField(default=True, help_text="Habilitar som de beep")
    bell_enabled = models.BooleanField(default=False, help_text="Habilitar campainha")
    bell_relay = models.IntegerField(default=1, help_text="Relé da campainha")
    
    # Configurações SSH
    ssh_enabled = models.BooleanField(default=False, help_text="Habilitar SSH")
    
    # Configurações de relés
    relayN_enabled = models.BooleanField(default=False, help_text="Habilitar relé N")
    relayN_timeout = models.IntegerField(default=5, help_text="Timeout do relé N em segundos")
    relayN_auto_close = models.BooleanField(default=True, help_text="Fechar relé automaticamente")
    
    # Configurações de sensores de porta
    door_sensorN_enabled = models.BooleanField(default=False, help_text="Habilitar sensor de porta N")
    door_sensorN_idle = models.IntegerField(default=10, help_text="Tempo de inatividade do sensor em segundos")
    doorN_interlock = models.BooleanField(default=False, help_text="Intertravamento da porta N")
    
    # Configurações de exceção
    exception_mode = models.BooleanField(default=False, help_text="Modo de exceção")
    doorN_exception_mode = models.BooleanField(default=False, help_text="Modo de exceção da porta N")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração de Hardware"
        verbose_name_plural = "Configurações de Hardware"

    def __str__(self):
        return f"Configuração de Hardware - {self.device.name}"

