from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend

from src.core.control_Id.infra.control_id_django_app.models import PortalDevice
from src.core.control_Id.infra.control_id_django_app.serializers.portal_device import (
    PortalDeviceSerializer,
)


class PortalDeviceViewSet(ModelViewSet):
    serializer_class = PortalDeviceSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["portal", "device", "portal_group"]

    def get_queryset(self):
        return PortalDevice.objects.filter(deleted_at__isnull=True).prefetch_related(
            "portal", "device", "portal_group"
        )
