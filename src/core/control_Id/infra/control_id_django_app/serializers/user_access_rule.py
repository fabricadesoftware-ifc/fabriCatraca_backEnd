from rest_framework import serializers
from ..models.user_access_rule import UserAccessRule

class UserAccessRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAccessRule
        fields = ['user_id', 'access_rule_id'] 