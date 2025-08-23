from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from src.core.control_Id.infra.control_id_django_app.models import AccessLogs
from src.core.control_Id.infra.control_id_django_app.serializers import AccessLogsSerializer
from src.core.__seedwork__.infra.mixins import AccessLogsSyncMixin

class AccessLogsViewSet(AccessLogsSyncMixin, viewsets.ModelViewSet):
    queryset = AccessLogs.objects.all()
    serializer_class = AccessLogsSerializer
    filterset_fields = ['id', 'time', 'event_type', 'device', 'identifier_id', 'user', 'portal', 'access_rule', 'qr_code', 'uhf_value', 'pin_value', 'card_value', 'confidence', 'mask']
    search_fields = ['time', 'event_type', 'device', 'identifier_id', 'user', 'portal', 'access_rule', 'qr_code', 'uhf_value', 'pin_value', 'card_value', 'confidence', 'mask']
    ordering_fields = ['id', 'time', 'event_type', 'device', 'identifier_id', 'user', 'portal', 'access_rule', 'qr_code', 'uhf_value', 'pin_value', 'card_value', 'confidence', 'mask']
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        
        # Criar na catraca
        response = self.create_objects("access_logs", [{
            "id": instance.id,
            "time": instance.time,
            "event": instance.event_type,
            "device": instance.device,
            "identifier_id": instance.identifier_id,
            "user": instance.user,
            "portal": instance.portal,
            "access_rule": instance.access_rule,
            "qr_code": instance.qr_code,
            "uhf_value": instance.uhf_value,
            "pin_value": instance.pin_value,
            "card_value": instance.card_value,
            "confidence": instance.confidence,
            "mask": instance.mask
        }])
        
        if response.status_code != status.HTTP_201_CREATED:
            instance.delete()  # Reverte se falhar na catraca
            return response
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        
        # Atualizar na catraca
        response = self.update_objects("access_logs", {
            "id": instance.id,
            "time": instance.time,
            "event": instance.event_type,
            "device": instance.device,
            "identifier_id": instance.identifier_id,
            "user": instance.user,
            "portal": instance.portal,
            "access_rule": instance.access_rule,
        }, {"access_logs": {"id": instance.id}})
        
        if response.status_code != status.HTTP_201_CREATED:
            instance.delete()  # Reverte se falhar na catraca
            return response
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        
        # Atualizar na catraca
        response = self.update_objects("access_logs", {
            "id": instance.id,
            "time": instance.time,
            "event": instance.event_type,
            "device": instance.device,
            "identifier_id": instance.identifier_id,
            "user": instance.user,
            "portal": instance.portal,
            "access_rule": instance.access_rule,
        }, {"access_logs": {"id": instance.id}})
        
        if response.status_code != status.HTTP_201_CREATED:
            instance.delete()  # Reverte se falhar na catraca
            return response
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Deletar na catraca
        response = self.destroy_objects("access_logs", {"access_logs": {"id": instance.id}})
        
        if response.status_code != status.HTTP_204_NO_CONTENT:
            return response
        
        # Deletar no banco local
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)