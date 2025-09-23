from rest_framework import viewsets, status
from rest_framework.response import Response
from ..models.user_access_rule import UserAccessRule
from ..serializers.user_access_rule import UserAccessRuleSerializer
from src.core.__seedwork__.infra.mixins import UserAccessRuleSyncMixin
from drf_spectacular.utils import extend_schema

@extend_schema(tags=["User Access Rules"])
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

        response = self.create_in_catraca(instance)

        if response.status_code != status.HTTP_201_CREATED:
            instance.delete()  # Reverte se falhar na catraca
            return response

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        response = self.update_in_catraca(instance)

        if response.status_code != status.HTTP_200_OK:
            return response

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        response = self.delete_in_catraca(instance)

        if response.status_code != status.HTTP_204_NO_CONTENT:
            return response

        # Deletar no banco local
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
