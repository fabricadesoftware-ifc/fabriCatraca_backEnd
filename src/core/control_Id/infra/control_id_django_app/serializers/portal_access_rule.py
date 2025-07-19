from rest_framework import serializers
from src.core.control_Id.infra.control_id_django_app.models import PortalAccessRule
 
class PortalAccessRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortalAccessRule
        fields = ['id','portal_id', 'access_rule_id']
        read_only_fields = ['id']