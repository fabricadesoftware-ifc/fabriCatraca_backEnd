from src.core.__seedwork__.infra import ControlIDSyncMixin
from rest_framework.response import Response
from src.core.__seedwork__.infra.mixins._typing import AreaLike
from src.core.__seedwork__.infra.types import AreasData

class AreaSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance: AreaLike) -> Response:
        payload: AreasData = {
            "id": instance.id,
            "name": instance.name,
        }
        response = self.create_objects("areas", [payload])
        return response
    
    def update_in_catraca(self, instance: AreaLike) -> Response:
        payload: AreasData = {
            "id": instance.id,
            "name": instance.name,
        }
        response = self.update_objects(
            "areas",
            payload,
            {"areas": {"id": instance.id}},
        )
        return response
    
    def delete_in_catraca(self, instance: AreaLike) -> Response:
        response = self.destroy_objects(
            "areas",
            {"areas": {"id": instance.id}},
        )
        return response
    