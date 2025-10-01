from rest_framework import serializers
from ..models import MonitorConfig


class MonitorConfigSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source='device.name', read_only=True)

    class Meta:
        model = MonitorConfig
        fields = [
            'id', 'device', 'device_name',
            'request_timeout', 'hostname', 'port', 'path'
        ]
        read_only_fields = ['id']
        