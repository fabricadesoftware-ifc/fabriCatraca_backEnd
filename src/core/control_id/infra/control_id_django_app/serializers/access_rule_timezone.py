from rest_framework import serializers

from src.core.control_id.infra.control_id_django_app.models import (
    AccessRule,
    AccessRuleTimeZone,
    TimeZone,
)


class AccessRuleBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessRule
        fields = ["id", "name"]


class TimeZoneBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeZone
        fields = ["id", "name"]


class AccessRuleTimeZoneSerializer(serializers.ModelSerializer):
    access_rule = AccessRuleBasicSerializer(read_only=True)
    access_rule_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=AccessRule.objects.all(),
        source="access_rule",
        required=True,
    )
    time_zone = TimeZoneBasicSerializer(read_only=True)
    time_zone_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=TimeZone.objects.all(),
        source="time_zone",
        required=True,
    )

    class Meta:
        model = AccessRuleTimeZone
        fields = ["id", "access_rule", "access_rule_id", "time_zone", "time_zone_id"]
        read_only_fields = ["id"]
        validators = []
