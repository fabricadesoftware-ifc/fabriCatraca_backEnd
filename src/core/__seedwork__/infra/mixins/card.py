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
    
    def sync_from_catraca(self):
        try:
            from src.core.control_Id.infra.control_id_django_app.models import Card
            from src.core.user.infra.user_django_app.models import User
            
            catraca_objects = self.load_objects("cards")
            
            with transaction.atomic():
                Card.objects.all().delete()
                for data in catraca_objects:
                    Card.objects.create(
                        id=data["id"],
                        value=data["value"]
                    )

            return Response({
                "success": True,
                "message": f"Sincronizados {len(catraca_objects)} cards"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        