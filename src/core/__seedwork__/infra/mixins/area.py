from src.core.__seedwork__.infra import ControlIDSyncMixin
from django.db import transaction
from rest_framework.response import Response
from rest_framework import status

class AreaSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance):
        response = self.create_objects("areas", [{
            "id": instance.id,
            "name": instance.name
        }])
        return response
    
    def update_in_catraca(self, instance):
        response = self.update_objects(
            "areas",
            {
                "id": instance.id,
                "name": instance.name
            },
            {"areas": {"id": instance.id}}
        )
        return response
    
    def delete_in_catraca(self, instance):
        response = self.destroy_objects(
            "areas",
            {"areas": {"id": instance.id}}
        )
        return response
    