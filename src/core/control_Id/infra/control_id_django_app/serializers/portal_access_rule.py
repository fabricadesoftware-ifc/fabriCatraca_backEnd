from rest_framework import serializers
from ..models.portal_access_rule import PortalAccessRule

class PortalAccessRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortalAccessRule
        fields = ['portal_id', 'access_rule_id'] 