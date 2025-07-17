from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from ..models.portal_access_rule import PortalAccessRule
from ..serializers.portal_access_rule import PortalAccessRuleSerializer
from ..sync_mixins.portal_access_rule import PortalAccessRuleSyncMixin

class PortalAccessRuleViewSet(PortalAccessRuleSyncMixin, viewsets.ModelViewSet):
    queryset = PortalAccessRule.objects.all()
    serializer_class = PortalAccessRuleSerializer
    filterset_fields = ['portal_id', 'access_rule_id']
    search_fields = ['portal_id', 'access_rule_id']
    ordering_fields = ['portal_id', 'access_rule_id']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        # Criar na catraca
        response = self.create_objects("portal_access_rules", [{
            "portal_id": instance.portal_id_id,
            "access_rule_id": instance.access_rule_id_id
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
            "portal_access_rules",
            [{
                "portal_id": instance.portal_id_id,
                "access_rule_id": instance.access_rule_id_id
            }],
            {"portal_access_rules": {"portal_id": instance.portal_id_id, "access_rule_id": instance.access_rule_id_id}}
        )

        if response.status_code != status.HTTP_200_OK:
            return response

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        # Deletar na catraca
        response = self.destroy_objects(
            "portal_access_rules",
            {"portal_access_rules": {"portal_id": instance.portal_id_id, "access_rule_id": instance.access_rule_id_id}}
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
                "portal_access_rules",
                fields=["id","portal_id", "access_rule_id"],
                order_by=["portal_id", "access_rule_id"]
            )

            # Apagar todos do banco local
            PortalAccessRule.objects.all().delete()

            # Cadastrar da catraca no banco local
            for data in catraca_objects:
                PortalAccessRule.objects.create(
                    id=data["id"],
                    portal_id=data["portal_id"],
                    access_rule_id=data["access_rule_id"]
                )

            return Response({
                "success": True,
                "message": f"Sincronizadas {len(catraca_objects)} associações portal-regra"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 