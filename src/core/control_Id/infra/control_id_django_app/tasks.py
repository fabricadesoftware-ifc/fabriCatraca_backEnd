import logging

from celery import shared_task
from django.utils import timezone

from src.core.control_id_monitor.infra.control_id_monitor_django_app.monitoring import (
    create_temporary_release_delay_alert,
)
from src.core.control_Id.infra.control_id_django_app.views.sync import GlobalSyncMixin
from src.core.control_Id.infra.control_id_django_app.models import (
    AccessLogs,
    Device,
    TemporaryUserRelease,
    TemporaryGroupRelease,
)
from src.core.control_Id.infra.control_id_django_app.temporary_release_service import (
    TemporaryUserReleaseService,
    TemporaryGroupReleaseService,
)
from src.core.control_Id.infra.control_id_django_app.release_audit_service import (
    ReleaseAuditService,
)
from src.core.control_Id.infra.control_id_django_app.temporary_release_notification_service import (
    TemporaryUserReleaseNotificationService,
)

logger = logging.getLogger(__name__)
GRANTED_EVENT_TYPES = [7, 11, 12, 15]
DESISTANCE_EVENT_TYPE = 13


@shared_task(bind=True)
def send_temporary_user_release_notification(self, release_id: int) -> dict:
    try:
        release = TemporaryUserRelease.objects.select_related(
            "user",
            "requested_by",
            "notified_server",
        ).get(pk=release_id)
    except TemporaryUserRelease.DoesNotExist:
        logger.warning(
            "[RELEASE] User release %d nao encontrado ao enviar notificacao por e-mail.",
            release_id,
        )
        return {"success": False, "error": "Release not found"}

    if not release.notified_server_id:
        logger.info(
            "[RELEASE] User release %d nao possui servidor para notificacao.",
            release_id,
        )
        return {"success": False, "skipped": True, "reason": "no_notified_server"}

    try:
        TemporaryUserReleaseNotificationService.notify_release_created(release)
        return {"success": True}
    except Exception as exc:
        logger.exception(
            "Erro ao enviar e-mail da liberacao temporaria %d: %s",
            release_id,
            exc,
        )
        return {"success": False, "error": str(exc)}


# ============================================================================
# Scheduled tasks (eta=valid_from ou valid_until)
# Agendadas via apply_async quando o release e criado ou ativado.
# Verificam o status no momento da execucao e ignoram se ja mudou,
# garantindo idempotencia mesmo que a task seja chamada mais de uma vez.
# ============================================================================

@shared_task(bind=True)
def activate_user_release(self, release_id: int) -> dict:
    """Ativa um release pendente — agendado com eta=valid_from."""
    from celery.app.task import Ignore

    try:
        release = TemporaryUserRelease.objects.select_related("user", "access_rule").get(
            pk=release_id
        )
    except TemporaryUserRelease.DoesNotExist:
        logger.warning("[RELEASE] User release %d nao encontrado ao executar ativacao.", release_id)
        return {"success": False, "error": "Release not found"}

    if release.status != TemporaryUserRelease.Status.PENDING:
        logger.info(
            "[RELEASE] Release user %d ja esta em status '%s' — ignorando ativacao.",
            release_id, release.status,
        )
        return {"success": False, "skipped": True, "reason": f"status={release.status}"}

    if release.valid_until <= timezone.now():
        release.status = release.Status.EXPIRED
        release.closed_at = timezone.now()
        release.result_message = "Liberação expirou antes de ser ativada."
        release.save(update_fields=["status", "closed_at", "result_message", "updated_at"])
        ReleaseAuditService.sync_from_temporary_release(release)
        logger.info("[RELEASE] Release user %d expirou antes de ativar.", release_id)
        return {"success": False, "expired": True}

    service = TemporaryUserReleaseService()
    try:
        service.activate_release(release)
        logger.info("[RELEASE] User release %d ativado via scheduled task.", release_id)
        return {"success": True}
    except Exception as exc:
        logger.exception("Erro ao ativar scheduled release user %d: %s", release_id, exc)
        service.fail_release(
            release,
            result_message=f"Falha ao agendar liberação temporária: {exc}",
        )
        return {"success": False, "error": str(exc)}


