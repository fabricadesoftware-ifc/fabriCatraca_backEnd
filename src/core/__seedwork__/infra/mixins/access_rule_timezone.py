from src.core.__seedwork__.infra import ControlIDSyncMixin
from django.db import transaction
from rest_framework.response import Response
from rest_framework import status


class AccessRuleTimeZoneSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance):
        response = self.create_objects("access_rule_time_zones", [{
            "access_rule_id": instance.access_rule.id,
            "time_zone_id": instance.time_zone.id
        }])
        return response

    def update_in_catraca(self, instance):
        response = self.update_objects(
            "access_rule_time_zones",
            {
                "access_rule_id": instance.access_rule.id,
                "time_zone_id": instance.time_zone.id
            },
            {"access_rule_time_zones": {
                "access_rule_id": instance.access_rule.id,
                "time_zone_id": instance.time_zone.id
            }}
        )
        return response

    def delete_in_catraca(self, instance):
        response = self.destroy_objects(
            "access_rule_time_zones",
            {"access_rule_time_zones": {
                "access_rule_id": instance.access_rule.id,
                "time_zone_id": instance.time_zone.id
            }}
        )
        return response

    def sync_from_catraca(self):
        try:
            from src.core.control_Id.infra.control_id_django_app.models import AccessRuleTimeZone, AccessRule, TimeZone
            
            catraca_objects = self.load_objects(
                "access_rule_time_zones",
                fields=["access_rule_id", "time_zone_id"],
                order_by=["access_rule_id", "time_zone_id"]
            )

            with transaction.atomic():
                AccessRuleTimeZone.objects.all().delete()
                for data in catraca_objects:
                    AccessRuleTimeZone.objects.create(
                        access_rule=AccessRule.objects.get(id=data["access_rule_id"]),
                        time_zone=TimeZone.objects.get(id=data["time_zone_id"])
                    )

            return Response({
                "success": True,
                "message": f"Sincronizadas {len(catraca_objects)} associações regra-zona"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

