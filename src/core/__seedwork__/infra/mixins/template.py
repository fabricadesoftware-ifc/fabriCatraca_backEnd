from src.core.__seedwork__.infra import ControlIDSyncMixin
from django.db import transaction
from rest_framework.response import Response
from rest_framework import status

class TemplateSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance):
        response = self.create_objects("templates", [{
            "id": instance.id,
            "user_id": instance.user.id,
            "template": instance.template,
            "finger_type": 0,  # dedo comum
            "finger_position": 0  # campo reservado
        }])
        return response

    def update_in_catraca(self, instance):
        response = self.update_objects(
            "templates",
            {
                "id": instance.id,
                "user_id": instance.user.id,
                "template": instance.template,
                "finger_type": 0,  # dedo comum
                "finger_position": 0  # campo reservado
            },
            {"templates": {"id": instance.id}}
        )
        return response

    def delete_in_catraca(self, instance):
        response = self.destroy_objects(
            "templates",
            {"templates": {"id": instance.id}}
        )
        return response

