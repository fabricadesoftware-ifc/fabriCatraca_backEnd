from rest_framework import serializers
from ..models import SystemConfig


class SystemConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemConfig
        fields = [
            'id', 'device',
            'auto_reboot_hour', 'auto_reboot_minute',
            'clear_expired_users', 'keep_user_image',
            'url_reboot_enabled', 'web_server_enabled',
            'online', 'local_identification',
            'language', 'daylight_savings_time_start', 'daylight_savings_time_end',
            'catra_timeout',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']



