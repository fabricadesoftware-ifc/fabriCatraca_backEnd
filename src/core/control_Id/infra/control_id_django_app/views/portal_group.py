from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status as http_status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from src.core.control_Id.infra.control_id_django_app.models import PortalGroup
from src.core.control_Id.infra.control_id_django_app.serializers.portal_group import (
    PortalGroupSerializer,
)


class PortalGroupViewSet(ModelViewSet):
    queryset = PortalGroup.objects.prefetch_related("devices").all()
    serializer_class = PortalGroupSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["is_active"]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])

    @action(detail=True, methods=["post"], url_path="assign-devices")
    def assign_devices(self, request, pk=None):
        group = self.get_object()
        device_ids = request.data.get("device_ids", [])
        if not isinstance(device_ids, list):
            return Response(
                {"error": "device_ids deve ser uma lista de IDs."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        group.devices.add(*device_ids)
        return Response({"success": True, "assigned": len(device_ids)})

    @action(detail=True, methods=["post"], url_path="remove-devices")
    def remove_devices(self, request, pk=None):
        group = self.get_object()
        device_ids = request.data.get("device_ids", [])
        if not isinstance(device_ids, list):
            return Response(
                {"error": "device_ids deve ser uma lista de IDs."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        group.devices.remove(*device_ids)
        return Response({"success": True, "removed": len(device_ids)})
