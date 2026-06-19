from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from src.core.control_id.infra.control_id_django_app.models import (
    GroupAccessRule,
    UserAccessRule,
)
from src.core.control_id.infra.control_id_django_app.release_audit_service import (
    ReleaseAuditService,
)
from src.core.control_id.infra.control_id_django_app.services import (
    AccessRuleRelationDeviceSyncService,
    AccessRuleRelationSyncError,
)


class TemporaryUserReleaseService:
    def __init__(
        self,
        sync_service: AccessRuleRelationDeviceSyncService | None = None,
    ) -> None:
        self.sync_service = sync_service or AccessRuleRelationDeviceSyncService()

    def activate_release(self, release):
        if release.status != release.Status.PENDING:
            return release

        with transaction.atomic():
            existing_user_rule = UserAccessRule.objects.filter(
                user=release.user,
                access_rule=release.access_rule,
            ).first()

            if existing_user_rule:
                raise ValueError(
                    "O usuario ja possui a regra temporaria diretamente vinculada."
                )

            user_access_rule = UserAccessRule.objects.create(
                user=release.user,
                access_rule=release.access_rule,
                portal_group=release.portal_group,
            )

            try:
                self.sync_service.create_user_rule(user_access_rule)
            except AccessRuleRelationSyncError as exc:
                user_access_rule.delete()
                raise RuntimeError(
                    f"Falha ao ativar liberacao temporaria: {exc.details or exc}"
                ) from exc

            release.user_access_rule = user_access_rule
            release.status = release.Status.ACTIVE
            release.activated_at = timezone.now()
            release.result_message = "Liberacao temporaria ativada com sucesso."
            release.save(
                update_fields=[
                    "user_access_rule",
                    "status",
                    "activated_at",
                    "result_message",
                    "updated_at",
                ]
            )
            ReleaseAuditService.sync_from_temporary_release(release)

        return release

    def close_release(
        self,
        release,
        final_status: str,
        result_message: str,
        consumed_log=None,
        consumed_at=None,
    ):
        with transaction.atomic():
            user_access_rule = release.user_access_rule

            if user_access_rule:
                try:
                    self.sync_service.delete_user_rule(user_access_rule)
                except AccessRuleRelationSyncError as exc:
                    raise RuntimeError(
                        f"Falha ao remover regra temporaria: {exc.details or exc}"
                    ) from exc
                user_access_rule.delete()

            release.user_access_rule = None
            release.status = final_status
            release.result_message = result_message
            release.closed_at = timezone.now()
            release.consumed_log = consumed_log
            if consumed_at is not None:
                release.consumed_at = consumed_at
            release.save(
                update_fields=[
                    "user_access_rule",
                    "status",
                    "result_message",
                    "closed_at",
                    "consumed_log",
                    "consumed_at",
                    "updated_at",
                ]
            )
            ReleaseAuditService.sync_from_temporary_release(release)

        return release

    def fail_release(self, release, result_message: str):
        release.status = release.Status.FAILED
        release.closed_at = timezone.now()
        release.result_message = result_message
        release.save(
            update_fields=["status", "closed_at", "result_message", "updated_at"]
        )
        ReleaseAuditService.sync_from_temporary_release(release)
        return release


class TemporaryGroupReleaseService:
    def __init__(
        self,
        sync_service: AccessRuleRelationDeviceSyncService | None = None,
    ) -> None:
        self.sync_service = sync_service or AccessRuleRelationDeviceSyncService()

    def activate_release(self, release):
        if release.status != release.Status.PENDING:
            return release

        with transaction.atomic():
            existing_group_rule = GroupAccessRule.objects.filter(
                group=release.group,
                access_rule=release.access_rule,
            ).first()

            if existing_group_rule:
                raise ValueError(
                    "O grupo ja possui a regra temporaria diretamente vinculada."
                )

            group_access_rule = GroupAccessRule.objects.create(
                group=release.group,
                access_rule=release.access_rule,
                portal_group=release.portal_group,
            )

            try:
                self.sync_service.create_group_rule(group_access_rule)
            except AccessRuleRelationSyncError as exc:
                group_access_rule.delete()
                raise RuntimeError(
                    f"Falha ao ativar liberacao temporaria: {exc.details or exc}"
                ) from exc

            release.group_access_rule = group_access_rule
            release.status = release.Status.ACTIVE
            release.activated_at = timezone.now()
            release.result_message = "Liberacao temporaria ativada com sucesso."
            release.save(
                update_fields=[
                    "group_access_rule",
                    "status",
                    "activated_at",
                    "result_message",
                    "updated_at",
                ]
            )
            ReleaseAuditService.sync_from_temporary_release(release)

        return release

    def close_release(
        self,
        release,
        final_status: str,
        result_message: str,
        consumed_log=None,
        consumed_at=None,
    ):
        with transaction.atomic():
            group_access_rule = release.group_access_rule

            if group_access_rule:
                try:
                    self.sync_service.delete_group_rule(group_access_rule)
                except AccessRuleRelationSyncError as exc:
                    raise RuntimeError(
                        f"Falha ao remover regra temporaria: {exc.details or exc}"
                    ) from exc
                group_access_rule.delete()

            release.group_access_rule = None
            release.status = final_status
            release.result_message = result_message
            release.closed_at = timezone.now()
            release.consumed_log = consumed_log
            if consumed_at is not None:
                release.consumed_at = consumed_at
            release.save(
                update_fields=[
                    "group_access_rule",
                    "status",
                    "result_message",
                    "closed_at",
                    "consumed_log",
                    "consumed_at",
                    "updated_at",
                ]
            )
            ReleaseAuditService.sync_from_temporary_release(release)

        return release

    def fail_release(self, release, result_message: str):
        release.status = release.Status.FAILED
        release.closed_at = timezone.now()
        release.result_message = result_message
        release.save(
            update_fields=["status", "closed_at", "result_message", "updated_at"]
        )
        ReleaseAuditService.sync_from_temporary_release(release)
        return release
