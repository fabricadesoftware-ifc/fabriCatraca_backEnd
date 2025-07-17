from rest_framework import serializers
from ..models.access_rule import AccessRule

class AccessRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessRule
        fields = ['id', 'name', 'type', 'priority'] 