from django.db import models
from src.core.__seedwork__.domain import BaseModel

class AccessRule(BaseModel):
    name = models.CharField(max_length=255)
    type = models.IntegerField(default=1)  # 1 para permissão, 0 para bloqueio
    priority = models.IntegerField(default=0)

    class Meta(BaseModel.Meta):
        verbose_name = "Regra de Acesso"
        verbose_name_plural = "Regras de Acesso"
        ordering = ["priority"]

    def __str__(self):
        return self.name
