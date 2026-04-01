from django.db import models
from src.core.__seedwork__.domain import BaseModel


class Area(BaseModel):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta(BaseModel.Meta):
        verbose_name = "Area"
        verbose_name_plural = "Areas"
