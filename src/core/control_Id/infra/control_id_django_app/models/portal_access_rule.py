from django.db import models
from .portal import Portal
from .access_rule import AccessRule

class PortalAccessRule(models.Model):
    portal_id = models.ForeignKey(Portal, on_delete=models.CASCADE)
    access_rule_id = models.ForeignKey(AccessRule, on_delete=models.CASCADE)

    def __str__(self):
        return f"Regra {self.access_rule_id} no portal {self.portal_id}" 