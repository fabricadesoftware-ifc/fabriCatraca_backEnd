from drf_spectacular.utils import extend_schema
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Visitas
from ..permissions import IsAdminOrSisaeRole
from ..serializers import VisitasSerializer
from ..tasks import expire_visit
from ..visit_service import VisitService


@extend_schema(tags=["Users"])
class VisitasViewSet(viewsets.ModelViewSet):
    serializer_class = VisitasSerializer
    permission_classes = [IsAdminOrSisaeRole]
    queryset = (
        Visitas.objects.filter(deleted_at__isnull=True)
        .select_related("user", "created_by", "card")
        .order_by("-visit_date")
    )
    filterset_fields = ["user", "created_by", "visit_date"]
    search_fields = ["user__name", "user__cpf", "user__phone", "card__value"]
    ordering_fields = ["id", "visit_date", "initial_date", "created_at"]
    ordering = ["-visit_date"]

    def get_queryset(self):
        queryset = super().get_queryset()
        user_id = self.request.query_params.get("user")
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        return queryset

    def perform_create(self, serializer):
        visit = serializer.save()
        self._schedule_expiration(visit)

    def perform_update(self, serializer):
        visit = serializer.save()
        self._schedule_expiration(visit)

    def _schedule_expiration(self, visit: Visitas):
        if visit.end_date and not visit.finished_at and visit.end_date > timezone.now():
            expire_visit.apply_async(kwargs={"visit_id": visit.id}, eta=visit.end_date)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        visit = self.get_object()
        service = VisitService()

        try:
            visit = service.close_visit(visit)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(visit)
        return Response(serializer.data, status=status.HTTP_200_OK)
