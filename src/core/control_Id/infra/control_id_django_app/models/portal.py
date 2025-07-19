from django.db import models
from src.core.control_Id.infra.control_id_django_app.models import Area

class Portal(models.Model):
    name = models.CharField(max_length=255)
    area_from_id = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='portals_from')
    area_to_id = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='portals_to')

    def __str__(self):
        return self.name 