from src.core.__seedwork__.infra import ControlIDSyncMixin
from django.db import transaction
from rest_framework.response import Response
from rest_framework import status

class CardSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance):
        response = self.create_objects("cards", [{
            "id": instance.id,
            "value": instance.value
        }])
        return response
    
    def update_in_catraca(self, instance):
        response = self.update_objects(
            "cards",
            {
                "id": instance.id,
                "value": instance.value
            },
            {"cards": {"id": instance.id}}
        )
        return response
    
    def delete_in_catraca(self, instance):
        response = self.destroy_objects(
            "cards",
            {"cards": {"id": instance.id}}
        )
        return response
    