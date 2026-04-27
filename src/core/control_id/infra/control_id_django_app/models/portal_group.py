from django.db import models
from src.core.__seedwork__.domain import BaseModel


class PortalGroup(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    devices = models.ManyToManyField(
        "control_id_django_app.Device",
        blank=True,
        related_name="portal_groups",
    )

    class Meta(BaseModel.Meta):
        verbose_name = "Grupo de Portais"
        verbose_name_plural = "Grupos de Portais"
        db_table = "portal_groups"

    def __str__(self):
        return self.name

    def active_devices(self):
        """Return queryset of active devices in this group."""
        return self.devices.filter(deleted_at__isnull=True, is_active=True)
