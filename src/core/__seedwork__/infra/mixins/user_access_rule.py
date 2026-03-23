from src.core.__seedwork__.infra import ControlIDSyncMixin
from rest_framework.response import Response
from src.core.__seedwork__.infra.mixins._typing import UserAccessRuleLike
from src.core.__seedwork__.infra.types import UserAccessRulesData


class UserAccessRuleSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance: UserAccessRuleLike) -> Response:
        payload: UserAccessRulesData = {
            "user_id": instance.user.id,
            "access_rule_id": instance.access_rule.id,
        }
        response = self.create_objects("user_access_rules", [payload])
        return response

    def update_in_catraca(self, instance: UserAccessRuleLike) -> Response:
        payload: UserAccessRulesData = {
            "user_id": instance.user.id,
            "access_rule_id": instance.access_rule.id,
        }
        response = self.update_objects(
            "user_access_rules",
            payload,
            {"user_access_rules": payload},
        )
        return response

    def delete_in_catraca(self, instance: UserAccessRuleLike) -> Response:
        response = self.destroy_objects(
            "user_access_rules",
            {"user_access_rules": {
                "user_id": instance.user.id,
                "access_rule_id": instance.access_rule.id,
            }},
        )
        return response
