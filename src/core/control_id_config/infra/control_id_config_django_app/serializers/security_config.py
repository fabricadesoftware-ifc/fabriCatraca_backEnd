from rest_framework import serializers
from ..models import SecurityConfig


class SecurityConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityConfig
        fields = [
            'id', 'device',
            'password_only', 'hide_password_only', 'password_only_tip',
            'hide_name_on_identification',
            'denied_transaction_code',
            'send_code_when_not_identified', 'send_code_when_not_authorized',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']



