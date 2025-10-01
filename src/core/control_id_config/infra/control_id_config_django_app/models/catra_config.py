from django.db import models
from src.core.control_Id.infra.control_id_django_app.models import Device


class CatraConfig(models.Model):
    """Configurações específicas da catraca (seção 'catra' da API)"""
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name='catra_config')
    
    # Anti-dupla entrada
    anti_passback = models.BooleanField(
        default=False, 
        help_text="Habilita ou desabilita o controle de anti-dupla entrada"
    )
    
    # Reset diário
    daily_reset = models.BooleanField(
        default=False,
        help_text="Habilita o reset de logs para o controle de anti-dupla entrada (meia-noite)"
    )
    
    # Sentido da entrada
    GATEWAY_CHOICES = [
        ('clockwise', 'Horário'),
        ('anticlockwise', 'Anti-horário'),
    ]
    gateway = models.CharField(
        max_length=20,
        choices=GATEWAY_CHOICES,
        default='clockwise',
        help_text="Sentido da entrada (horário ou anti-horário)"
    )
    
    # Modo de operação
    OPERATION_MODE_CHOICES = [
        ('blocked', 'Ambas controladas'),
        ('entrance_open', 'Entrada liberada'),
        ('exit_open', 'Saída liberada'),
        ('both_open', 'Ambas liberadas'),
    ]
    operation_mode = models.CharField(
        max_length=20,
        choices=OPERATION_MODE_CHOICES,
        default='blocked',
        help_text="Modo de operação da catraca"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração da Catraca"
        verbose_name_plural = "Configurações da Catraca"

    def __str__(self):
        return f"Configuração da Catraca - {self.device.name}"
