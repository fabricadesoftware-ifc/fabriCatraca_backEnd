from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from ..models import SecurityConfig
from ..serializers import SecurityConfigSerializer
from ..mixins import SecurityConfigSyncMixin


@extend_schema(tags=["Security Config"])
class SecurityConfigViewSet(SecurityConfigSyncMixin, viewsets.ModelViewSet):
    queryset = SecurityConfig.objects.all()
    serializer_class = SecurityConfigSerializer
    filterset_fields = ['device', 'password_only', 'hide_password_only']
    search_fields = ['device__name']
    ordering_fields = ['device__name']
    ordering = ['device__name']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        self.set_device(instance.device)
        response = self.update_security_config_in_catraca(instance)

        if response.status_code != status.HTTP_200_OK:
            instance.delete()  # Reverte se falhar na catraca
            return response

        readback = self.sync_security_config_from_catraca()
        return readback if getattr(readback, 'status_code', 200) != 200 else Response(readback.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        self.set_device(instance.device)
        response = self.update_security_config_in_catraca(instance)

        if response.status_code != status.HTTP_200_OK:
            return response

        # Retorna a configuração atualizada (como o app control_Id faz)
        return Response(serializer.data)

    @extend_schema(
        summary="Sincronizar configurações de segurança da catraca",
        description="Sincroniza as configurações de segurança de um dispositivo específico com a catraca"
    )
    @action(detail=True, methods=['post'])
    def sync_from_catraca(self, request, pk=None):
        """Sincroniza configurações de segurança da catraca"""
        instance = self.get_object()
        self.set_device(instance.device)
        return self.sync_security_config_from_catraca(instance.device)


