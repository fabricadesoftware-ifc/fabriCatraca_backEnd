from rest_framework import serializers

from src.core.control_id.infra.control_id_django_app.models import (
    AccessRule,
    Portal,
    PortalAccessRule,
)


class PortalBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Portal
        fields = ["id", "name"]


class AccessRuleBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessRule
        fields = ["id", "name"]


class PortalAccessRuleSerializer(serializers.ModelSerializer):
    portal = PortalBasicSerializer(read_only=True)
    access_rule = AccessRuleBasicSerializer(read_only=True)
    portal_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=Portal.objects.all(),
        source="portal",
        required=True,
    )
    access_rule_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=AccessRule.objects.all(),
        source="access_rule",
        required=True,
    )

    class Meta:
        model = PortalAccessRule
        fields = ["id", "portal", "portal_id", "access_rule", "access_rule_id"]
        read_only_fields = ["id"]
        validators = []
