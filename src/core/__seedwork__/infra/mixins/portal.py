from src.core.__seedwork__.infra import ControlIDSyncMixin
from django.db import transaction
from rest_framework.response import Response
from rest_framework import status

class PortalSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance):
        response = self.create_objects("portals", [{
            "id": instance.id,
            "name": instance.name
        }])
        return response
    
    def update_in_catraca(self, instance):
        response = self.update_objects(
            "portals",
            {
                "id": instance.id,
                "name": instance.name
            },
            {"portals": {"id": instance.id}}
        )
        return response
    
    def delete_in_catraca(self, instance):
        response = self.destroy_objects(
            "portals",
            {"portals": {"id": instance.id}}
        )
        return response
    
    def sync_from_catraca(self):
        try:
            from src.core.control_Id.infra.control_id_django_app.models import Portal
            
            catraca_objects = self.load_objects("portals")

            with transaction.atomic():
                Portal.objects.all().delete()
                for data in catraca_objects:
                    Portal.objects.create(**data)

            return Response({
                "success": True,
                "message": f"Sincronizados {len(catraca_objects)} portais"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 
        
