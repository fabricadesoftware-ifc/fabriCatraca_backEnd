from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from src.core.control_Id.infra.control_id_django_app.models import Area
from src.core.control_Id.infra.control_id_django_app.serializers import AreaSerializer
from src.core.__seedwork__.infra.mixins import AreaSyncMixin

class AreaViewSet(AreaSyncMixin, viewsets.ModelViewSet):
    queryset = Area.objects.all()
    serializer_class = AreaSerializer
    filterset_fields = ['id', 'name']
    search_fields = ['name']
    ordering_fields = ['id', 'name']
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        
        # Criar na catraca
        response = self.create_objects("areas", [{
            "id": instance.id,
            "name": instance.name
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
        response = self.update_objects("areas", {
            "id": instance.id,
            "name": instance.name
        }, {"areas": {"id": instance.id}})
        
        if response.status_code != status.HTTP_200_OK:
            return response
        
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Deletar na catraca
        response = self.destroy_objects("areas", {"areas": {"id": instance.id}})
        
        if response.status_code != status.HTTP_204_NO_CONTENT:
            return response
        
        # Deletar no banco local
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)