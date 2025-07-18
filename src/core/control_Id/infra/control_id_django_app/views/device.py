from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction

from src.core.control_Id.infra.control_id_django_app.models.device import Device
from src.core.control_Id.infra.control_id_django_app.serializers.device import DeviceSerializer

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
        return Response(serializer.data, status=status.HTTP_201_CREATED)

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
            
            return Response({
                "success": True,
                "message": "Conexão estabelecida com sucesso"
            })
        except Exception as e:
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def set_default(self, request, pk=None):
        """Define este dispositivo como padrão"""
        device = self.get_object()
        
        with transaction.atomic():
            # Remove o default de outros dispositivos
            Device.objects.filter(is_default=True).update(is_default=False)
            # Define este como default
            device.is_default = True
            device.save()
            
        serializer = self.get_serializer(device)
        return Response(serializer.data) 