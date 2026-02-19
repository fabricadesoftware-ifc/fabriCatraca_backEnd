from django.db import models
from src.core.control_Id.infra.control_id_django_app.models import Device, Portal, AccessRule
from src.core.user.infra.user_django_app.models import User

class EventType(models.IntegerChoices):
    EQUIPAMENTO_INVALIDO = 1
    PARAMETRO_DE_IDENTIFICACAO_INVALIDO = 2
    NÃO_IDENTIFICADO = 3
    IDENTIFICACAO_PENDENTE = 4
    TEMPO_DE_IDENTIFICACAO_ESGOTADO = 5
    ACESSO_NEGADO = 6
    ACESSO_CONCEDIDO = 7
    ACESSO_PENDENTE = 8
    USUARIO_NAO_E_ADM = 9
    ACESSO_NAO_IDENTIFICADO = 10
    ACESSO_POR_BOTOEIRA = 11
    ACESSO_PELA_INTERFACE_WEB = 12
    DESISTENCIA_DE_ENTRADA = 13
    SEM_RESPOSTA = 14
    ACESSO_PELA_INTERFONIA = 15


class AccessLogs(models.Model):
    time = models.DateTimeField()
    event_type = models.IntegerField(choices=EventType.choices)
    device = models.ForeignKey(Device, on_delete=models.DO_NOTHING)
    identifier_id = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    portal = models.ForeignKey(Portal, on_delete=models.SET_NULL, blank=True, null=True)
    access_rule = models.ForeignKey(AccessRule, on_delete=models.SET_NULL, blank=True, null=True)
    qr_code = models.CharField(max_length=255)
    uhf_value = models.CharField(max_length=255)
    pin_value = models.CharField(max_length=255)
    card_value = models.CharField(max_length=255)
    confidence = models.IntegerField()
    mask = models.CharField(max_length=255)
    
    class Meta:
        db_table = 'access_logs'
        verbose_name = 'Log de Acesso'
        verbose_name_plural = 'Logs de Acesso'
        ordering = ['-time']
        indexes = [
            models.Index(fields=['time']),
            models.Index(fields=['event_type']),
            models.Index(fields=['device']),
            models.Index(fields=['user']),
            models.Index(fields=['portal']),
            models.Index(fields=['access_rule']),
            models.Index(fields=['device', 'identifier_id', 'time']),
        ]
        
        
        
    def __str__(self):
        return f"{self.time} - {self.event_type} - {self.device} - {self.identifier_id} - {self.user} - {self.portal} - {self.access_rule} - {self.qr_code} - {self.uhf_value} - {self.pin_value} - {self.card_value} - {self.confidence} - {self.mask}"