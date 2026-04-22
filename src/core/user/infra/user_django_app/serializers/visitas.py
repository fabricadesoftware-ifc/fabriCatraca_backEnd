from rest_framework import serializers
from django.utils import timezone

from ..models import Visitas


class VisitasSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.name", read_only=True)
    card_value = serializers.CharField(source="card.value", read_only=True)
    status = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()

    class Meta:
        model = Visitas
        fields = [
            "id",
            "user",
            "user_name",
            "created_by",
            "created_by_name",
            "initial_date",
            "end_date",
            "visit_date",
            "card",
            "card_value",
            "status",
            "status_label",
            "finished_at",
            "card_removed_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "created_by_name",
            "initial_date",
            "card_value",
            "finished_at",
            "card_removed_at",
        ]

    def create(self, validated_data):
        request = self.context.get("request")
        if request and getattr(request, "user", None) and request.user.is_authenticated:
            validated_data["created_by"] = request.user
        return super().create(validated_data)

    def get_status(self, obj: Visitas):
        if obj.finished_at:
            return "finished"
        if obj.end_date and obj.end_date <= timezone.now():
            return "overdue"
        return "active"

    def get_status_label(self, obj: Visitas):
        labels = {
            "active": "Em andamento",
            "overdue": "Aguardando encerramento",
            "finished": "Encerrada",
        }
        return labels[self.get_status(obj)]
