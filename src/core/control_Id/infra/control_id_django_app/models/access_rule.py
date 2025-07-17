from django.db import models

class AccessRule(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    type = models.IntegerField(default=1)  # 1 para permissão, 0 para bloqueio
    priority = models.IntegerField(default=0)

    def __str__(self):
        return self.name 