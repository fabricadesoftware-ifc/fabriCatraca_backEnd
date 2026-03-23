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
