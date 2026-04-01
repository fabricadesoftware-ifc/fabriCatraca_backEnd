from django.db import models
from src.core.__seedwork__.domain import BaseModel
from .timezone import TimeZone

class TimeSpan(BaseModel):
    time_zone = models.ForeignKey(TimeZone, on_delete=models.CASCADE, related_name='spans')
    start = models.IntegerField(help_text='Segundos desde meia-noite')  # Segundos desde meia-noite
    end = models.IntegerField(help_text='Segundos desde meia-noite')
    sun = models.BooleanField(default=False)
    mon = models.BooleanField(default=False)
    tue = models.BooleanField(default=False)
    wed = models.BooleanField(default=False)
    thu = models.BooleanField(default=False)
    fri = models.BooleanField(default=False)
    sat = models.BooleanField(default=False)
    hol1 = models.BooleanField(default=False)
    hol2 = models.BooleanField(default=False)
    hol3 = models.BooleanField(default=False)

    class Meta(BaseModel.Meta):
        db_table = 'time_spans'
        verbose_name = "Intervalo de Tempo"
        verbose_name_plural = "Intervalos de Tempo"

    def __str__(self):
        return f"Intervalo {self.pk} da zona {self.time_zone.name}"
