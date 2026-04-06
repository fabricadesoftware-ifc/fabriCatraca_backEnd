from typing import List, Optional

from src.core.__seedwork__.infra import ControlIDSyncMixin
from rest_framework.response import Response
from src.core.__seedwork__.infra.mixins._typing import GroupAccessRuleLike
from src.core.__seedwork__.infra.types import GroupAccessRuleData
from rest_framework import status

class GroupAccessRulesSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance: GroupAccessRuleLike, device_ids: Optional[List[int]] = None) -> Response:
        payload: GroupAccessRuleData = {
            "group_id": instance.group.id,
            "access_rule_id": instance.access_rule.id,
        }
        response = self.create_or_update_objects("group_access_rules", [payload], device_ids=device_ids)
        if response.status_code == status.HTTP_200_OK:
            response.status_code = status.HTTP_201_CREATED
        return response

    def update_in_catraca(self, instance: GroupAccessRuleLike, device_ids: Optional[List[int]] = None) -> Response:
        payload: GroupAccessRuleData = {
            "group_id": instance.group.id,
            "access_rule_id": instance.access_rule.id,
        }
        response = self.update_objects(
            "group_access_rules",
            payload,
            {"group_access_rules": payload},
            device_ids=device_ids,
        )
        return response

    def delete_in_catraca(self, instance: GroupAccessRuleLike, device_ids: Optional[List[int]] = None) -> Response:
        response = self.destroy_objects(
            "group_access_rules",
            {"group_access_rules": {
                "group_id": instance.group.id,
                "access_rule_id": instance.access_rule.id,
            }},
            device_ids=device_ids,
        )
        return response
