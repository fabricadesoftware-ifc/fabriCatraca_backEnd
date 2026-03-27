from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from src.core.control_Id.infra.control_id_django_app.models import (
    AccessLogs,
    AccessRule,
    TemporaryUserRelease,
    UserAccessRule,
)
from src.core.control_Id.infra.control_id_django_app.release_audit_service import (
    ReleaseAuditService,
)
from src.core.user.infra.user_django_app.models import User


class TemporaryReleaseUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "registration"]


class TemporaryReleaseAccessRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessRule
        fields = ["id", "name", "type", "priority"]


class TemporaryReleaseAccessLogSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)
    portal_name = serializers.CharField(source="portal.name", read_only=True)

    class Meta:
        model = AccessLogs
        fields = ["id", "time", "event_type", "device_name", "portal_name"]


class TemporaryUserReleaseSerializer(serializers.ModelSerializer):
    user = TemporaryReleaseUserSerializer(read_only=True)
    requested_by = TemporaryReleaseUserSerializer(read_only=True)
    access_rule = TemporaryReleaseAccessRuleSerializer(read_only=True)
    consumed_log = TemporaryReleaseAccessLogSerializer(read_only=True)

    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source="user",
        write_only=True,
        required=True,
    )
    duration_minutes = serializers.IntegerField(
        min_value=1,
        write_only=True,
        required=True,
    )
    valid_from = serializers.DateTimeField(required=False)
    notes = serializers.CharField(required=False)

    class Meta:
        model = TemporaryUserRelease
        fields = [
            "id",
            "user",
            "user_id",
            "requested_by",
            "access_rule",
            "status",
            "valid_from",
            "valid_until",
            "activated_at",
            "consumed_at",
            "closed_at",
            "consumed_log",
            "notes",
            "result_message",
            "created_at",
            "updated_at",
            "duration_minutes",
        ]
        read_only_fields = [
            "id",
            "requested_by",
            "access_rule",
            "status",
            "valid_until",
            "activated_at",
            "consumed_at",
            "closed_at",
            "consumed_log",
            "result_message",
            "created_at",
            "updated_at",
        ]

    def _get_temporary_access_rule(self) -> AccessRule:
        access_rule_id = getattr(settings, "TEMPORARY_RELEASE_ACCESS_RULE_ID", None)

        if not access_rule_id:
            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        "TEMPORARY_RELEASE_ACCESS_RULE_ID não está configurado no backend."
                    ]
                }
            )

        try:
            return AccessRule.objects.get(id=access_rule_id)
        except AccessRule.DoesNotExist as exc:
            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        f"Regra temporária global {access_rule_id} não existe."
                    ]
                }
            ) from exc

    def validate(self, attrs):
        user = attrs["user"]
        access_rule = self._get_temporary_access_rule()

        if self.instance is None:  # CREATE
            notes = attrs.get("notes")
            if not notes or not str(notes).strip():
                raise serializers.ValidationError({"notes": ["Este campo é obrigatório na criação."]})

        if TemporaryUserRelease.objects.filter(
            user=user,
            status__in=[
                TemporaryUserRelease.Status.PENDING,
                TemporaryUserRelease.Status.ACTIVE,
            ],
        ).exists():
            raise serializers.ValidationError(
                {"user_id": ["O usuário já possui uma liberação temporária em aberto."]}
            )

        if UserAccessRule.objects.filter(user=user, access_rule=access_rule).exists():
            raise serializers.ValidationError(
                {
                    "user_id": [
                        "O usuário já possui a regra temporária global vinculada diretamente."
                    ]
                }
            )

        attrs["resolved_access_rule"] = access_rule
        return attrs

    def create(self, validated_data):
        user = validated_data.pop("user")
        duration_minutes = validated_data.pop("duration_minutes")
        access_rule = validated_data.pop("resolved_access_rule")
        request = self.context["request"]
        valid_from = validated_data.pop("valid_from", timezone.now())
        if valid_from < timezone.now():
            valid_from = timezone.now()
        valid_until = valid_from + timedelta(minutes=duration_minutes)

        release = TemporaryUserRelease.objects.create(
            user=user,
            requested_by=request.user,
            access_rule=access_rule,
            valid_from=valid_from,
            valid_until=valid_until,
            **validated_data,
        )
        ReleaseAuditService.sync_from_temporary_release(release)
        return release
