from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from ..models import MonitorConfig
from src.core.control_Id.infra.control_id_django_app.models import Device
from ..serializers import MonitorConfigSerializer
from ..mixins import MonitorConfigSyncMixin


@extend_schema(tags=["Monitor Config"])
class MonitorConfigViewSet(MonitorConfigSyncMixin, viewsets.ModelViewSet):
    queryset = MonitorConfig.objects.all()
    serializer_class = MonitorConfigSerializer
    filterset_fields = ['device']
    search_fields = ['device__name']
    ordering_fields = ['device__name']
    ordering = ['device__name']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        self.set_device(instance.device)
        response = self.update_monitor_config_in_catraca(instance)
        
        if response.status_code != status.HTTP_200_OK:
            instance.delete()  # Reverte se falhar na catraca
            return response

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        self.set_device(instance.device)
        response = self.update_monitor_config_in_catraca(instance)

        if response.status_code != status.HTTP_200_OK:
            return response

        # Retorna a configuração atualizada (como o app control_Id faz)
        return Response(serializer.data)

    @extend_schema(
        summary="Sincronizar configurações de monitor",
        description="Obtém configurações de monitor diretamente da catraca (sem persistência imediata)",
    )
    @action(detail=True, methods=['post'])
    def sync_from_catraca(self, request, pk=None):
        instance = self.get_object()
        self.set_device(instance.device)
        return self.sync_monitor_into_model()

    @extend_schema(
        summary="Obter bloco monitor direto da catraca",
        description="Retorna o payload bruto do bloco monitor via get_configuration.fcgi para inspeção",
    )
    @action(detail=True, methods=['get'], url_path='probe')
    def probe_from_catraca(self, request, pk=None):
        instance = self.get_object()
        self.set_device(instance.device)
        # Retorna o payload bruto e metadados de debug do mixin
        return self.sync_monitor_config_from_catraca()

    @extend_schema(
        summary="Sonde o bloco monitor por device_id",
        description="Retorna o payload bruto do bloco monitor para um device específico, sem exigir MonitorConfig criado",
    )
    @action(detail=False, methods=['get'], url_path='probe-by-device/(?P<device_id>\\d+)')
    def probe_by_device(self, request, device_id=None):
        try:
            device = Device.objects.get(id=device_id)
        except Device.DoesNotExist:
            return Response({"error": "Dispositivo não encontrado"}, status=status.HTTP_404_NOT_FOUND)
        self.set_device(device)
        # Retorna o payload bruto e metadados de debug do mixin
        return self.sync_monitor_config_from_catraca()


