from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from ..models import SystemConfig
from ..serializers import SystemConfigSerializer
from ..mixins import SystemConfigSyncMixin


@extend_schema(tags=["System Config"])
class SystemConfigViewSet(SystemConfigSyncMixin, viewsets.ModelViewSet):
    queryset = SystemConfig.objects.all()
    serializer_class = SystemConfigSerializer
    filterset_fields = ['device', 'auto_reboot_hour', 'online', 'web_server_enabled']
    search_fields = ['device__name']
    ordering_fields = ['device__name', 'auto_reboot_hour']
    ordering = ['device__name']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        # Define o device alvo antes de enviar para a catraca
        self.set_device(instance.device)
        response = self.update_system_config_in_catraca(instance)

        if response.status_code != status.HTTP_200_OK:
            instance.delete()  # Reverte se falhar na catraca
            return response

        readback = self.sync_system_config_from_catraca()
        return readback if getattr(readback, 'status_code', 200) != 200 else Response(readback.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        
        # Define o device alvo antes de enviar para a catraca
        self.set_device(instance.device)
        response = self.update_system_config_in_catraca(instance)

        if response.status_code != status.HTTP_200_OK:
            return response

        # Retorna a configuração atualizada (como o app control_Id faz)
        return Response(serializer.data)

    @extend_schema(
        summary="Sincronizar configurações do sistema da catraca",
        description="Sincroniza as configurações do sistema de um dispositivo específico com a catraca"
    )
    @action(detail=True, methods=['post'])
    def sync_from_catraca(self, request, pk=None):
        """Sincroniza configurações do sistema da catraca"""
        instance = self.get_object()
        self.set_device(instance.device)
        return self.sync_system_config_from_catraca(instance.device)


