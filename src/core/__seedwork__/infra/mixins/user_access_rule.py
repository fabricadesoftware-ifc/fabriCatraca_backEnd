from typing import List, Optional

from src.core.__seedwork__.infra import ControlIDSyncMixin
from rest_framework.response import Response
from src.core.__seedwork__.infra.mixins._typing import UserAccessRuleLike
from src.core.__seedwork__.infra.types import UserAccessRulesData
from rest_framework import status


class UserAccessRuleSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance: UserAccessRuleLike, device_ids: Optional[List[int]] = None) -> Response:
        payload: UserAccessRulesData = {
            "user_id": instance.user.id,
            "access_rule_id": instance.access_rule.id,
        }
        response = self.create_or_update_objects("user_access_rules", [payload], device_ids=device_ids)
        if response.status_code == status.HTTP_200_OK:
            response.status_code = status.HTTP_201_CREATED
        return response

    def update_in_catraca(self, instance: UserAccessRuleLike, device_ids: Optional[List[int]] = None) -> Response:
        payload: UserAccessRulesData = {
            "user_id": instance.user.id,
            "access_rule_id": instance.access_rule.id,
        }
        response = self.update_objects(
            "user_access_rules",
            payload,
            {"user_access_rules": payload},
            device_ids=device_ids,
        )
        return response

    def delete_in_catraca(self, instance: UserAccessRuleLike, device_ids: Optional[List[int]] = None) -> Response:
        response = self.destroy_objects(
            "user_access_rules",
            {"user_access_rules": {
                "user_id": instance.user.id,
                "access_rule_id": instance.access_rule.id,
            }},
            device_ids=device_ids,
        )
        return response
