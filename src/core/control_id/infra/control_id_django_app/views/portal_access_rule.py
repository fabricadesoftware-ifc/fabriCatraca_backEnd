from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.response import Response

from src.core.__seedwork__.infra.api_errors import api_error_response
from src.core.control_id.infra.control_id_django_app.models import PortalAccessRule
from src.core.control_id.infra.control_id_django_app.serializers import (
    PortalAccessRuleSerializer,
)
from src.core.control_id.infra.control_id_django_app.services import (
    AccessRuleRelationDeviceSyncService,
    AccessRuleRelationSyncError,
)
from src.core.control_id.infra.control_id_django_app.use_cases import (
    CreatePortalAccessRuleUseCase,
    DeletePortalAccessRuleUseCase,
    UpdatePortalAccessRuleUseCase,
)


@extend_schema(tags=["Portal Access Rules"])
class PortalAccessRuleViewSet(viewsets.ModelViewSet):
    queryset = PortalAccessRule.objects.all()
    serializer_class = PortalAccessRuleSerializer
    filterset_fields = ["portal_id", "access_rule_id"]
    search_fields = ["portal_id", "access_rule_id"]
    ordering_fields = ["portal_id", "access_rule_id"]

    def _sync_service(self) -> AccessRuleRelationDeviceSyncService:
        return AccessRuleRelationDeviceSyncService()

    def _build_sync_error_response(self, exc: AccessRuleRelationSyncError):
        return api_error_response(
            "Erro ao sincronizar regra de acesso do portal na catraca.",
            code="portal_access_rule_sync_failed",
            details=exc.details or exc.message,
            status_code=exc.status_code,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = CreatePortalAccessRuleUseCase(
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
            result = UpdatePortalAccessRuleUseCase(
                sync_service=self._sync_service(),
            ).execute(serializer, instance=instance)
        except AccessRuleRelationSyncError as exc:
            return self._build_sync_error_response(exc)

        return Response(self.get_serializer(result.instance).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        try:
            DeletePortalAccessRuleUseCase(
                sync_service=self._sync_service(),
            ).execute(instance)
        except AccessRuleRelationSyncError as exc:
            return self._build_sync_error_response(exc)

        return Response(status=status.HTTP_204_NO_CONTENT)
