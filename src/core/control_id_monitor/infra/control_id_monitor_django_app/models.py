from django.db import models
from src.core.control_Id.infra.control_id_django_app.models import Device


class MonitorConfig(models.Model):
    """
    Configurações do Monitor - Sistema de Push de Logs em Tempo Real
    
    O Monitor permite que a catraca ENVIE os logs automaticamente para um servidor,
    ao invés de termos que ficar sincronizando manualmente. Isso é muito mais eficiente!
    
    Funcionamento:
    - Quando alguém passa pela catraca, ela envia uma notificação HTTP para o servidor
    - Configuramos o hostname/IP, porta e endpoint onde a catraca vai enviar os dados
    - É um sistema PUSH (catraca → servidor) ao invés de PULL (servidor busca da catraca)
    """
    device = models.OneToOneField(
        Device, 
        on_delete=models.CASCADE, 
        related_name='monitor_config',
        help_text="Dispositivo/catraca vinculada a esta configuração de monitor"
    )

    # Timeout para as requisições HTTP que a catraca faz
    request_timeout = models.IntegerField(
        default=1000, 
        help_text="Tempo em ms para timeout da request HTTP que a catraca envia"
    )
    
    # Servidor que vai receber as notificações
    hostname = models.CharField(
        max_length=255, 
        blank=True, 
        default="", 
        help_text="Hostname ou IP do servidor que vai receber notificações (ex: api.exemplo.com ou 192.168.1.100)"
    )
    
    port = models.CharField(
        max_length=10, 
        blank=True, 
        default="", 
        help_text="Porta do servidor de monitor (ex: 80, 443, 8000)"
    )
    
    path = models.CharField(
        max_length=255, 
        blank=True, 
        default="api/notifications", 
        help_text="Endpoint/path do servidor onde a catraca vai enviar (ex: /api/monitor/events)"
    )
    
    # Controle de timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração de Monitor"
        verbose_name_plural = "Configurações de Monitor"
        db_table = "control_id_monitor_config"

    def __str__(self):
        if self.hostname:
            return f"Monitor {self.device.name} → {self.hostname}:{self.port}/{self.path}"
        return f"Monitor {self.device.name} (não configurado)"
    
    @property
    def is_configured(self):
        """Verifica se o monitor está configurado com hostname válido"""
        return bool(self.hostname and self.hostname.strip())
    
    @property
    def full_url(self):
        """Retorna a URL completa para onde a catraca enviará as notificações"""
        if not self.is_configured:
            return None
        
        protocol = "https" if self.port == "443" else "http"
        port_str = f":{self.port}" if self.port and self.port not in ["80", "443"] else ""
        path_str = self.path if self.path.startswith("/") else f"/{self.path}"
        
        return f"{protocol}://{self.hostname}{port_str}{path_str}"
