from django.db import models
from src.core.user.infra.user_django_app.models import User


class Card(models.Model):
    value = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        verbose_name = "Card"
        verbose_name_plural = "Cards"
        
    def __str__(self):
        return f"{self.id} - {self.value}"
    