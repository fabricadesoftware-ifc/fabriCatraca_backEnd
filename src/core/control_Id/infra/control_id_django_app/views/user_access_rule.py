from rest_framework import viewsets, status
from rest_framework.response import Response
from ..models.user_access_rule import UserAccessRule
from ..serializers.user_access_rule import UserAccessRuleSerializer
from src.core.__seedwork__.infra.mixins import UserAccessRuleSyncMixin

class UserAccessRuleViewSet(UserAccessRuleSyncMixin, viewsets.ModelViewSet):
    queryset = UserAccessRule.objects.all()
    serializer_class = UserAccessRuleSerializer
    filterset_fields = ['user_id', 'access_rule_id']
    search_fields = ['user_id', 'access_rule_id']
    ordering_fields = ['user_id', 'access_rule_id']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        # Criar na catraca
        response = self.create_objects("user_access_rules", [{
            "user_id": instance.user_id_id,
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
            "user_access_rules",
            {
                "user_id": instance.user_id_id,
                "access_rule_id": instance.access_rule_id_id
            },
            {"user_access_rules": {"user_id": instance.user_id_id, "access_rule_id": instance.access_rule_id_id}}
        )

        if response.status_code != status.HTTP_200_OK:
            return response

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        # Deletar na catraca
        response = self.destroy_objects(
            "user_access_rules",
            {"user_access_rules": {"user_id": instance.user_id_id, "access_rule_id": instance.access_rule_id_id}}
        )

        if response.status_code != status.HTTP_204_NO_CONTENT:
            return response

        # Deletar no banco local
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
