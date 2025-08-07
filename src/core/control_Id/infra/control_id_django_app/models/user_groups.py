from django.db import models
from django.contrib.auth.models import Group
from src.core.user.infra.user_django_app.models import User

class UserGroup(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    
    class Meta:
        verbose_name = "Usuário em Grupo"
        verbose_name_plural = "Usuários em Grupos"
        
    def __str__(self):
        return f"{self.user.username} - {self.group.name}"