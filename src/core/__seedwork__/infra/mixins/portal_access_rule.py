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
