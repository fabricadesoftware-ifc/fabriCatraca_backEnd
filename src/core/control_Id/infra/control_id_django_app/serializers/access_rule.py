from rest_framework import serializers
from src.core.control_Id.infra.control_id_django_app.models import AccessRule

class AccessRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessRule
        fields = ['id', 'name', 'type', 'priority']
        read_only_fields = ['id']