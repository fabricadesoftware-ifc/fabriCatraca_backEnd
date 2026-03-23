from src.core.__seedwork__.infra import ControlIDSyncMixin
from rest_framework.response import Response
from src.core.__seedwork__.infra.mixins._typing import TimeZoneLike
from src.core.__seedwork__.infra.types import TimeZonesData


class TimeZoneSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance: TimeZoneLike) -> Response:
        payload: TimeZonesData = {
            "id": instance.id,
            "name": instance.name,
        }
        response = self.create_objects("time_zones", [payload])
        return response

    def update_in_catraca(self, instance: TimeZoneLike) -> Response:
        payload: TimeZonesData = {
            "id": instance.id,
            "name": instance.name,
        }
        response = self.update_objects(
            "time_zones",
            payload,
            {"time_zones": {"id": instance.id}},
        )
        return response

    def delete_in_catraca(self, instance: TimeZoneLike) -> Response:
        response = self.destroy_objects(
            "time_zones",
            {"time_zones": {"id": instance.id}},
        )
        return response
