from django.db import models
from src.core.control_Id.infra.control_id_django_app.models import Device


class SystemConfig(models.Model):
    """Configurações gerais do sistema da catraca"""
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name='system_config')
    
    # Configurações de reinicialização
    auto_reboot_hour = models.IntegerField(default=3, help_text="Hora para reinicialização automática")
    auto_reboot_minute = models.IntegerField(default=0, help_text="Minuto para reinicialização automática")
    
    # Configurações de usuários
    clear_expired_users = models.BooleanField(default=False, help_text="Limpar usuários expirados")
    keep_user_image = models.BooleanField(default=True, help_text="Manter imagens dos usuários")
    
    # Configurações de conectividade
    url_reboot_enabled = models.BooleanField(default=True, help_text="Habilitar reinicialização via URL")
    web_server_enabled = models.BooleanField(default=True, help_text="Habilitar servidor web")
    online = models.BooleanField(default=True, help_text="Modo online")
    local_identification = models.BooleanField(default=True, help_text="Identificação local")
    
    # Configurações de idioma e horário
    language = models.CharField(max_length=10, default='pt', help_text="Idioma do sistema")
    daylight_savings_time_start = models.DateTimeField(null=True, blank=True, help_text="Início do horário de verão")
    daylight_savings_time_end = models.DateTimeField(null=True, blank=True, help_text="Fim do horário de verão")
    
    # Configurações de timeout
    catra_timeout = models.IntegerField(default=30, help_text="Timeout da catraca em segundos")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração do Sistema"
        verbose_name_plural = "Configurações do Sistema"

    def __str__(self):
        return f"Configuração do Sistema - {self.device.name}"

