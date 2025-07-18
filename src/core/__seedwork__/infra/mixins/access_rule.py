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

    def sync_from_catraca(self):
        try:
            from src.core.control_Id.infra.control_id_django_app.models import AccessRule
            
            catraca_objects = self.load_objects("access_rules")

            with transaction.atomic():
                AccessRule.objects.all().delete()
                for data in catraca_objects:
                    AccessRule.objects.create(
                        id=data["id"],
                        name=data["name"],
                        type=data["type"],
                        priority=data["priority"]
                    )

            return Response({
                "success": True,
                "message": f"Sincronizadas {len(catraca_objects)} regras de acesso"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)