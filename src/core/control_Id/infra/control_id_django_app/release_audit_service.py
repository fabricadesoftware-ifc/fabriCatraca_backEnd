from datetime import timedelta

from django.utils import timezone

from src.core.control_Id.infra.control_id_django_app.models import (
    Device,
    Portal,
    ReleaseAudit,
    TemporaryUserRelease,
    TemporaryGroupRelease,
)
from src.core.user.infra.user_django_app.models import User


class ReleaseAuditService:
    @staticmethod
    def _requested_by_snapshot(user):
        if not user:
            return {
                "requested_by": None,
                "requested_by_name": "",
                "requested_by_role": "",
                "requested_by_email": "",
            }
        return {
            "requested_by": user,
            "requested_by_name": user.name or user.email or f"Usuário {user.id}",
            "requested_by_role": user.effective_app_role,
            "requested_by_email": user.email or "",
        }

    @staticmethod
    def _target_user_snapshot(user):
        if not user:
            return {
                "target_user": None,
                "target_user_name": "",
                "target_user_registration": "",
            }
        return {
            "target_user": user,
            "target_user_name": user.name or "",
            "target_user_registration": user.registration or "",
        }

    @staticmethod
    def _temporary_release_status(release):
        mapping = {
            TemporaryUserRelease.Status.PENDING: ReleaseAudit.Status.REQUESTED,
            TemporaryUserRelease.Status.ACTIVE: ReleaseAudit.Status.ACTIVE,
            TemporaryUserRelease.Status.CONSUMED: ReleaseAudit.Status.CONSUMED,
            TemporaryUserRelease.Status.EXPIRED: ReleaseAudit.Status.EXPIRED,
            TemporaryUserRelease.Status.CANCELLED: ReleaseAudit.Status.CANCELLED,
            TemporaryUserRelease.Status.FAILED: ReleaseAudit.Status.FAILED,
        }
        return mapping.get(release.status, ReleaseAudit.Status.REQUESTED)

    @staticmethod
    def _temporary_release_type(release):
        if type(release) is TemporaryGroupRelease:
            return ReleaseAudit.ReleaseType.TEMPORARY_GROUP_RELEASE
        threshold = timedelta(minutes=1)
        if release.valid_from and release.created_at and release.valid_from > release.created_at + threshold:
            return ReleaseAudit.ReleaseType.SCHEDULED_USER_RELEASE
        return ReleaseAudit.ReleaseType.TEMPORARY_USER_RELEASE

    @classmethod
    def sync_from_temporary_release(cls, release: TemporaryUserRelease | TemporaryGroupRelease):
        if (type(release) is TemporaryUserRelease):
            defaults = {
                **cls._requested_by_snapshot(release.requested_by),
                **cls._target_user_snapshot(release.user),
                "release_type": cls._temporary_release_type(release),
                "status": cls._temporary_release_status(release),
                "notes": release.notes or "",
                "request_payload": {
                    "user_id": release.user.pk,
                    "access_rule_id": release.access_rule.pk,
                },
                "response_payload": (
                    {"result_message": release.result_message}
                    if release.result_message
                    else {}
                ),
                "scheduled_for": release.valid_from,
                "executed_at": release.activated_at,
                "expires_at": release.valid_until,
                "closed_at": release.closed_at,
                "access_log": release.consumed_log,
            }
            audit, created = ReleaseAudit.objects.get_or_create(
                temporary_release=release,
                defaults={
                    **defaults,
                    "requested_at": release.created_at or timezone.now(),
                },
            )
            if not created:
                for field, value in defaults.items():
                    setattr(audit, field, value)
                audit.save()
            return audit

        elif (type(release) is TemporaryGroupRelease):
            defaults = {
                **cls._requested_by_snapshot(release.requested_by),
                "target_group": release.group,
                "target_group_name": release.group.name or "",
                "release_type": cls._temporary_release_type(release),
                "status": cls._temporary_release_status(release),
                "notes": release.notes or "",
                "request_payload": {
                    "group_id": release.group.pk,
                    "access_rule_id": release.access_rule.pk,
                },
                "response_payload": (
                    {"result_message": release.result_message}
                    if release.result_message
                    else {}
                ),
                "scheduled_for": release.valid_from,
                "executed_at": release.activated_at,
                "expires_at": release.valid_until,
                "closed_at": release.closed_at,
                "access_log": release.consumed_log,
            }
            audit, created = ReleaseAudit.objects.get_or_create(
                temporary_group_release=release,
                defaults={
                    **defaults,
                    "requested_at": release.created_at or timezone.now(),
                },
            )
            if not created:
                for field, value in defaults.items():
                    setattr(audit, field, value)
                audit.save()
            return audit

    @classmethod
    def create_remote_authorization(cls, requested_by, payload, response):
        payload = payload or {}
        response_data = getattr(response, "data", {}) or {}
        device_ids = payload.get("device_ids") or []
        first_device = Device.objects.filter(id=device_ids[0]).first() if len(device_ids) == 1 else None
        portal = Portal.objects.filter(id=payload.get("portal_id")).first()
        target_user = None
        if payload.get("user_id"):
            target_user = User.objects.filter(id=payload.get("user_id")).first()

        actions = payload.get("actions") or []
        release_mode = payload.get("release_mode")
        release_type = (
            ReleaseAudit.ReleaseType.DEVICE_EVENT
            if release_mode == "device_event"
            else ReleaseAudit.ReleaseType.SINGLE_TURN
        )
        if not release_mode and not any(
            action.get("action") == "catra" and "allow=" in str(action.get("parameters", ""))
            for action in actions
        ):
            release_type = ReleaseAudit.ReleaseType.DEVICE_EVENT

        success = bool(response_data.get("success"))
        now = timezone.now()
        audit = ReleaseAudit.objects.create(
            **cls._requested_by_snapshot(requested_by),
            **cls._target_user_snapshot(target_user),
            device=first_device,
            portal=portal,
            release_type=release_type,
            status=ReleaseAudit.Status.SENT if success else ReleaseAudit.Status.FAILED,
            notes=payload.get("notes", ""),
            request_payload=payload,
            response_payload=response_data,
            requested_at=now,
            executed_at=now,
            closed_at=now,
            error_message="" if success else str(response_data.get("error", "")),
        )
        return audit
