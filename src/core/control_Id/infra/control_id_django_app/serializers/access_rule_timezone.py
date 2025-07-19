from rest_framework import serializers
from src.core.control_Id.infra.control_id_django_app.models import AccessRuleTimeZone
 
class AccessRuleTimeZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessRuleTimeZone
        fields = ['id', 'access_rule_id', 'time_zone_id'] 
        read_only_fields = ['id']