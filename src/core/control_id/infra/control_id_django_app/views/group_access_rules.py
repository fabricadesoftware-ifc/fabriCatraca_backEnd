from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.response import Response

from src.core.__seedwork__.infra.api_errors import api_error_response
from src.core.control_id.infra.control_id_django_app.models import GroupAccessRule
from src.core.control_id.infra.control_id_django_app.serializers import (
    GroupAccessRuleSerializer,
)
from src.core.control_id.infra.control_id_django_app.services import (
    AccessRuleRelationDeviceSyncService,
    AccessRuleRelationSyncError,
)
from src.core.control_id.infra.control_id_django_app.use_cases import (
    CreateGroupAccessRuleUseCase,
    DeleteGroupAccessRuleUseCase,
    UpdateGroupAccessRuleUseCase,
)


@extend_schema(tags=["Group Access Rules"])
class GroupAccessRulesViewSet(viewsets.ModelViewSet):
    queryset = GroupAccessRule.objects.all()
    serializer_class = GroupAccessRuleSerializer
    filterset_fields = ["id", "group", "access_rule", "portal_group"]
    search_fields = ["group__name", "access_rule__name"]
    ordering_fields = ["id", "group__name", "access_rule__name"]

    def _sync_service(self) -> AccessRuleRelationDeviceSyncService:
        return AccessRuleRelationDeviceSyncService()

    def _build_sync_error_response(self, exc: AccessRuleRelationSyncError):
        return api_error_response(
            "Erro ao sincronizar regra de acesso do grupo na catraca.",
            code="group_access_rule_sync_failed",
            details=exc.details or exc.message,
            status_code=exc.status_code,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = CreateGroupAccessRuleUseCase(
                sync_service=self._sync_service(),
            ).execute(serializer)
        except AccessRuleRelationSyncError as exc:
            return self._build_sync_error_response(exc)

        return Response(
            self.get_serializer(result.instance).data,
            status=status.HTTP_201_CREATED if result.created else status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            result = UpdateGroupAccessRuleUseCase(
                sync_service=self._sync_service(),
            ).execute(serializer, instance=instance)
        except AccessRuleRelationSyncError as exc:
            return self._build_sync_error_response(exc)

        return Response(self.get_serializer(result.instance).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        try:
            DeleteGroupAccessRuleUseCase(
                sync_service=self._sync_service(),
            ).execute(instance)
        except AccessRuleRelationSyncError as exc:
            return self._build_sync_error_response(exc)

        return Response(status=status.HTTP_204_NO_CONTENT)
