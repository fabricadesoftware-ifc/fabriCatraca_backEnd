from rest_framework import serializers
from .models import Template, TimeZone, TimeSpan, AccessRule, UserAccessRule, AccessRuleTimeZone, PortalAccessRule, Portal

class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = ['id', 'user', 'template']

class TimeZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeZone
        fields = ['id', 'name']

class TimeSpanSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeSpan
        fields = ['id', 'time_zone', 'start', 'end', 'sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'hol1', 'hol2', 'hol3']

class AccessRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessRule
        fields = ['id', 'name', 'type', 'priority']

class UserAccessRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAccessRule
        fields = ['user_id', 'access_rule_id']

class AccessRuleTimeZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessRuleTimeZone
        fields = ['access_rule', 'time_zone']

class PortalAccessRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortalAccessRule
        fields = ['portal_id', 'access_rule_id']

class PortalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Portal
        fields = ['id', 'name']