@shared_task(bind=True)
def activate_group_release(self, release_id: int) -> dict:
    """Ativa um release de grupo pendente — agendado com eta=valid_from."""
    try:
        release = TemporaryGroupRelease.objects.select_related("group", "access_rule").get(
            pk=release_id
        )
    except TemporaryGroupRelease.DoesNotExist:
        logger.warning("[RELEASE] Group release %d nao encontrado ao executar ativacao.", release_id)
        return {"success": False, "error": "Release not found"}

    if release.status != TemporaryGroupRelease.Status.PENDING:
        logger.info(
            "[RELEASE] Group release %d ja esta em status '%s' — ignorando ativacao.",
            release_id, release.status,
        )
        return {"success": False, "skipped": True, "reason": f"status={release.status}"}

    if release.valid_until <= timezone.now():
        release.status = TemporaryGroupRelease.Status.EXPIRED
        release.closed_at = timezone.now()
        release.result_message = "Liberação expirou antes de ser ativada."
        release.save(update_fields=["status", "closed_at", "result_message", "updated_at"])
        ReleaseAuditService.sync_from_temporary_release(release)
        logger.info("[RELEASE] Group release %d expirou antes de ativar.", release_id)
        return {"success": False, "expired": True}

    service = TemporaryGroupReleaseService()
    try:
        service.activate_release(release)
        logger.info("[RELEASE] Group release %d ativado via scheduled task.", release_id)
        return {"success": True}
    except Exception as exc:
        logger.exception("Erro ao ativar scheduled group release %d: %s", release_id, exc)
        service.fail_release(
            release,
            result_message=f"Falha ao agendar liberação de turma: {exc}",
        )
        return {"success": False, "error": str(exc)}


@shared_task(bind=True)
def expire_user_release(self, release_id: int) -> dict:
    """Verifica e expira um release ativo que passou de valid_until."""
    try:
        release = TemporaryUserRelease.objects.select_related(
            "user", "access_rule", "user_access_rule"
        ).get(pk=release_id)
    except TemporaryUserRelease.DoesNotExist:
        logger.warning("[RELEASE] User release %d nao encontrado ao expirar.", release_id)
        return {"success": False, "error": "Release not found"}

    if release.status != TemporaryUserRelease.Status.ACTIVE:
        logger.info(
            "[RELEASE] User release %d ja esta em status '%s' — ignorando expiracao.",
            release_id, release.status,
        )
        return {"success": False, "skipped": True, "reason": f"status={release.status}"}

    # Antes de expirar, verifica se o usuario consumiu
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

    service = TemporaryUserReleaseService()
    if consumed_log:
        try:
            service.close_release(
                release,
                final_status=release.Status.CONSUMED,
                result_message="Liberação utilizada com sucesso.",
                consumed_log=consumed_log,
                consumed_at=consumed_log.time,
            )
            create_temporary_release_delay_alert(
                release,
                consumed_log=consumed_log,
                consumed_at=consumed_log.time,
            )
            logger.info("[RELEASE] User release %d consumido via scheduled expire.", release_id)
            return {"success": True, "consumed": True}
        except Exception as exc:
            logger.exception("Erro ao fechar release %d consumido.", release_id)
            service.fail_release(
                release,
                result_message=f"Falha ao encerrar liberação consumida: {exc}",
            )
            return {"success": False, "error": str(exc)}

    # Nao consumiu — verifica desistencia ou expira
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
        logger.info("[RELEASE] User release %d expirado via scheduled task.", release_id)
        return {"success": True}
    except Exception as exc:
        logger.exception("Erro ao expirar release %d.", release_id)
        service.fail_release(
            release,
            result_message=f"Falha ao expirar liberação temporária: {exc}",
        )
        return {"success": False, "error": str(exc)}


