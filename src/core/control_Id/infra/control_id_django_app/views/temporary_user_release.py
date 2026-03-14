from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from src.core.control_Id.infra.control_id_django_app.models import TemporaryUserRelease
from src.core.control_Id.infra.control_id_django_app.serializers import (
    TemporaryUserReleaseSerializer,
)
from src.core.control_Id.infra.control_id_django_app.temporary_release_service import (
    TemporaryUserReleaseService,
)


@extend_schema(tags=["Temporary User Releases"])
class TemporaryUserReleaseViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = TemporaryUserRelease.objects.select_related(
        "user",
        "requested_by",
        "access_rule",
        "consumed_log__device",
        "consumed_log__portal",
    ).all()
    serializer_class = TemporaryUserReleaseSerializer
    filterset_fields = ["user", "status"]
    search_fields = ["user__name", "requested_by__name", "notes", "result_message"]
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
        user_id = self.request.query_params.get("user")
        if user_id:
            queryset = queryset.filter(user_id=user_id)
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

        service = TemporaryUserReleaseService()
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
