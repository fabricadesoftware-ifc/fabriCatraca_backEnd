from rest_framework import serializers
from src.core.control_Id.infra.control_id_django_app.models import GroupAccessRule


class GroupAccessRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupAccessRule
        fields = ['id', 'group', 'access_rule']
        read_only_fields = ['id']
        