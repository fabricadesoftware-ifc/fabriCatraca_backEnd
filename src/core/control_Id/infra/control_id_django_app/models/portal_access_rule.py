from django.db import models
from src.core.__seedwork__.domain import BaseModel
from .portal import Portal
from .access_rule import AccessRule

class PortalAccessRule(BaseModel):
    portal = models.ForeignKey(Portal, on_delete=models.CASCADE)
    access_rule = models.ForeignKey(AccessRule, on_delete=models.CASCADE)

    class Meta(BaseModel.Meta):
        unique_together = ('portal', 'access_rule')
        verbose_name = "Regra de Acesso - Portal"
        verbose_name_plural = "Regras de Acesso - Portais"

    def __str__(self):
        return f"Regra {self.access_rule} no portal {self.portal}"
