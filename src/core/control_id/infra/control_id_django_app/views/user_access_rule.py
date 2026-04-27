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
    filterset_fields = ['user_id', 'access_rule_id', 'portal_group']
    search_fields = ['user_id', 'access_rule_id']
    ordering_fields = ['user_id', 'access_rule_id']

    def _get_device_ids(self, portal_group=None):
        if portal_group:
            return list(portal_group.active_devices().values_list("id", flat=True))
        return None

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        device_ids = self._get_device_ids(instance.portal_group)
        response = self.create_in_catraca(instance, device_ids=device_ids)

        if response.status_code != status.HTTP_201_CREATED:
            instance.delete()
            return response

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        old_portal_group = instance.portal_group
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        old_ids = self._get_device_ids(old_portal_group)
        new_ids = self._get_device_ids(instance.portal_group)

        if old_ids == new_ids:
            response = self.update_in_catraca(instance, device_ids=old_ids)
        else:
            removed = set(old_ids or []) - set(new_ids or [])
            added = set(new_ids or []) - set(old_ids or [])
            common = set(old_ids or []) & set(new_ids or [])

            if removed:
                self.delete_in_catraca(instance, device_ids=list(removed))
            if added:
                self.create_in_catraca(instance, device_ids=list(added))
            if common:
                response = self.update_in_catraca(instance, device_ids=list(common))

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        device_ids = self._get_device_ids(instance.portal_group)

        response = self.delete_in_catraca(instance, device_ids=device_ids)

        if response.status_code != status.HTTP_204_NO_CONTENT:
            return response

        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
