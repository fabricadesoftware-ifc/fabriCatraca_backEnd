from rest_framework import serializers
from src.core.control_Id.infra.control_id_django_app.models import CustomGroup, GroupAccessRule
from src.core.user.infra.user_django_app.models import User
from .group_access_rules import GroupAccessRuleSerializer

class CustomGroupSerializer(serializers.ModelSerializer):
    users = serializers.SerializerMethodField()
    access_rules = serializers.SerializerMethodField()
    

    class Meta:
        model = CustomGroup
        fields = ['id', 'name', 'users', 'access_rules']
        read_only_fields = ['id']

    def get_users(self, obj):
        return [{'id': user.id, 'name': user.name} for user in User.objects.filter(usergroup__group=obj)]

    def get_access_rules(self, obj):
        queryset = GroupAccessRule.objects.filter(group=obj).select_related('group', 'access_rule')
        return GroupAccessRuleSerializer(queryset, many=True).data
    