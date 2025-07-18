from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from src.core.user.infra.user_django_app.models import User
from src.core.user.infra.user_django_app.serializers import UserSerializer
from src.core.user.infra.user_django_app.sync_mixins import UserSyncMixin

class UserViewSet(UserSyncMixin, viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filterset_fields = ['id', 'name', 'registration', 'user_type_id']
    search_fields = ['name']
    ordering_fields = ['id', 'name', 'registration', 'user_type_id']
    depth = 1

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        # Criar na catraca
        response = self.create_objects("users", [{
            "name": instance.name,
            "registration": instance.registration,
            "user_type_id": instance.user_type_id
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
        response = self.update_objects(
            "users",
            {
                "name": instance.name,
                "registration": instance.registration,
                "user_type_id": instance.user_type_id
            },
            {"users": {"id": instance.id}}
        )

        if response.status_code != status.HTTP_200_OK:
            return Response(response.data, status=response.status_code)

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        # Deletar na catraca
        response = self.destroy_objects(
            "users",
            {"users": {"id": instance.id}}
        )

        if response.status_code != status.HTTP_204_NO_CONTENT:
            return response

        # Deletar no banco local
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def sync(self, request):
        try:
            # Carregar da catraca
            catraca_objects = self.load_objects(
                "users",
                fields=["id", "name", "registration", "user_type_id"],
                order_by=["id"]
            )

            # Apagar todos do banco local
            User.objects.all().delete()

            # Cadastrar da catraca no banco local
            for data in catraca_objects:
                User.objects.create(**data)

            return Response({
                "success": True,
                "message": f"Sincronizadas {len(catraca_objects)} usuários"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 
        