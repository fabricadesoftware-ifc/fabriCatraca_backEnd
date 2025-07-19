from django.db import models
from .timezone import TimeZone

class TimeSpan(models.Model):
    time_zone = models.ForeignKey(TimeZone, on_delete=models.CASCADE, related_name='spans')
    start = models.IntegerField()  # Segundos desde meia-noite
    end = models.IntegerField()
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

    def __str__(self):
        return f"Intervalo {self.id} da zona {self.time_zone.name}" 