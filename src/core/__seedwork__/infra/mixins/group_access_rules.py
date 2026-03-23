from src.core.__seedwork__.infra import ControlIDSyncMixin
from rest_framework.response import Response
from src.core.__seedwork__.infra.mixins._typing import GroupAccessRuleLike
from src.core.__seedwork__.infra.types import GroupAccessRuleData

class GroupAccessRulesSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance: GroupAccessRuleLike) -> Response:
        payload: GroupAccessRuleData = {
            "group_id": instance.group.id,
            "access_rule_id": instance.access_rule.id,
        }
        response = self.create_objects("group_access_rules", [payload])
        return response
    
    def update_in_catraca(self, instance: GroupAccessRuleLike) -> Response:
        payload: GroupAccessRuleData = {
            "group_id": instance.group.id,
            "access_rule_id": instance.access_rule.id,
        }
        response = self.update_objects(
            "group_access_rules",
            payload,
            {"group_access_rules": payload},
        )
        return response
    
    def delete_in_catraca(self, instance: GroupAccessRuleLike) -> Response:
        response = self.destroy_objects(
            "group_access_rules",
            {"group_access_rules": {
                "group_id": instance.group.id,
                "access_rule_id": instance.access_rule.id,
            }},
        )
        return response
    