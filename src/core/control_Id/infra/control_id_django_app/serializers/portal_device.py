from rest_framework import serializers
from src.core.control_Id.infra.control_id_django_app.models import PortalDevice


class PortalDeviceSerializer(serializers.ModelSerializer):
    portal_name = serializers.CharField(source="portal.name", read_only=True)
    device_name = serializers.CharField(source="device.name", read_only=True)
    portal_group_name = serializers.CharField(source="portal_group.name", read_only=True)

    class Meta:
        model = PortalDevice
        fields = [
            "id",
            "portal",
            "device",
            "portal_group",
            "portal_name",
            "device_name",
            "portal_group_name",
        ]
