from src.core.__seedwork__.infra import ControlIDSyncMixin
from rest_framework.response import Response
from src.core.__seedwork__.infra.mixins._typing import GroupLike
from src.core.__seedwork__.infra.types import GroupsData

class GroupSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance: GroupLike) -> Response:
        payload: GroupsData = {
            "id": instance.id,
            "name": instance.name,
        }
        response = self.create_objects("groups", [payload])
        return response
    
    def update_in_catraca(self, instance: GroupLike) -> Response:
        payload: GroupsData = {
            "id": instance.id,
            "name": instance.name,
        }
        response = self.update_objects(
            "groups",
            payload,
            {"groups": {"id": instance.id}},
        )
        return response
    
    def delete_in_catraca(self, instance: GroupLike) -> Response:
        response = self.destroy_objects(
            "groups",
            {"groups": {"id": instance.id}},
        )
        return response
    