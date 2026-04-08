from src.core.__seedwork__.infra import ControlIDSyncMixin
from rest_framework.response import Response
from rest_framework import status
from src.core.__seedwork__.infra.mixins._typing import AccessRuleTimeZoneLike
from src.core.__seedwork__.infra.types import AccessRuleTimeZoneData


class AccessRuleTimeZoneSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance: AccessRuleTimeZoneLike) -> Response:
        payload: AccessRuleTimeZoneData = {
            "access_rule_id": instance.access_rule.id,
            "time_zone_id": instance.time_zone.id,
        }
        response = self.create_or_update_objects("access_rule_time_zones", [payload])
        if response.status_code == status.HTTP_200_OK:
            response.status_code = status.HTTP_201_CREATED
        return response

    def update_in_catraca(self, instance: AccessRuleTimeZoneLike) -> Response:
        payload: AccessRuleTimeZoneData = {
            "access_rule_id": instance.access_rule.id,
            "time_zone_id": instance.time_zone.id,
        }
        response = self.update_objects(
            "access_rule_time_zones",
            payload,
            {"access_rule_time_zones": payload},
        )
        return response

    def delete_in_catraca(self, instance: AccessRuleTimeZoneLike) -> Response:
        response = self.destroy_objects(
            "access_rule_time_zones",
            {
                "access_rule_time_zones": {
                    "access_rule_id": instance.access_rule.id,
                    "time_zone_id": instance.time_zone.id,
                }
            },
        )
        return response
