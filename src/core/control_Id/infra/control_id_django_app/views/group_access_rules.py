from django.db import IntegrityError
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
    filterset_fields = ["id", "group", "access_rule", "portal_group"]
    search_fields = ["group__name", "access_rule__name"]
    ordering_fields = ["id", "group__name", "access_rule__name"]

    def _get_device_ids(self, portal_group=None):
        if portal_group:
            return list(portal_group.active_devices().values_list("id", flat=True))
        return None

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group = serializer.validated_data["group"]
        access_rule = serializer.validated_data["access_rule"]
        portal_group = serializer.validated_data.get("portal_group")

        instance = GroupAccessRule.objects.filter(
            group=group,
            access_rule=access_rule,
            portal_group=portal_group,
        ).first()

        if instance:
            return Response(
                self.get_serializer(instance).data, status=status.HTTP_200_OK
            )

        soft_deleted_instance = GroupAccessRule._base_manager.filter(
            group=group,
            access_rule=access_rule,
            portal_group=portal_group,
        ).first()

        if soft_deleted_instance:
            soft_deleted_instance.undelete()
            instance = soft_deleted_instance
        else:
            try:
                instance = serializer.save()
            except IntegrityError:
                instance = GroupAccessRule._base_manager.filter(
                    group=group,
                    access_rule=access_rule,
                    portal_group=portal_group,
                ).first()
                if not instance:
                    raise
                if getattr(instance, "deleted", None):
                    instance.undelete()

        device_ids = self._get_device_ids(instance.portal_group)
        response = self.create_in_catraca(instance, device_ids=device_ids)

        if response.status_code != status.HTTP_201_CREATED:
            instance.delete()
            return response

        return Response(
            self.get_serializer(instance).data, status=status.HTTP_201_CREATED
        )

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
