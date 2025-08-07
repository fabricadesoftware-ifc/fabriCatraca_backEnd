from src.core.__seedwork__.infra import ControlIDSyncMixin
from django.db import transaction
from rest_framework.response import Response
from rest_framework import status

class UserGroupsSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance):
        response = self.create_objects("user_groups", [{
            "user_id": instance.user.id,
            "group_id": instance.group.id
        }])
        return response
    
    def update_in_catraca(self, instance):
        response = self.update_objects(
            "user_groups",
            {
                "user_id": instance.user.id,
                "group_id": instance.group.id
            },
            {"user_groups": {"id": instance.id}}
        )
        return response
    
    def delete_in_catraca(self, instance):
        response = self.destroy_objects(
            "user_groups",
            {"user_groups": {"id": instance.id}}
        )
        return response
    
    def sync_from_catraca(self):
        try:
            from src.core.control_Id.infra.control_id_django_app.models import UserGroup
            
            catraca_objects = self.load_objects("user_groups")

            with transaction.atomic():
                UserGroup.objects.all().delete()
                for data in catraca_objects:
                    UserGroup.objects.create(**data)

            return Response({
                "success": True,
                "message": f"Sincronizados {len(catraca_objects)} usuários em grupos"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 
        
