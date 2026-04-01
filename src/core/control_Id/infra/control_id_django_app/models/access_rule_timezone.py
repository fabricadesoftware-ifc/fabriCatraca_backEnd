from django.db import models
from src.core.__seedwork__.domain import BaseModel
from .access_rule import AccessRule
from .timezone import TimeZone

class AccessRuleTimeZone(BaseModel):
    access_rule = models.ForeignKey(AccessRule, on_delete=models.CASCADE)
    time_zone = models.ForeignKey(TimeZone, on_delete=models.CASCADE)

    class Meta(BaseModel.Meta):
        unique_together = ('access_rule', 'time_zone')
        verbose_name = "Regra de Acesso - Zona de Tempo"
        verbose_name_plural = "Regras de Acesso - Zonas de Tempo"

    def __str__(self):
        return f"Regra {self.access_rule} com zona {self.time_zone}"
