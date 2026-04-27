from rest_framework import serializers
from src.core.control_id.infra.control_id_django_app.models import PortalGroup, Device
from .device import DeviceSerializer


class PortalGroupSerializer(serializers.ModelSerializer):
    devices = DeviceSerializer(many=True, read_only=True)
    device_ids = serializers.PrimaryKeyRelatedField(
        queryset=Device.objects.filter(deleted_at__isnull=True),
        many=True,
        write_only=True,
        required=False,
    )

    class Meta:
        model = PortalGroup
        fields = [
            "id",
            "name",
            "description",
            "is_active",
            "devices",
            "device_ids",
        ]
        read_only_fields = ["id"]

    def update(self, instance, validated_data):
        device_ids = validated_data.pop("device_ids", None)
        instance = super().update(instance, validated_data)
        if device_ids is not None:
            instance.devices.set(device_ids)
        return instance

    def create(self, validated_data):
        device_ids = validated_data.pop("device_ids", None)
        instance = super().create(validated_data)
        if device_ids:
            instance.devices.set(device_ids)
        return instance
