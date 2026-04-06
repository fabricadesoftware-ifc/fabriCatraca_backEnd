from rest_framework import serializers
from src.core.control_Id.infra.control_id_django_app.models import UserAccessRule, AccessRule
from src.core.user.infra.user_django_app.models import User
from ..models.portal_group import PortalGroup


class UserBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name']


class AccessRuleBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessRule
        fields = ['id', 'name']


class PortalGroupBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortalGroup
        fields = ['id', 'name']


class UserAccessRuleSerializer(serializers.ModelSerializer):
    # ✅ Saída: mostra os dados completos
    user = UserBasicSerializer(read_only=True)
    access_rule = AccessRuleBasicSerializer(read_only=True)
    portal_group = PortalGroupBasicSerializer(read_only=True)

    # ✅ Entrada: permite enviar apenas os ids
    user_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=User.objects.all(),
        source="user",
        required=True
    )
    access_rule_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=AccessRule.objects.all(),
        source="access_rule",
        required=True
    )
    portal_group_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=PortalGroup.objects.filter(is_active=True),
        source="portal_group",
        required=False,
        allow_null=True,
    )

    class Meta:
        model = UserAccessRule
        fields = ['id', 'user', 'user_id', 'access_rule', 'access_rule_id', 'portal_group', 'portal_group_id']
        read_only_fields = ['id']
