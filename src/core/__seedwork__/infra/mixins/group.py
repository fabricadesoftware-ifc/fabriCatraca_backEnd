from src.core.__seedwork__.infra import ControlIDSyncMixin
from django.db import transaction
from rest_framework.response import Response
from rest_framework import status

class GroupSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance):
        response = self.create_objects("groups", [{
            "id": instance.id,
            "name": instance.name
        }])
        return response
    
    def update_in_catraca(self, instance):
        response = self.update_objects(
            "groups",
            {
                "id": instance.id,
                "name": instance.name
            },
            {"groups": {"id": instance.id}}
        )
        return response
    
    def delete_in_catraca(self, instance):
        response = self.destroy_objects(
            "groups",
            {"groups": {"id": instance.id}}
        )
        return response
    
    def sync_from_catraca(self):
        try:
            from src.core.control_Id.infra.control_id_django_app.models import CustomGroup
            
            catraca_objects = self.load_objects("groups")

            with transaction.atomic():
                CustomGroup.objects.all().delete()
                for data in catraca_objects:
                    CustomGroup.objects.create(**data)

            return Response({
                "success": True,
                "message": f"Sincronizados {len(catraca_objects)} grupos"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 
        
