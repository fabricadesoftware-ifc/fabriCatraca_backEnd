from rest_framework import serializers
from ..models import UIConfig


class UIConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = UIConfig
        fields = [
            'id', 'device',
            'screen_always_on',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']



