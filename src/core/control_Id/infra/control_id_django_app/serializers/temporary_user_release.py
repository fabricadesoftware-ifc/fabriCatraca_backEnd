from datetime import timedelta
import logging

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from src.core.control_Id.infra.control_id_django_app.models import (
    AccessLogs,
    AccessRule,
    TemporaryUserRelease,
    UserAccessRule,
    PortalGroup,
)

from .portal_group import PortalGroupSerializer
from src.core.control_Id.infra.control_id_django_app.release_audit_service import (
    ReleaseAuditService,
)
from src.core.user.infra.user_django_app.models import User, Visitas

logger = logging.getLogger(__name__)


class TemporaryReleaseUserSerializer(serializers.ModelSerializer):
    picture_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "name", "registration", "cpf", "phone", "birth_date", "picture_url"]

    def get_picture_url(self, obj):
        if obj.picture and obj.picture.arquivo:
            return obj.picture.arquivo.url
        return None


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


class TemporaryReleaseVisitSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.name", read_only=True)

    class Meta:
        model = Visitas
        fields = [
            "id",
            "user",
            "user_name",
            "created_by",
            "created_by_name",
            "initial_date",
            "visit_date",
            "end_date",
        ]


class TemporaryUserReleaseSerializer(serializers.ModelSerializer):
    user = TemporaryReleaseUserSerializer(read_only=True)
    requested_by = TemporaryReleaseUserSerializer(read_only=True)
    notified_server = TemporaryReleaseUserSerializer(read_only=True)
    access_rule = TemporaryReleaseAccessRuleSerializer(read_only=True)
    consumed_log = TemporaryReleaseAccessLogSerializer(read_only=True)
    portal_group = PortalGroupSerializer(read_only=True)
    visita = TemporaryReleaseVisitSerializer(read_only=True)

    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source="user",
        write_only=True,
        required=True,
    )
    notified_server_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(
            app_role=User.AppRole.SERVIDOR,
            deleted_at__isnull=True,
        ),
        source="notified_server",
        write_only=True,
        required=False,
        allow_null=True,
    )
    duration_minutes = serializers.IntegerField(
        min_value=1,
        write_only=True,
        required=True,
    )
    valid_from = serializers.DateTimeField(required=False)
    notes = serializers.CharField(required=False)
    notification_message = serializers.CharField(required=False, allow_blank=True)
    notification_email = serializers.EmailField(required=False, allow_blank=True)
    portal_group_id = serializers.PrimaryKeyRelatedField(
        queryset=PortalGroup.objects.filter(is_active=True),
        source="portal_group",
        write_only=True,
        required=False,
        allow_null=True,
    )
    visita_id = serializers.PrimaryKeyRelatedField(
        queryset=Visitas.objects.filter(deleted_at__isnull=True),
        source="visita",
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = TemporaryUserRelease
        fields = [
            "id",
            "user",
            "user_id",
            "requested_by",
            "notified_server",
            "notified_server_id",
            "access_rule",
            "status",
            "visita",
            "visita_id",
            "valid_from",
            "valid_until",
            "activated_at",
            "consumed_at",
            "closed_at",
            "consumed_log",
            "notes",
            "notification_message",
            "notification_email",
            "result_message",
            "created_at",
            "updated_at",
            "duration_minutes",
            "portal_group",
            "portal_group_id",
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
        visita = attrs.get("visita")
        notified_server = attrs.get("notified_server")
        notification_email = (attrs.get("notification_email") or "").strip().lower()
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

        if visita and visita.user_id != user.id:
            raise serializers.ValidationError(
                {"visita_id": ["A visita selecionada nao pertence ao usuario informado."]}
            )

        if notified_server and notified_server.app_role != User.AppRole.SERVIDOR:
            raise serializers.ValidationError(
                {
                    "notified_server_id": [
                        "Selecione um usuario com perfil de servidor para a notificacao."
                    ]
                }
            )

        if notified_server and not notified_server.email:
            raise serializers.ValidationError(
                {
                    "notified_server_id": [
                        "O servidor selecionado precisa ter um e-mail cadastrado."
                    ]
                }
            )

        if notified_server and not notification_email:
            attrs["notification_email"] = notified_server.email
        elif notification_email:
            attrs["notification_email"] = notification_email

        attrs["resolved_access_rule"] = access_rule
        return attrs

    def create(self, validated_data):
        self.notification_status = None
        self.notification_warning = ""
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

        if release.notification_email:
            try:
                from src.core.control_Id.infra.control_id_django_app.tasks import (
                    send_temporary_user_release_notification,
                )

                send_temporary_user_release_notification.delay(release.id)
                self.notification_status = "queued"
            except Exception:
                logger.exception(
                    "Failed to enqueue temporary release notification for release %s",
                    release.id,
                )
                self.notification_status = "failed"
                self.notification_warning = (
                    "Liberacao criada, mas nao foi possivel enfileirar o e-mail para o "
                    "destinatario informado."
                )

        # Agenda tasks com eta exato
        from src.core.control_Id.infra.control_id_django_app.tasks import (
            activate_user_release,
            expire_user_release,
        )
        activate_user_release.apply_async(kwargs={"release_id": release.id}, eta=valid_from)
        expire_user_release.apply_async(kwargs={"release_id": release.id}, eta=valid_until)

        return release
