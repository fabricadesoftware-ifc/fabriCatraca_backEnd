from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from ..models.access_rule import AccessRule
from ..serializers.access_rule import AccessRuleSerializer
from ..sync_mixins.access_rule import AccessRuleSyncMixin

class AccessRuleViewSet(AccessRuleSyncMixin, viewsets.ModelViewSet):
    queryset = AccessRule.objects.all()
    serializer_class = AccessRuleSerializer
    filterset_fields = ['id', 'name', 'type', 'priority']
    search_fields = ['name']
    ordering_fields = ['id', 'name', 'priority']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        # Criar na catraca
        response = self.create_objects("access_rules", [{
            "id": instance.id,
            "name": instance.name,
            "type": instance.type,
            "priority": instance.priority
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
            "access_rules",
            [{
                "id": instance.id,
                "name": instance.name,
                "type": instance.type,
                "priority": instance.priority
            }],
            {"access_rules": {"id": instance.id}}
        )

        if response.status_code != status.HTTP_200_OK:
            return response

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        # Deletar na catraca
        response = self.destroy_objects(
            "access_rules",
            {"access_rules": {"id": instance.id}}
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
                "access_rules",
                fields=["id", "name", "type", "priority"],
                order_by=["id"]
            )

            # Apagar todos do banco local
            AccessRule.objects.all().delete()

            # Cadastrar da catraca no banco local
            for data in catraca_objects:
                AccessRule.objects.create(**data)

            return Response({
                "success": True,
                "message": f"Sincronizadas {len(catraca_objects)} regras de acesso"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 