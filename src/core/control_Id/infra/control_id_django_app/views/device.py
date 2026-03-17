from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction

from src.core.control_Id.infra.control_id_django_app.device_registry_sync import (
    DeviceRegistrySyncService,
)
from src.core.control_Id.infra.control_id_django_app.models.device import Device
from src.core.control_Id.infra.control_id_django_app.serializers.device import DeviceSerializer
from drf_spectacular.utils import extend_schema

@extend_schema(tags=["Devices"])
class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    filterset_fields = ['name', 'ip', 'is_active', 'is_default']
    search_fields = ['name', 'ip']
    ordering_fields = ['name', 'ip', 'is_active', 'is_default']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Se está criando como default, remove o default de outros
        if serializer.validated_data.get('is_default'):
            Device.objects.filter(is_default=True).update(is_default=False)
            
        instance = serializer.save()
        DeviceRegistrySyncService().sync_all_active_devices()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data.get('is_default'):
            Device.objects.filter(is_default=True).exclude(id=instance.id).update(is_default=False)

        instance = serializer.save()
        DeviceRegistrySyncService().sync_all_active_devices()
        return Response(self.get_serializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        DeviceRegistrySyncService().sync_all_active_devices()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def test_connection(self, request, pk=None):
        """Testa a conexão com o dispositivo"""
        device = self.get_object()
        
        try:
            # Tenta fazer login
            from src.core.__seedwork__.infra import ControlIDSyncMixin
            mixin = ControlIDSyncMixin()
            mixin.set_device(device)
            mixin.login()
            
            
            Device.objects.filter(id=device.id).update(is_active=True)
            return Response({
                "success": True,
                "message": "Conexão estabelecida com sucesso"
            })
        except Exception as e:
            Device.objects.filter(id=device.id).update(is_active=False)
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def sync_registry(self, request):
        """Sincroniza a tabela devices em todas as catracas ativas."""
        result = DeviceRegistrySyncService().sync_all_active_devices()
        return Response(result, status=status.HTTP_200_OK if result.get("success") else status.HTTP_207_MULTI_STATUS)
