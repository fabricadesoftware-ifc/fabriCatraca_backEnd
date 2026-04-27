from django.db import models
from src.core.__seedwork__.domain import BaseModel

class TimeZone(BaseModel):
    name = models.CharField(max_length=255)

    class Meta(BaseModel.Meta):
        db_table = 'time_zones'
        verbose_name = "Zona de Tempo"
        verbose_name_plural = "Zonas de Tempo"

    def __str__(self):
        return self.name
