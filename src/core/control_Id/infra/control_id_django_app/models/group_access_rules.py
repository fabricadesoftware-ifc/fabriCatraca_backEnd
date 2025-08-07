from django.db import models
from src.core.control_Id.infra.control_id_django_app.models import CustomGroup, AccessRule


class GroupAccessRule(models.Model):
    group = models.ForeignKey(CustomGroup, on_delete=models.CASCADE)
    access_rule = models.ForeignKey(AccessRule, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.group.name} - {self.access_rule.name}"
    
    class Meta:
        verbose_name = "Grupo de Acesso"
        verbose_name_plural = "Grupos de Acesso"
        db_table = "group_access_rules"
        unique_together = ('group', 'access_rule')
        