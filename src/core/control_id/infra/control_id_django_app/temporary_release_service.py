from django.db import transaction
from django.utils import timezone
from rest_framework import status

from src.core.__seedwork__.infra.mixins import (
    GroupAccessRulesSyncMixin,
    UserAccessRuleSyncMixin,
)
from src.core.control_id.infra.control_id_django_app.models import (
    GroupAccessRule,
    UserAccessRule,
)
from src.core.control_id.infra.control_id_django_app.release_audit_service import (
    ReleaseAuditService,
)


class TemporaryUserReleaseService(UserAccessRuleSyncMixin):
    def _get_device_ids(self, release):
        """Determina quais devices devem receber esta liberação."""
        if release.portal_group:
            return list(
                release.portal_group.active_devices().values_list("id", flat=True)
            )
        return None  # None = todos os devices

    def activate_release(self, release):
        if release.status != release.Status.PENDING:
            return release

        device_ids = self._get_device_ids(release)

        with transaction.atomic():
            existing_user_rule = UserAccessRule.objects.filter(
                user=release.user,
                access_rule=release.access_rule,
            ).first()

            if existing_user_rule:
                raise ValueError(
                    "O usuário já possui a regra temporária diretamente vinculada."
                )

            user_access_rule = UserAccessRule.objects.create(
                user=release.user,
                access_rule=release.access_rule,
            )

            response = self.create_in_catraca(user_access_rule, device_ids=device_ids)
            if response.status_code != status.HTTP_201_CREATED:
                user_access_rule.delete()
                raise RuntimeError(
                    f"Falha ao ativar liberação temporária: {response.data}"
                )

            release.user_access_rule = user_access_rule
            release.status = release.Status.ACTIVE
            release.activated_at = timezone.now()
            release.result_message = "Liberação temporária ativada com sucesso."
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
        device_ids = self._get_device_ids(release)

        with transaction.atomic():
            user_access_rule = release.user_access_rule

            if user_access_rule:
                response = self.delete_in_catraca(
                    user_access_rule, device_ids=device_ids
                )
                if response.status_code != status.HTTP_204_NO_CONTENT:
                    raise RuntimeError(
                        f"Falha ao remover regra temporária: {response.data}"
                    )
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


class TemporaryGroupReleaseService(GroupAccessRulesSyncMixin):
    def _get_device_ids(self, release):
        """Determina quais devices devem receber esta liberação."""
        if release.portal_group:
            return list(
                release.portal_group.active_devices().values_list("id", flat=True)
            )
        return None  # None = todos os devices

    def activate_release(self, release):
        if release.status != release.Status.PENDING:
            return release

        device_ids = self._get_device_ids(release)

        with transaction.atomic():
            existing_group_rule = GroupAccessRule.objects.filter(
                group=release.group,
                access_rule=release.access_rule,
            ).first()

            if existing_group_rule:
                raise ValueError(
                    "O grupo já possui a regra temporária diretamente vinculada."
                )

            group_access_rule = GroupAccessRule.objects.create(
                group=release.group,
                access_rule=release.access_rule,
            )

            response = self.create_in_catraca(group_access_rule, device_ids=device_ids)
            if response.status_code != status.HTTP_201_CREATED:
                group_access_rule.delete()
                raise RuntimeError(
                    f"Falha ao ativar liberação temporária: {response.data}"
                )

            release.group_access_rule = group_access_rule
            release.status = release.Status.ACTIVE
            release.activated_at = timezone.now()
            release.result_message = "Liberação temporária ativada com sucesso."
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
        device_ids = self._get_device_ids(release)

        with transaction.atomic():
            group_access_rule = release.group_access_rule

            if group_access_rule:
                response = self.delete_in_catraca(
                    group_access_rule, device_ids=device_ids
                )
                if response.status_code != status.HTTP_204_NO_CONTENT:
                    raise RuntimeError(
                        f"Falha ao remover regra temporária: {response.data}"
                    )
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
