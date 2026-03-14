import logging

from celery import shared_task
from django.utils import timezone

from src.core.control_Id.infra.control_id_django_app.views.sync import GlobalSyncMixin
from src.core.control_Id.infra.control_id_django_app.models import (
    AccessLogs,
    Device,
    TemporaryUserRelease,
)
from src.core.control_Id.infra.control_id_django_app.temporary_release_service import (
    TemporaryUserReleaseService,
)
from .sync_collect import collect_all
from .sync_persist import persist_all

logger = logging.getLogger(__name__)
GRANTED_EVENT_TYPES = [7, 11, 12, 15]
DESISTANCE_EVENT_TYPE = 13


@shared_task(bind=True)
def run_global_sync(self) -> dict:
    sync = GlobalSyncMixin()
    devices = list(Device.objects.filter(is_active=True))
    if not devices:
        return {"success": False, "error": "Nenhuma catraca ativa encontrada"}

    (
        all_users,
        all_time_zones,
        all_time_spans,
        all_access_rules,
        all_portals,
        all_areas,
        all_templates,
        all_cards,
        all_user_access_rules,
        all_portal_access_rules,
        all_access_rule_time_zones,
        all_group_access_rules,
        all_user_groups,
        all_groups,
        all_access_logs,
    ) = collect_all(sync, devices)

    persist_all(
        all_users,
        all_time_zones,
        all_time_spans,
        all_access_rules,
        all_portals,
        all_areas,
        all_templates,
        all_cards,
        all_user_access_rules,
        all_portal_access_rules,
        all_access_rule_time_zones,
        all_group_access_rules,
        all_user_groups,
        all_groups,
        all_access_logs,
    )

    return {
        "success": True,
        "message": "Sincronização global concluída com sucesso",
        "stats": {
            "users": len(all_users),
            "time_zones": len(all_time_zones),
            "time_spans": len(all_time_spans),
            "access_rules": len(all_access_rules),
            "areas": len(all_areas),
            "portals": len(all_portals),
            "templates": len(all_templates),
            "cards": len(all_cards),
            "user_access_rules": len(all_user_access_rules),
            "portal_access_rules": len(all_portal_access_rules),
            "access_rule_time_zones": len(all_access_rule_time_zones),
            "groups": len(all_groups),
            "user_groups": len(all_user_groups),
            "group_access_rules": len(all_group_access_rules),
            "devices": len(devices),
            "access_logs": len(all_access_logs),
        },
    }


@shared_task(bind=True)
def process_temporary_user_releases(self) -> dict:
    service = TemporaryUserReleaseService()
    now = timezone.now()

    stats = {
        "processed": 0,
        "activated": 0,
        "consumed": 0,
        "expired": 0,
        "failed": 0,
    }

    pending_releases = list(
        TemporaryUserRelease.objects.select_related("user", "access_rule").filter(
            status=TemporaryUserRelease.Status.PENDING,
            valid_from__lte=now,
        )
    )

    active_releases = list(
        TemporaryUserRelease.objects.select_related(
            "user",
            "access_rule",
            "user_access_rule",
        ).filter(status=TemporaryUserRelease.Status.ACTIVE)
    )

    for release in pending_releases:
        stats["processed"] += 1

        if release.valid_until <= now:
            release.status = release.Status.EXPIRED
            release.closed_at = now
            release.result_message = "Liberação expirou antes de ser ativada."
            release.save(update_fields=["status", "closed_at", "result_message", "updated_at"])
            stats["expired"] += 1
            continue

        try:
            service.activate_release(release)
            stats["activated"] += 1
        except Exception as exc:
            logger.exception("Erro ao ativar liberação temporária %s", release.id)
            service.fail_release(
                release,
                result_message=f"Falha ao ativar liberação temporária: {exc}",
            )
            stats["failed"] += 1

    refreshed_active_releases = list(
        TemporaryUserRelease.objects.select_related(
            "user",
            "access_rule",
            "user_access_rule",
        ).filter(status=TemporaryUserRelease.Status.ACTIVE)
    )

    for release in refreshed_active_releases:
        stats["processed"] += 1

        consumed_log = (
            AccessLogs.objects.filter(
                user=release.user,
                access_rule=release.access_rule,
                time__gte=release.activated_at or release.valid_from,
                event_type__in=GRANTED_EVENT_TYPES,
            )
            .order_by("time")
            .first()
        )

        if consumed_log:
            try:
                service.close_release(
                    release,
                    final_status=release.Status.CONSUMED,
                    result_message="Liberação utilizada com sucesso.",
                    consumed_log=consumed_log,
                    consumed_at=consumed_log.time,
                )
                stats["consumed"] += 1
            except Exception as exc:
                logger.exception("Erro ao finalizar liberação consumida %s", release.id)
                service.fail_release(
                    release,
                    result_message=f"Falha ao encerrar liberação consumida: {exc}",
                )
                stats["failed"] += 1
            continue

        if release.valid_until > now:
            continue

        desistance_log = (
            AccessLogs.objects.filter(
                user=release.user,
                access_rule=release.access_rule,
                time__gte=release.activated_at or release.valid_from,
                event_type=DESISTANCE_EVENT_TYPE,
            )
            .order_by("time")
            .first()
        )

        result_message = (
            "Usuário desistiu da entrada após a liberação temporária."
            if desistance_log
            else "Usuário não utilizou a liberação temporária."
        )

        try:
            service.close_release(
                release,
                final_status=release.Status.EXPIRED,
                result_message=result_message,
            )
            stats["expired"] += 1
        except Exception as exc:
            logger.exception("Erro ao expirar liberação temporária %s", release.id)
            service.fail_release(
                release,
                result_message=f"Falha ao expirar liberação temporária: {exc}",
            )
            stats["failed"] += 1

    return {"success": True, "stats": stats}