@shared_task(bind=True)
def expire_group_release(self, release_id: int) -> dict:
    """Verifica e expira um release de grupo ativo."""
    try:
        release = TemporaryGroupRelease.objects.select_related(
            "group", "access_rule", "group_access_rule"
        ).get(pk=release_id)
    except TemporaryGroupRelease.DoesNotExist:
        logger.warning("[RELEASE] Group release %d nao encontrado ao expirar.", release_id)
        return {"success": False, "error": "Release not found"}

    if release.status != TemporaryGroupRelease.Status.ACTIVE:
        logger.info(
            "[RELEASE] Group release %d ja esta em status '%s' — ignorando expiracao.",
            release_id, release.status,
        )
        return {"success": False, "skipped": True, "reason": f"status={release.status}"}

    consumed_log = (
        AccessLogs.objects.filter(
            user__groups=release.group,
            access_rule=release.access_rule,
            time__gte=release.activated_at or release.valid_from,
            event_type__in=GRANTED_EVENT_TYPES,
        )
        .order_by("time")
        .first()
    )

    service = TemporaryGroupReleaseService()
    if consumed_log:
        try:
            service.close_release(
                release,
                final_status=release.Status.CONSUMED,
                result_message="Liberação de turma utilizada com sucesso.",
                consumed_log=consumed_log,
                consumed_at=consumed_log.time,
            )
            logger.info("[RELEASE] Group release %d consumido via scheduled expire.", release_id)
            return {"success": True, "consumed": True}
        except Exception as exc:
            logger.exception("Erro ao fechar group release %d consumido.", release_id)
            service.fail_release(
                release,
                result_message=f"Falha ao encerrar liberação de turma consumida: {exc}",
            )
            return {"success": False, "error": str(exc)}

    desistance_log = (
        AccessLogs.objects.filter(
            user__groups=release.group,
            access_rule=release.access_rule,
            time__gte=release.activated_at or release.valid_from,
            event_type=DESISTANCE_EVENT_TYPE,
        )
        .order_by("time")
        .first()
    )

    result_message = (
        "Turma desistiu da entrada após a liberação temporária."
        if desistance_log
        else "Turma não utilizou a liberação temporária."
    )

    try:
        service.close_release(
            release,
            final_status=release.Status.EXPIRED,
            result_message=result_message,
        )
        logger.info("[RELEASE] Group release %d expirado via scheduled task.", release_id)
        return {"success": True}
    except Exception as exc:
        logger.exception("Erro ao expirar group release %d.", release_id)
        service.fail_release(
            release,
            result_message=f"Falha ao expirar liberação de turma: {exc}",
        )
        return {"success": False, "error": str(exc)}


# ============================================================================
# Safety net — roda a cada 10 min para recapturar tasks orfas (worker restart)
# So processa releases que ficaram "presas" devido a perda de eta.
# ============================================================================

@shared_task(bind=True)
def reconcile_temporary_releases(self) -> dict:
    """
    Safety net para releases que ficaram orfas por restart do worker.
    Roda a cada ~10 min e so faz algo se houver releases inconsistentes.
    """
    now = timezone.now()
    stats = {"orphan_activated": 0, "orphan_expired": 0, "checked": 0}

    # 1. Pendentes que ja passaram de valid_from e nao tem eta task
    orphan_pending_user = TemporaryUserRelease.objects.filter(
        status=TemporaryUserRelease.Status.PENDING,
        valid_from__lte=now,
        valid_until__gt=now,
    )
    for release in orphan_pending_user:
        stats["checked"] += 1
        try:
            TemporaryUserReleaseService().activate_release(release)
            stats["orphan_activated"] += 1
        except Exception:
            logger.exception("[RECONCILE] Falha ao ativar orphan release %d", release.id)

    orphan_pending_group = TemporaryGroupRelease.objects.filter(
        status=TemporaryGroupRelease.Status.PENDING,
        valid_from__lte=now,
        valid_until__gt=now,
    )
    for release in orphan_pending_group:
        stats["checked"] += 1
        try:
            TemporaryGroupReleaseService().activate_release(release)
            stats["orphan_activated"] += 1
        except Exception:
            logger.exception("[RECONCILE] Falha ao ativar orphan group release %d", release.id)

    # 2. Ativos que ja passaram de valid_until e nao foram consumidos
    orphan_active_user = TemporaryUserRelease.objects.filter(
        status=TemporaryUserRelease.Status.ACTIVE,
        valid_until__lte=now,
    )
    for release in orphan_active_user:
        stats["checked"] += 1
        try:
            expire_user_release.delay(release.id)
            stats["orphan_expired"] += 1
        except Exception:
            logger.exception("[RECONCILE] Falha ao expirar orphan active release %d", release.id)

    orphan_active_group = TemporaryGroupRelease.objects.filter(
        status=TemporaryGroupRelease.Status.ACTIVE,
        valid_until__lt=now,
    )
    for release in orphan_active_group:
        stats["checked"] += 1
        try:
            expire_group_release.delay(release.id)
            stats["orphan_expired"] += 1
        except Exception:
            logger.exception("[RECONCILE] Falha ao expirar orphan active group release %d", release.id)

    if stats["checked"] > 0:
        logger.info(
            "[RECONCILE] Verificou %d releases, ativou %d, expirou %d",
            stats["checked"], stats["orphan_activated"], stats["orphan_expired"],
        )

    return {"success": True, "stats": stats}


