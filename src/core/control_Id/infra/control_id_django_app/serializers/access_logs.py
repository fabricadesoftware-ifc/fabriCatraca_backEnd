from rest_framework import serializers
from src.core.control_Id.infra.control_id_django_app.models import AccessLogs

class AccessLogsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessLogs
        fields = ['id', 'time', 'event_type', 'device', 'identifier_id', 'user', 'portal', 'access_rule', 'qr_code', 'uhf_value', 'pin_value', 'card_value', 'confidence', 'mask']
        read_only_fields = ['id']


