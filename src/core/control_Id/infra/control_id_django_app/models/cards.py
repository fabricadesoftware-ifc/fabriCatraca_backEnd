from django.db import models
from src.core.user.infra.user_django_app.models import User


class Card(models.Model):
    value = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cards')
    devices = models.ManyToManyField('control_id_django_app.Device', related_name='cards', blank=True)
    
    class Meta:
        verbose_name = "Card"
        verbose_name_plural = "Cards"
        db_table = 'cards'
        
    def __str__(self):
        return f"{self.id} - {self.value} ({self.user.name})"
    