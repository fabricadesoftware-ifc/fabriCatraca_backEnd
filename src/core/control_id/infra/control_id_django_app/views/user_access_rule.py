from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.response import Response

from src.core.__seedwork__.infra.api_errors import api_error_response
from src.core.control_id.infra.control_id_django_app.models.user_access_rule import (
    UserAccessRule,
)
from src.core.control_id.infra.control_id_django_app.serializers.user_access_rule import (
    UserAccessRuleSerializer,
)
from src.core.control_id.infra.control_id_django_app.services import (
    AccessRuleRelationDeviceSyncService,
    AccessRuleRelationSyncError,
)
from src.core.control_id.infra.control_id_django_app.use_cases import (
    CreateUserAccessRuleUseCase,
    DeleteUserAccessRuleUseCase,
    UpdateUserAccessRuleUseCase,
)


@extend_schema(tags=["User Access Rules"])
class UserAccessRuleViewSet(viewsets.ModelViewSet):
    queryset = UserAccessRule.objects.all()
    serializer_class = UserAccessRuleSerializer
    filterset_fields = ['user_id', 'access_rule_id', 'portal_group']
    search_fields = ['user_id', 'access_rule_id']
    ordering_fields = ['user_id', 'access_rule_id']

    def _sync_service(self) -> AccessRuleRelationDeviceSyncService:
        return AccessRuleRelationDeviceSyncService()

    def _build_sync_error_response(self, exc: AccessRuleRelationSyncError):
        return api_error_response(
            "Erro ao sincronizar regra de acesso do usuario na catraca.",
            code="user_access_rule_sync_failed",
            details=exc.details or exc.message,
            status_code=exc.status_code,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = CreateUserAccessRuleUseCase(
                sync_service=self._sync_service(),
            ).execute(serializer)
        except AccessRuleRelationSyncError as exc:
            return self._build_sync_error_response(exc)

        return Response(
            self.get_serializer(result.instance).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            result = UpdateUserAccessRuleUseCase(
                sync_service=self._sync_service(),
            ).execute(serializer, instance=instance)
        except AccessRuleRelationSyncError as exc:
            return self._build_sync_error_response(exc)

        return Response(self.get_serializer(result.instance).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        try:
            DeleteUserAccessRuleUseCase(
                sync_service=self._sync_service(),
            ).execute(instance)
        except AccessRuleRelationSyncError as exc:
            return self._build_sync_error_response(exc)

        return Response(status=status.HTTP_204_NO_CONTENT)
