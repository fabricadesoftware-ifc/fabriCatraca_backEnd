from typing import cast

from src.core.__seedwork__.infra.catraca_sync import ControlIDSyncMixin
from rest_framework.response import Response
from src.core.__seedwork__.infra.mixins._typing import AccessRuleLike
from src.core.__seedwork__.infra.types.access_rules import AccessRuleData, AccessRuleType

class AccessRuleSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance: AccessRuleLike) -> Response:
        payload: AccessRuleData = {
            "id": instance.id,
            "name": instance.name,
            "type": cast(AccessRuleType, instance.type),
            "priority": instance.priority,
        }
        response = self.create_objects("access_rules", [payload])
        return response

    def update_in_catraca(self, instance: AccessRuleLike) -> Response:
        payload: AccessRuleData = {
            "id": instance.id,
            "name": instance.name,
            "type": cast(AccessRuleType, instance.type),
            "priority": instance.priority,
        }
        response = self.update_objects(
            "access_rules",
            payload,
            {"access_rules": {"id": instance.id}},
        )
        return response

    def delete_in_catraca(self, instance: AccessRuleLike) -> Response:
        response = self.destroy_objects(
            "access_rules",
            {"access_rules": {"id": instance.id}},
        )
        return response