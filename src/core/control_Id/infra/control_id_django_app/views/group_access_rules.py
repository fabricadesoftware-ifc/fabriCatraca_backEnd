from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from src.core.control_Id.infra.control_id_django_app.models import GroupAccessRule
from src.core.control_Id.infra.control_id_django_app.serializers import (
    GroupAccessRuleSerializer,
)
from src.core.__seedwork__.infra.mixins import GroupAccessRulesSyncMixin
from drf_spectacular.utils import extend_schema


@extend_schema(tags=["Group Access Rules"])
class GroupAccessRulesViewSet(GroupAccessRulesSyncMixin, viewsets.ModelViewSet):
    queryset = GroupAccessRule.objects.all()
    serializer_class = GroupAccessRuleSerializer
    filterset_fields = ["id", "group", "access_rule"]
    search_fields = ["group__name", "access_rule__name"]
    ordering_fields = ["id", "group__name", "access_rule__name"]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        # Criar na catraca
        response = self.create_objects(
            "group_access_rules",
            [
                {
                    "group_id": instance.group.id,
                    "access_rule_id": instance.access_rule.id,
                }
            ],
        )

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
            "group_access_rules",
            {"group_id": instance.group.id, "access_rule_id": instance.access_rule.id},
            {
                "group_access_rules": {
                    "group_id": instance.group.id,
                    "access_rule_id": instance.access_rule.id,
                }
            },
        )

        if response.status_code != status.HTTP_200_OK:
            return response

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        # Deletar na catraca
        response = self.destroy_objects(
            "group_access_rules",
            {
                "group_access_rules": {
                    "group_id": instance.group.id,
                    "access_rule_id": instance.access_rule.id,
                }
            },
        )

        if response.status_code != status.HTTP_204_NO_CONTENT:
            return response

        # Deletar no banco local
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
