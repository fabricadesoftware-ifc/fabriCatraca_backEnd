from django.db import models
from src.core.user.infra.user_django_app.models import User
from .access_rule import AccessRule

class UserAccessRule(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    access_rule_id = models.ForeignKey(AccessRule, on_delete=models.CASCADE)

    def __str__(self):
        return f"Regra {self.access_rule_id} para usuário {self.user_id}" 