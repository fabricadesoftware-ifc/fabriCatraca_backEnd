from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from src.core.control_Id.infra.control_id_django_app.models import TemporaryGroupRelease
from src.core.control_Id.infra.control_id_django_app.serializers import (
    TemporaryGroupReleaseSerializer,
)
from src.core.control_Id.infra.control_id_django_app.temporary_release_service import (
    TemporaryGroupReleaseService,
)
from src.core.user.infra.user_django_app.permissions import IsAdminOrSisaeRole


@extend_schema(tags=["Temporary Group Releases"])
class TemporaryGroupReleaseViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = TemporaryGroupRelease.objects.select_related(
        "group",
        "requested_by",
        "access_rule",
        "consumed_log__device",
        "consumed_log__portal",
    ).all()
    serializer_class = TemporaryGroupReleaseSerializer
    permission_classes = [IsAdminOrSisaeRole]
    filterset_fields = ["group", "status", "requested_by"]
    search_fields = ["group__name", "requested_by__name", "notes", "result_message"]
    ordering_fields = [
        "created_at",
        "valid_from",
        "valid_until",
        "activated_at",
        "closed_at",
    ]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        group_id = self.request.query_params.get("group")
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        release = self.get_object()

        if release.status not in (
            release.Status.PENDING,
            release.Status.ACTIVE,
        ):
            return Response(
                {"error": "Apenas liberações pendentes ou ativas podem ser canceladas."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = TemporaryGroupReleaseService()
        try:
            service.close_release(
                release,
                final_status=release.Status.CANCELLED,
                result_message=(
                    f"Liberação cancelada manualmente por {request.user.name or request.user}"
                ),
            )
        except Exception as exc:
            service.fail_release(
                release,
                result_message=f"Falha ao cancelar liberação temporária: {exc}",
            )
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        serializer = self.get_serializer(release)
        return Response(serializer.data, status=status.HTTP_200_OK)
