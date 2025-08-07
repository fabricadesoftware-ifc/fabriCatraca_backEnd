from src.core.__seedwork__.infra import ControlIDSyncMixin
from django.db import transaction
from rest_framework.response import Response
from rest_framework import status

class GroupAccessRulesSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance):
        response = self.create_objects("group_access_rules", [{
            "user_id": instance.user.id,
            "access_rule_id": instance.group.id
        }])
        return response
    
    def update_in_catraca(self, instance):
        response = self.update_objects(
            "group_access_rules",
            {
                "group_id": instance.user.id,
                "access_rule_id": instance.group.id
            },
            {"group_access_rules": {"id": instance.id}}
        )
        return response
    
    def delete_in_catraca(self, instance):
        response = self.destroy_objects(
            "group_access_rules",
            {"group_access_rules": {"id": instance.id}}
        )
        return response
    
    def sync_from_catraca(self):
        try:
            from src.core.control_Id.infra.control_id_django_app.models import GroupAccessRule
            
            catraca_objects = self.load_objects("group_access_rules")

            with transaction.atomic():
                GroupAccessRule.objects.all().delete()
                for data in catraca_objects:
                    GroupAccessRule.objects.create(**data)

            return Response({
                "success": True,
                "message": f"Sincronizados {len(catraca_objects)} grupos de acesso"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 
        
