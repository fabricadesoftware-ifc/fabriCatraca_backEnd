from django.db import transaction
from django.utils import timezone
from rest_framework import status

from src.core.__seedwork__.infra.mixins import UserAccessRuleSyncMixin
from src.core.control_Id.infra.control_id_django_app.models import UserAccessRule
from src.core.control_Id.infra.control_id_django_app.release_audit_service import (
    ReleaseAuditService,
)


class TemporaryUserReleaseService(UserAccessRuleSyncMixin):
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
                    "O usuário já possui a regra temporária diretamente vinculada."
                )

            user_access_rule = UserAccessRule.objects.create(
                user=release.user,
                access_rule=release.access_rule,
            )

            response = self.create_in_catraca(user_access_rule)
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
        with transaction.atomic():
            user_access_rule = release.user_access_rule

            if user_access_rule:
                response = self.delete_in_catraca(user_access_rule)
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
        release.save(update_fields=["status", "closed_at", "result_message", "updated_at"])
        ReleaseAuditService.sync_from_temporary_release(release)
        return release
