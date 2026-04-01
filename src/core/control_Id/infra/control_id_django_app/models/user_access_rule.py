from django.db import models
from src.core.__seedwork__.domain import BaseModel
from src.core.user.infra.user_django_app.models import User
from .access_rule import AccessRule

class UserAccessRule(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    access_rule = models.ForeignKey(AccessRule, on_delete=models.CASCADE)

    class Meta(BaseModel.Meta):
        db_table = 'user_access_rules'
        verbose_name = "Regra de Acesso do Usuário"
        verbose_name_plural = "Regras de Acesso dos Usuários"

    def __str__(self):
        return f"Regra {self.access_rule} para usuário {self.user}"
