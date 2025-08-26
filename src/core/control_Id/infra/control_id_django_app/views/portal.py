from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from ..models.portal import Portal
from ..serializers.portal import PortalSerializer
from src.core.__seedwork__.infra.mixins import PortalSyncMixin
from drf_spectacular.utils import extend_schema

@extend_schema(tags=["Portals"])
class PortalViewSet(PortalSyncMixin, viewsets.ModelViewSet):
    queryset = Portal.objects.all()
    serializer_class = PortalSerializer
    filterset_fields = ['id', 'name']
    search_fields = ['name']
    ordering_fields = ['id', 'name']
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        
        # Criar na catraca
        response = self.create_objects("portals", [{
            "id": instance.id,
            "name": instance.name,
            "area_from_id": instance.area_from.id,
            "area_to_id": instance.area_to.id
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
        response = self.update_objects("portals", {
            "id": instance.id,
            "name": instance.name,
            "area_from_id": instance.area_from.id,
            "area_to_id": instance.area_to.id
        }, {"portals": {"id": instance.id}})
        
        if response.status_code != status.HTTP_200_OK:
            return response
        
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Deletar na catraca
        response = self.destroy_objects("portals", {"portals": {"id": instance.id}})
        
        if response.status_code != status.HTTP_204_NO_CONTENT:
            return response
        
        # Deletar no banco local
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)