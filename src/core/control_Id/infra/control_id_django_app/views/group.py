from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from src.core.control_Id.infra.control_id_django_app.models import CustomGroup
from src.core.control_Id.infra.control_id_django_app.serializers import CustomGroupSerializer
from src.core.__seedwork__.infra.mixins import GroupSyncMixin
from drf_spectacular.utils import extend_schema

@extend_schema(tags=["Groups"])
class GroupViewSet(GroupSyncMixin, viewsets.ModelViewSet):
    queryset = CustomGroup.objects.all()
    serializer_class = CustomGroupSerializer
    filterset_fields = ['id', 'name']
    search_fields = ['name']
    ordering_fields = ['id', 'name']
    
    def create(self, request, *args, **kwargs):
        # Local-first para garantir a autoridade de IDs do backend
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        response = self.create_in_catraca(instance)
        if response.status_code != status.HTTP_201_CREATED:
            instance.delete()
            return response
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        
        # Atualizar na catraca
        response = self.update_objects("groups", {
            "id": instance.id,
            "name": instance.name
        }, {"groups": {"id": instance.id}})
        
        if response.status_code != status.HTTP_200_OK:
            return response
        
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Deletar na catraca
        response = self.destroy_objects("groups", {"groups": {"id": instance.id}})
        
        if response.status_code != status.HTTP_204_NO_CONTENT:
            return response
        
        # Deletar no banco local
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)