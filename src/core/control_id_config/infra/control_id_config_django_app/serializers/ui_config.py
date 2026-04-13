from rest_framework import serializers

from ..models import UIConfig


class UIConfigSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)

    class Meta:
        model = UIConfig
        fields = ["id", "device", "device_name"]
        read_only_fields = ["id"]
        extra_kwargs = {
            "device": {"required": False},
        }
