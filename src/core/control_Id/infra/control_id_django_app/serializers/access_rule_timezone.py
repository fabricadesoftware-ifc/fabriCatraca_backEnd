from src.core.control_Id.infra.control_id_django_app.models import AccessRule, AccessRuleTimeZone, TimeZone
from rest_framework import serializers


class AccessRuleBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessRule
        fields = ['id', 'name']


class TimeZoneBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeZone
        fields = ['id', 'name']


class AccessRuleTimeZoneSerializer(serializers.ModelSerializer):
    access_rule = AccessRuleBasicSerializer(read_only=True)  # saída
    access_rule_id = serializers.PrimaryKeyRelatedField(  # entrada
        write_only=True,
        queryset=AccessRule.objects.all(),
        source="access_rule"
    )

    time_zone = TimeZoneBasicSerializer(read_only=True)
    time_zone_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=TimeZone.objects.all(),
        source="time_zone"
    )

    class Meta:
        model = AccessRuleTimeZone
        fields = ["id", "access_rule", "access_rule_id", "time_zone", "time_zone_id"]
        read_only_fields = ["id"]
