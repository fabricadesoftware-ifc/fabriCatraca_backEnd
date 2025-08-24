from django.db import models
from .portal import Portal
from .access_rule import AccessRule

class PortalAccessRule(models.Model):
    portal = models.ForeignKey(Portal, on_delete=models.CASCADE)
    access_rule = models.ForeignKey(AccessRule, on_delete=models.CASCADE)

    def __str__(self):
        return f"Regra {self.access_rule} no portal {self.portal}" 