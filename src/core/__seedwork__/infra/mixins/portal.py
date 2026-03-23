from src.core.__seedwork__.infra import ControlIDSyncMixin
from rest_framework.response import Response
from src.core.__seedwork__.infra.mixins._typing import PortalLike
from src.core.__seedwork__.infra.types import PortalData

class PortalSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance: PortalLike) -> Response:
        payload: PortalData = {
            "id": instance.id,
            "name": instance.name,
            "area_from_id": instance.area_from.id,
            "area_to_id": instance.area_to.id,
        }
        response = self.create_objects("portals", [payload])
        return response
    
    def update_in_catraca(self, instance: PortalLike) -> Response:
        payload: PortalData = {
            "id": instance.id,
            "name": instance.name,
            "area_from_id": instance.area_from.id,
            "area_to_id": instance.area_to.id,
        }
        response = self.update_objects(
            "portals",
            payload,
            {"portals": {"id": instance.id}},
        )
        return response
    
    def delete_in_catraca(self, instance: PortalLike) -> Response:
        response = self.destroy_objects(
            "portals",
            {"portals": {"id": instance.id}},
        )
        return response
    