from rest_framework import serializers
from ..models import HardwareConfig


class HardwareConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = HardwareConfig
        fields = [
            'id', 'device',
            'beep_enabled', 'bell_enabled', 'bell_relay',
            'ssh_enabled',
            'relayN_enabled', 'relayN_timeout', 'relayN_auto_close',
            'door_sensorN_enabled', 'door_sensorN_idle', 'doorN_interlock',
            'exception_mode', 'doorN_exception_mode',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


