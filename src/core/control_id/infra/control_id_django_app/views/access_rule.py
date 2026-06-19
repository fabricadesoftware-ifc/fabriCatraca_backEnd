from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.response import Response

from src.core.__seedwork__.infra.api_errors import api_error_response
from src.core.control_id.infra.control_id_django_app.models.access_rule import (
    AccessRule,
)
from src.core.control_id.infra.control_id_django_app.serializers.access_rule import (
    AccessRuleSerializer,
)
from src.core.control_id.infra.control_id_django_app.services import (
    AccessRuleDeviceSyncError,
    AccessRuleDeviceSyncService,
)
from src.core.control_id.infra.control_id_django_app.use_cases import (
    CreateAccessRuleUseCase,
    DeleteAccessRuleUseCase,
    UpdateAccessRuleUseCase,
)


@extend_schema(tags=["Access Rules"])
class AccessRuleViewSet(viewsets.ModelViewSet):
    queryset = AccessRule.objects.all()
    serializer_class = AccessRuleSerializer
    filterset_fields = ['id', 'name', 'type', 'priority']
    search_fields = ['name']
    ordering_fields = ['id', 'name', 'priority']

    def _sync_service(self) -> AccessRuleDeviceSyncService:
        return AccessRuleDeviceSyncService()

    def _build_sync_error_response(self, exc: AccessRuleDeviceSyncError):
        return api_error_response(
            "Erro ao sincronizar regra de acesso na catraca.",
            code="access_rule_sync_failed",
            details=exc.details or exc.message,
            status_code=exc.status_code,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = CreateAccessRuleUseCase(
                sync_service=self._sync_service(),
            ).execute(serializer)
        except AccessRuleDeviceSyncError as exc:
            return self._build_sync_error_response(exc)

        return Response(
            self.get_serializer(result.access_rule).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            result = UpdateAccessRuleUseCase(
                sync_service=self._sync_service(),
            ).execute(serializer)
        except AccessRuleDeviceSyncError as exc:
            return self._build_sync_error_response(exc)

        return Response(self.get_serializer(result.access_rule).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        try:
            DeleteAccessRuleUseCase(
                sync_service=self._sync_service(),
            ).execute(instance)
        except AccessRuleDeviceSyncError as exc:
            return self._build_sync_error_response(exc)

        return Response(status=status.HTTP_204_NO_CONTENT)
