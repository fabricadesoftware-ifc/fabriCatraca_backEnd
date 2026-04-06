from django.db import models
from src.core.__seedwork__.domain import BaseModel
from src.core.control_Id.infra.control_id_django_app.models import CustomGroup, AccessRule
from .portal_group import PortalGroup


class GroupAccessRule(BaseModel):
    group = models.ForeignKey(CustomGroup, on_delete=models.CASCADE)
    access_rule = models.ForeignKey(AccessRule, on_delete=models.CASCADE)
    portal_group = models.ForeignKey(
        PortalGroup,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="group_access_rules",
        help_text="Se definido, a regra se aplica apenas as catracas deste grupo.",
    )

    def __str__(self):
        pg = f" ({self.portal_group})" if self.portal_group else ""
        return f"{self.group.name} - {self.access_rule.name}{pg}"

    class Meta(BaseModel.Meta):
        verbose_name = "Grupo de Acesso"
        verbose_name_plural = "Grupos de Acesso"
        db_table = "group_access_rules"
        unique_together = ('group', 'access_rule', 'portal_group')
