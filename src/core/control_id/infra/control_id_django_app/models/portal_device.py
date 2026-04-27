from django.db import models
from django.core.exceptions import ValidationError
from src.core.__seedwork__.domain import BaseModel
from src.core.control_id.infra.control_id_django_app.models import Portal, Device
from src.core.control_id.infra.control_id_django_app.models.portal_group import (
    PortalGroup,
)


class PortalDevice(BaseModel):
    portal = models.ForeignKey(
        Portal, on_delete=models.CASCADE, related_name="portal_devices"
    )
    device = models.ForeignKey(
        Device, on_delete=models.CASCADE, related_name="portal_devices"
    )
    portal_group = models.ForeignKey(
        PortalGroup, on_delete=models.CASCADE, related_name="portal_devices"
    )

    class Meta(BaseModel.Meta):
        verbose_name = "Portal-Dispositivo"
        verbose_name_plural = "Portal-Dispositivos"
        db_table = "portal_device_mappings"
        constraints = [
            models.UniqueConstraint(
                fields=["portal", "device"],
                name="unique_portal_device",
            ),
        ]

    def clean(self):
        super().clean()
        # Validate device doesn't belong to another PortalGroup
        if self.pk:
            # On update, check other entries
            existing = PortalDevice.objects.exclude(pk=self.pk).filter(
                device=self.device,
                portal_group=self.portal_group,
            )
            if existing.exists():
                raise ValidationError(
                    "Este dispositivo já está vinculado a este mesmo grupo de portais."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.portal.name} → {self.device.name} ({self.portal_group.name})"
