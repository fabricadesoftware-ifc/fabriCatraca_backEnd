from src.core.__seedwork__.infra import ControlIDSyncMixin
from rest_framework.response import Response
from src.core.__seedwork__.infra.mixins._typing import PortalAccessRuleLike
from src.core.__seedwork__.infra.types import PortalAccessRuleData

class PortalAccessRuleSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance: PortalAccessRuleLike) -> Response:
        payload: PortalAccessRuleData = {
            "portal_id": instance.portal_id,
            "access_rule_id": instance.access_rule.id,
        }
        response = self.create_objects("portal_access_rules", [payload])
        return response

    def update_in_catraca(self, instance: PortalAccessRuleLike) -> Response:
        payload: PortalAccessRuleData = {
            "portal_id": instance.portal_id,
            "access_rule_id": instance.access_rule.id,
        }
        response = self.update_objects(
            "portal_access_rules",
            payload,
            {"portal_access_rules": payload},
        )
        return response

    def delete_in_catraca(self, instance: PortalAccessRuleLike) -> Response:
        response = self.destroy_objects(
            "portal_access_rules",
            {"portal_access_rules": {
                "portal_id": instance.portal_id,
                "access_rule_id": instance.access_rule.id,
            }},
        )
        return response