# ============================================================================
# Legacy polling — mantido para back-compat mas nao sera mais usado
# ============================================================================



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
            ReleaseAuditService.sync_from_temporary_release(release)
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
                create_temporary_release_delay_alert(
                    release,
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


@shared_task(bind=True)
def process_temporary_group_releases(self) -> dict:
    service = TemporaryGroupReleaseService()
    now = timezone.now()

    stats = {
        "processed": 0,
        "activated": 0,
        "consumed": 0,
        "expired": 0,
        "failed": 0,
    }

    pending_releases = list(
        TemporaryGroupRelease.objects.select_related("group", "access_rule").filter(
            status=TemporaryGroupRelease.Status.PENDING,
            valid_from__lte=now,
        )
    )

    for release in pending_releases:
        stats["processed"] += 1

        if release.valid_until <= now:
            release.status = release.Status.EXPIRED
            release.closed_at = now
            release.result_message = "Liberação expirou antes de ser ativada."
            release.save(update_fields=["status", "closed_at", "result_message", "updated_at"])
            ReleaseAuditService.sync_from_temporary_release(release)
            stats["expired"] += 1
            continue

        try:
            service.activate_release(release)
            stats["activated"] += 1
        except Exception as exc:
            logger.exception("Erro ao ativar liberação temporária de turma %s", release.id)
            service.fail_release(
                release,
                result_message=f"Falha ao ativar liberação de turma: {exc}",
            )
            stats["failed"] += 1

    refreshed_active_releases = list(
        TemporaryGroupRelease.objects.select_related(
            "group",
            "access_rule",
            "group_access_rule",
        ).filter(status=TemporaryGroupRelease.Status.ACTIVE)
    )

    for release in refreshed_active_releases:
        stats["processed"] += 1

        # Verifica se qualquer usuário do grupo utilizou a liberação
        consumed_log = (
            AccessLogs.objects.filter(
                user__groups=release.group,
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
                    result_message="Liberação de turma utilizada com sucesso.",
                    consumed_log=consumed_log,
                    consumed_at=consumed_log.time,
                )
                stats["consumed"] += 1
            except Exception as exc:
                logger.exception("Erro ao finalizar liberação de turma consumida %s", release.id)
                service.fail_release(
                    release,
                    result_message=f"Falha ao encerrar liberação de turma consumida: {exc}",
                )
                stats["failed"] += 1
            continue

        if release.valid_until > now:
            continue

        desistance_log = (
            AccessLogs.objects.filter(
                user__groups=release.group,
                access_rule=release.access_rule,
                time__gte=release.activated_at or release.valid_from,
                event_type=DESISTANCE_EVENT_TYPE,
            )
            .order_by("time")
            .first()
        )

        result_message = (
            "Turma desistiu da entrada após a liberação temporária."
            if desistance_log
            else "Turma não utilizou a liberação temporária."
        )

        try:
            service.close_release(
                release,
                final_status=release.Status.EXPIRED,
                result_message=result_message,
            )
            stats["expired"] += 1
        except Exception as exc:
            logger.exception("Erro ao expirar liberação de turma %s", release.id)
            service.fail_release(
                release,
                result_message=f"Falha ao expirar liberação de turma: {exc}",
            )
            stats["failed"] += 1

    return {"success": True, "stats": stats}
