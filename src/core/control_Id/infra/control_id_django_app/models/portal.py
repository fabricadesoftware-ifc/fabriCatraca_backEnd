from django.db import models
from src.core.__seedwork__.domain import BaseModel
from src.core.control_Id.infra.control_id_django_app.models import Area

class Portal(BaseModel):
    name = models.CharField(max_length=255)
    area_from = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='portals_from')
    area_to = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='portals_to')

    class Meta(BaseModel.Meta):
        verbose_name = "Portal"
        verbose_name_plural = "Portais"
        db_table = "portals"

    def __str__(self):
        return self.name
