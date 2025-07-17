from django.db import models
from src.core.user.infra.user_django_app.models import User

class Template(models.Model):
    id = models.IntegerField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='templates', db_column='user_id')
    template = models.TextField()  # Dados da biometria em base64
    finger_type = models.IntegerField(default=0)  # 0 para dedo comum, 1 para dedo de pânico
    finger_position = models.IntegerField(default=0)  # Campo reservado

    def __str__(self):
        return f"Biometria {self.id} do usuário {self.user.name}"

    class Meta:
        db_table = 'templates'
        managed = False  # Indica que a tabela é gerenciada pela catraca 