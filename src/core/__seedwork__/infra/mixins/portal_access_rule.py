from src.core.__seedwork__.infra import ControlIDSyncMixin
from django.db import transaction
from rest_framework.response import Response
from rest_framework import status

class PortalAccessRuleSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance):
        response = self.create_objects("portal_access_rules", [{
            "portal_id": instance.portal_id,
            "access_rule_id": instance.access_rule.id
        }])
        return response

    def update_in_catraca(self, instance):
        response = self.update_objects(
            "portal_access_rules",
            {
                "portal_id": instance.portal_id,
                "access_rule_id": instance.access_rule.id
            },
            {"portal_access_rules": {
                "portal_id": instance.portal_id,
                "access_rule_id": instance.access_rule.id
            }}
        )
        return response

    def delete_in_catraca(self, instance):
        response = self.destroy_objects(
            "portal_access_rules",
            {"portal_access_rules": {
                "portal_id": instance.portal_id,
                "access_rule_id": instance.access_rule.id
            }}
        )
        return response

    def sync_from_catraca(self):
        try:
            from src.core.control_Id.infra.control_id_django_app.models import PortalAccessRule, AccessRule
            
            catraca_objects = self.load_objects("portal_access_rules")

            with transaction.atomic():
                PortalAccessRule.objects.all().delete()
                for data in catraca_objects:
                    access_rule = AccessRule.objects.get(id=data["access_rule_id"])
                    PortalAccessRule.objects.create(
                        portal_id=data["portal_id"],
                        access_rule=access_rule
                    )

            return Response({
                "success": True,
                "message": f"Sincronizadas {len(catraca_objects)} associações regra-portal"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 

