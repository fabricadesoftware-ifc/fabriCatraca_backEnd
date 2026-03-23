from src.core.__seedwork__.infra import ControlIDSyncMixin
from django.db import transaction
from rest_framework.response import Response
from rest_framework import status


class UserAccessRuleSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance):
        response = self.create_objects("user_access_rules", [{
            "user_id": instance.user.id,
            "access_rule_id": instance.access_rule.id
        }])
        return response

    def update_in_catraca(self, instance):
        response = self.update_objects(
            "user_access_rules",
            {
                "user_id": instance.user.id,
                "access_rule_id": instance.access_rule.id
            },
            {"user_access_rules": {
                "user_id": instance.user.id,
                "access_rule_id": instance.access_rule.id
            }}
        )
        return response

    def delete_in_catraca(self, instance):
        response = self.destroy_objects(
            "user_access_rules",
            {"user_access_rules": {
                "user_id": instance.user.id,
                "access_rule_id": instance.access_rule.id
            }}
        )
        return response
