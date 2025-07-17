from django.db import models
from src.core.user.infra.user_django_app.models import User

class Template(models.Model):
    id = models.IntegerField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='templates')
    template = models.TextField()  # Dados da biometria em base64
    finger_type = models.IntegerField(default=0)  # 0 para dedo comum
    finger_position = models.IntegerField(default=0)  # Campo reservado

    def __str__(self):
        return f"Biometria {self.id} do usuário {self.user.name}"

class TimeZone(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class TimeSpan(models.Model):
    id = models.IntegerField(primary_key=True)
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

class AccessRule(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    type = models.IntegerField(default=1)  # 1 para permissão, 0 para bloqueio
    priority = models.IntegerField(default=0)

    def __str__(self):
        return self.name

class Portal(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class UserAccessRule(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    access_rule = models.ForeignKey(AccessRule, on_delete=models.CASCADE)

    def __str__(self):
        return f"Regra {self.access_rule} para usuário {self.user}"

class AccessRuleTimeZone(models.Model):
    access_rule = models.ForeignKey(AccessRule, on_delete=models.CASCADE)
    time_zone = models.ForeignKey(TimeZone, on_delete=models.CASCADE)

    def __str__(self):
        return f"Regra {self.access_rule} com zona {self.time_zone}"

class PortalAccessRule(models.Model):
    portal = models.ForeignKey(Portal, on_delete=models.CASCADE)
    access_rule = models.ForeignKey(AccessRule, on_delete=models.CASCADE)

    def __str__(self):
        return f"Regra {self.access_rule} no portal {self.portal}"