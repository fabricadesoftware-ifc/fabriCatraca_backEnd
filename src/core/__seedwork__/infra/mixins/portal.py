from src.core.__seedwork__.infra import ControlIDSyncMixin
from django.db import transaction
from rest_framework.response import Response
from rest_framework import status

class PortalSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance):
        response = self.create_objects("portals", [{
            "id": instance.id,
            "name": instance.name,
            "area_from_id": instance.area_from.id,
            "area_to_id": instance.area_to.id
        }])
        return response
    
    def update_in_catraca(self, instance):
        response = self.update_objects(
            "portals",
            {
                "id": instance.id,
                "name": instance.name,
                "area_from_id": instance.area_from.id,
                "area_to_id": instance.area_to.id
            },
            {"portals": {"id": instance.id}}
        )
        return response
    
    def delete_in_catraca(self, instance):
        response = self.destroy_objects(
            "portals",
            {"portals": {"id": instance.id}}
        )
        return response
    