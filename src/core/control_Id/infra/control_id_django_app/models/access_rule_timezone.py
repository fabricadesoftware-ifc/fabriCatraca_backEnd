from django.db import models
from .access_rule import AccessRule
from .timezone import TimeZone

class AccessRuleTimeZone(models.Model):
    access_rule_id = models.ForeignKey(AccessRule, on_delete=models.CASCADE)
    time_zone_id = models.ForeignKey(TimeZone, on_delete=models.CASCADE)

    def __str__(self):
        return f"Regra {self.access_rule_id} com zona {self.time_zone_id}" 