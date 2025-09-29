from django.db import models
from src.core.control_Id.infra.control_id_django_app.models import Device


class UIConfig(models.Model):
    """Configurações de interface do usuário da catraca"""
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name='ui_config')
    
    # Configurações de tela
    screen_always_on = models.BooleanField(default=False, help_text="Tela sempre ligada")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração de Interface"
        verbose_name_plural = "Configurações de Interface"

    def __str__(self):
        return f"Configuração de Interface - {self.device.name}"

