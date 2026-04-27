from rest_framework import serializers

from src.core.control_id.infra.control_id_django_app.models import ReleaseAudit


class ReleaseAuditActorSerializer(serializers.Serializer):
    id = serializers.IntegerField(allow_null=True)
    name = serializers.CharField(allow_blank=True)
    email = serializers.CharField(allow_blank=True, required=False)
    registration = serializers.CharField(allow_blank=True, required=False)
    role = serializers.CharField(allow_blank=True, required=False)


class ReleaseAuditSerializer(serializers.ModelSerializer):
    requested_by_data = serializers.SerializerMethodField()
    target_user_data = serializers.SerializerMethodField()
    device_name = serializers.CharField(source="device.name", read_only=True)
    portal_name = serializers.CharField(source="portal.name", read_only=True)
    access_log_time = serializers.DateTimeField(
        source="access_log.time", read_only=True
    )

    class Meta:
        model = ReleaseAudit
        fields = [
            "id",
            "release_type",
            "status",
            "requested_by",
            "requested_by_name",
            "requested_by_role",
            "requested_by_email",
            "requested_by_data",
            "target_user",
            "target_user_name",
            "target_user_registration",
            "target_user_data",
            "device",
            "device_name",
            "portal",
            "portal_name",
            "temporary_release",
            "access_log",
            "access_log_time",
            "notes",
            "error_message",
            "request_payload",
            "response_payload",
            "requested_at",
            "scheduled_for",
            "executed_at",
            "expires_at",
            "closed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_requested_by_data(self, obj):
        if obj.requested_by_id:
            return {
                "id": obj.requested_by_id,
                "name": obj.requested_by.name,
                "email": obj.requested_by.email or "",
                "role": obj.requested_by.effective_app_role,
            }
        return {
            "id": None,
            "name": obj.requested_by_name,
            "email": obj.requested_by_email,
            "role": obj.requested_by_role,
        }

    def get_target_user_data(self, obj):
        if obj.target_user_id:
            return {
                "id": obj.target_user_id,
                "name": obj.target_user.name,
                "registration": obj.target_user.registration or "",
            }
        return {
            "id": None,
            "name": obj.target_user_name,
            "registration": obj.target_user_registration,
        }
