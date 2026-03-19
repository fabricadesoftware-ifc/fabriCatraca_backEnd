from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets

from src.core.control_Id.infra.control_id_django_app.models import ReleaseAudit
from src.core.control_Id.infra.control_id_django_app.serializers.release_audit import (
    ReleaseAuditSerializer,
)
from src.core.user.infra.user_django_app.permissions import IsOperationalRole


@extend_schema(tags=["Release Audits"])
class ReleaseAuditViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ReleaseAudit.objects.select_related(
        "requested_by",
        "target_user",
        "device",
        "portal",
        "temporary_release",
        "access_log",
    ).all()
    serializer_class = ReleaseAuditSerializer
    permission_classes = [IsOperationalRole]
    filterset_fields = [
        "release_type",
        "status",
        "requested_by",
        "target_user",
        "device",
        "portal",
        "temporary_release",
    ]
    search_fields = [
        "requested_by_name",
        "target_user_name",
        "target_user_registration",
        "notes",
        "error_message",
    ]
    ordering_fields = [
        "requested_at",
        "scheduled_for",
        "executed_at",
        "expires_at",
        "closed_at",
    ]
    ordering = ["-requested_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if getattr(user, "is_superuser", False) or getattr(user, "is_admin_role", False):
            return queryset
        if getattr(user, "is_guarita_role", False):
            return queryset.filter(requested_by=user)
        if getattr(user, "is_sisae_role", False):
            return queryset
        return queryset.none()
