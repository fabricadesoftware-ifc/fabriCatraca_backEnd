from django.db import models
from src.core.__seedwork__.domain import BaseModel
from src.core.user.infra.user_django_app.models import User


class Card(BaseModel):
    value = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cards')

    class Meta(BaseModel.Meta):
        verbose_name = "Card"
        verbose_name_plural = "Cards"
        db_table = 'cards'

    def __str__(self):
        return f"{self.pk} - {self.value} ({self.user.name})"

