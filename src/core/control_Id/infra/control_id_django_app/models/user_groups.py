from django.db import models
from src.core.user.infra.user_django_app.models import User
from src.core.control_Id.infra.control_id_django_app.models import CustomGroup

class UserGroup(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(CustomGroup, on_delete=models.CASCADE)
    
    class Meta:
        verbose_name = "Usuário em Grupo"
        verbose_name_plural = "Usuários em Grupos"
        constraints = [
            models.UniqueConstraint(fields=['user', 'group'], name='unique_user_group')
        ]
        
    def __str__(self):
        return f"{self.user.username} - {self.group.name}"