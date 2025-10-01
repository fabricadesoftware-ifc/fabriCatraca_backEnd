from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from ..models import PushServerConfig
from ..serializers import PushServerConfigSerializer
from ..mixins import PushServerConfigSyncMixin


@extend_schema(tags=["Push Server Config"])
class PushServerConfigViewSet(PushServerConfigSyncMixin, viewsets.ModelViewSet):
    queryset = PushServerConfig.objects.all()
    serializer_class = PushServerConfigSerializer
    filterset_fields = ['device']
    search_fields = ['device__name', 'push_remote_address']
    ordering_fields = ['device__name', 'push_request_timeout', 'push_request_period']
    ordering = ['device__name']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        # Define o device alvo antes de enviar para a catraca
        self.set_device(instance.device)
        response = self.update_push_server_config_in_catraca(instance)

        if response.status_code != status.HTTP_200_OK:
            instance.delete()  # Reverte se falhar na catraca
            return response

        readback = self.sync_push_server_config_from_catraca()
        return readback if getattr(readback, 'status_code', 200) != 200 else Response(readback.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        
        # Define o device alvo antes de enviar para a catraca
        self.set_device(instance.device)
        response = self.update_push_server_config_in_catraca(instance)

        if response.status_code != status.HTTP_200_OK:
            return response

        # Retorna a configuração atualizada
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='sync-from-catraca')
    def sync_from_catraca(self, request):
        """
        Endpoint para sincronizar configurações do Push Server do dispositivo.
        Requer device_id no payload.
        """
        device_id = request.data.get('device_id')
        if not device_id:
            return Response(
                {"error": "device_id é obrigatório"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from src.core.control_Id.infra.control_id_django_app.models import Device
        try:
            device = Device.objects.get(id=device_id)
            self.set_device(device)
            return self.sync_push_server_config_from_catraca()
        except Device.DoesNotExist:
            return Response(
                {"error": "Device não encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )
