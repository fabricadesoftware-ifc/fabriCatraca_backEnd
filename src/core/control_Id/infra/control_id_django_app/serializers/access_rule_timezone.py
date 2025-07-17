from rest_framework import serializers
from ..models.access_rule_timezone import AccessRuleTimeZone

class AccessRuleTimeZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessRuleTimeZone
        fields = ['access_rule_id', 'time_zone_id'] 