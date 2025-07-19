from rest_framework import serializers
from src.core.control_Id.infra.control_id_django_app.models import UserAccessRule

class UserAccessRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAccessRule
        fields = ['id', 'user_id', 'access_rule_id']
        read_only_fields = ['id']
