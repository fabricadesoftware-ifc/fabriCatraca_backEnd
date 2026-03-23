from src.core.__seedwork__.infra import ControlIDSyncMixin
from django.db import transaction
from rest_framework.response import Response
from rest_framework import status

from src.core.__seedwork__.infra import ControlIDSyncMixin

class TimeZoneSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance):
        response = self.create_objects("time_zones", [{
            "id": instance.id,
            "name": instance.name
        }])
        return response

    def update_in_catraca(self, instance):
        response = self.update_objects(
            "time_zones",
            {
                "id": instance.id,
                "name": instance.name
            },
            {"time_zones": {"id": instance.id}}
        )
        return response

    def delete_in_catraca(self, instance):
        response = self.destroy_objects(
            "time_zones",
            {"time_zones": {"id": instance.id}}
        )
        return response
