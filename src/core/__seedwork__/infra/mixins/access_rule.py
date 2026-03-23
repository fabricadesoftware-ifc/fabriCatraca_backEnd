from src.core.__seedwork__.infra.catraca_sync import ControlIDSyncMixin
from django.db import transaction
from rest_framework.response import Response
from rest_framework import status

class AccessRuleSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance):
        response = self.create_objects("access_rules", [{
            "id": instance.id,
            "name": instance.name,
            "type": instance.type,
            "priority": instance.priority
        }])
        return response

    def update_in_catraca(self, instance):
        response = self.update_objects(
            "access_rules",
            {
                "id": instance.id,
                "name": instance.name,
                "type": instance.type,
                "priority": instance.priority
            },
            {"access_rules": {"id": instance.id}}
        )
        return response

    def delete_in_catraca(self, instance):
        response = self.destroy_objects(
            "access_rules",
            {"access_rules": {"id": instance.id}}
        )
        return response