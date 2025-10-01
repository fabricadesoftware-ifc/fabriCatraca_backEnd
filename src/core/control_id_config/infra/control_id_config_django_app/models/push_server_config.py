from django.db import models
from src.core.control_Id.infra.control_id_django_app.models import Device


class PushServerConfig(models.Model):
    """Configurações do servidor Push (seção 'push_server' da API)"""
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name='push_server_config')
    
    # Timeout das requisições
    push_request_timeout = models.IntegerField(
        default=15000,
        help_text="Timeout das requisições do equipamento para o servidor em milissegundos"
    )
    
    # Período entre requisições
    push_request_period = models.IntegerField(
        default=60,
        help_text="Período entre as requisições de push em segundos"
    )
    
    # Endereço remoto
    push_remote_address = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Endereço IP e porta em que o servidor está rodando (ex: 192.168.120.94:80)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração do Servidor Push"
        verbose_name_plural = "Configurações do Servidor Push"

    def __str__(self):
        return f"Configuração Push Server - {self.device.name}"
