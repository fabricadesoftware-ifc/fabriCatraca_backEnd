from celery import group, shared_task
import logging

logger = logging.getLogger(__name__)
SCREEN_MESSAGE_TIMEOUT_MS = 3000
SCREEN_MESSAGES = {
    "success": "Setup concluido",
    "partial": "Setup concluido com avisos",
    "failed": "Setup finalizado com falhas",
}


def _is_step_ok(step: dict, treat_missing_as_failure: bool = True) -> bool:
    if not isinstance(step, dict):
        return not treat_missing_as_failure
    return step.get("ok", False)


def _evaluate_easy_setup_report(report: dict) -> tuple[str, list[str], list[str]]:
    from .models import EasySetupLog

    steps = report.get("steps", {})
    push = report.get("steps", {}).get("push", {})
    tables_with_errors = sum(
        1
        for v in push.values()
        if isinstance(v, dict) and not v.get("ok") and not v.get("skipped")
    )

    # O fluxo atual nao executa mais algumas etapas legadas em todas as
    # reconfiguracoes. So avaliamos essas etapas quando elas aparecem no report,
    # evitando marcar uma execucao como failed por uma chave simplesmente ausente.
    critical_steps = {
        "login": _is_step_ok(steps.get("login")),
        "factory_reset": _is_step_ok(steps.get("factory_reset")),
        "device_settings": _is_step_ok(steps.get("device_settings")),
    }
    for legacy_step in ("disable_identifier", "verify_access_rules"):
        if legacy_step in steps:
            critical_steps[legacy_step] = _is_step_ok(steps.get(legacy_step))

    optional_warnings = {
        "datetime": _is_step_ok(
            steps.get("datetime"),
            treat_missing_as_failure=False,
        ),
        "monitor": _is_step_ok(
            steps.get("monitor"),
            treat_missing_as_failure=False,
        ),
    }
    failed_critical = [name for name, ok in critical_steps.items() if not ok]
    warning_steps = [name for name, ok in optional_warnings.items() if not ok]

    if failed_critical:
        log_status = EasySetupLog.Status.FAILED
    elif tables_with_errors > 0 or warning_steps:
        log_status = EasySetupLog.Status.PARTIAL
    else:
        log_status = EasySetupLog.Status.SUCCESS

    report.setdefault("summary", {})
    report["summary"]["failed_critical_steps"] = failed_critical
    report["summary"]["warning_steps"] = warning_steps

    return log_status, failed_critical, warning_steps


def _notify_device_setup_result(engine, device, log_status: str) -> dict:
    message = SCREEN_MESSAGES.get(log_status)
    if not message:
        return {"ok": False, "skipped": True, "reason": "unsupported_status"}

    try:
        response = engine.execute_remote_endpoint(
            endpoint="message_to_screen.fcgi",
            payload={"message": message, "timeout": SCREEN_MESSAGE_TIMEOUT_MS},
            request_timeout=10,
        )
        ok = 200 <= response.status_code < 300
        details = {"ok": ok, "status_code": response.status_code, "message": message}
        try:
            details["response"] = response.json()
        except ValueError:
            details["response"] = response.text or None

        if not ok:
            logger.warning(
                "[EASY_SETUP_TASK] Mensagem final falhou para %s: HTTP %s",
                device.name,
                response.status_code,
            )
        return details
    except Exception as exc:
        logger.warning(
            "[EASY_SETUP_TASK] Nao foi possivel exibir mensagem final em %s: %s",
            device.name,
            exc,
        )
        return {"ok": False, "message": message, "error": str(exc)}


def _run_easy_setup_for_device(device_id: int, task_id: str) -> dict:
    from django.utils import timezone as tz

    from src.core.control_id.infra.control_id_django_app.models import Device
    from .models import EasySetupLog
    from .views.easy_setup_engine import _EasySetupEngine

    device = Device.objects.filter(id=device_id, is_active=True).first()
    if not device:
        logger.warning(
            "[EASY_SETUP_TASK] Device %s nao encontrado ou inativo para task %s",
            device_id,
            task_id,
        )
        return {
            "success": False,
            "device_id": device_id,
            "error": "Device nao encontrado ou inativo",
        }

    log_entry, _ = EasySetupLog.objects.get_or_create(
        task_id=task_id,
        device=device,
        defaults={"status": EasySetupLog.Status.RUNNING},
    )
    log_entry.status = EasySetupLog.Status.RUNNING
    log_entry.started_at = tz.now()
    log_entry.finished_at = None
    log_entry.save(update_fields=["status", "started_at", "finished_at"])

    logger.info(
        f"[EASY_SETUP_TASK] === Iniciando setup: {device.name} ({device.ip}) ==="
    )

    engine = _EasySetupEngine()
    engine.set_device(device)

    try:
        report = engine.run_full_setup()
        log_status, _, _ = _evaluate_easy_setup_report(report)
        report.setdefault("summary", {})
        report["summary"]["screen_message"] = _notify_device_setup_result(
            engine, device, log_status
        )

        log_entry.status = log_status
        log_entry.report = report
        log_entry.finished_at = tz.now()
        log_entry.save(update_fields=["status", "report", "finished_at"])

        logger.info(
            f"[EASY_SETUP_TASK] === Concluido: {device.name} "
            f"[{log_status}] em {report.get('elapsed_s', '?')}s ==="
        )
        return {
            "success": log_status == EasySetupLog.Status.SUCCESS,
            "device_id": device.id,
            "status": log_status,
        }
    except Exception as e:
        logger.exception(f"[EASY_SETUP_TASK] === ERRO: {device.name} - {e} ===")
        failure_report = {"error": str(e), "summary": {}}
        failure_report["summary"]["screen_message"] = _notify_device_setup_result(
            engine,
            device,
            EasySetupLog.Status.FAILED,
        )
        log_entry.status = EasySetupLog.Status.FAILED
        log_entry.report = failure_report
        log_entry.finished_at = tz.now()
        log_entry.save(update_fields=["status", "report", "finished_at"])
        return {"success": False, "device_id": device.id, "error": str(e)}


def _legacy_run_easy_setup_task_v1(self, device_ids: list[int], task_id: str) -> dict:
    """
    Task Celery assíncrona para execução do Easy Setup.
    Cada device recebe seu próprio EasySetupLog com relatório detalhado.
    """
    from django.utils import timezone as tz

    from src.core.control_id.infra.control_id_django_app.models import Device
    from .models import EasySetupLog
    from .views.easy_setup_engine import _EasySetupEngine

    devices = Device.objects.filter(id__in=device_ids, is_active=True)
    if not devices.exists():
        return {"success": False, "error": "Nenhuma catraca ativa encontrada"}

    engine = _EasySetupEngine()
    results = []

    for device in devices:
        # Buscar ou criar log para este device+task
        log_entry, _ = EasySetupLog.objects.get_or_create(
            task_id=task_id,
            device=device,
            defaults={"status": EasySetupLog.Status.RUNNING},
        )
        log_entry.status = EasySetupLog.Status.RUNNING
        log_entry.started_at = tz.now()
        log_entry.finished_at = None
        log_entry.save(update_fields=["status", "started_at", "finished_at"])

        logger.info(
            f"[EASY_SETUP_TASK] ═══ Iniciando setup: {device.name} ({device.ip}) ═══"
        )
        try:
            engine.set_device(device)
            report = engine.run_full_setup()

            # Determinar status baseado no relatório
            push = report.get("steps", {}).get("push", {})
            tables_with_errors = sum(
                1
                for v in push.values()
                if isinstance(v, dict) and not v.get("ok") and not v.get("skipped")
            )
            login_ok = report.get("steps", {}).get("login", {}).get("ok", False)

            if not login_ok:
                log_status = EasySetupLog.Status.FAILED
            elif tables_with_errors > 0:
                log_status = EasySetupLog.Status.PARTIAL
            else:
                log_status = EasySetupLog.Status.SUCCESS

            log_entry.status = log_status
            log_entry.report = report
            log_entry.finished_at = tz.now()
            log_entry.save(update_fields=["status", "report", "finished_at"])

            results.append(report)
            logger.info(
                f"[EASY_SETUP_TASK] ═══ Concluído: {device.name} "
                f"[{log_status}] em {report.get('elapsed_s', '?')}s ═══"
            )
        except Exception as e:
            logger.exception(f"[EASY_SETUP_TASK] ═══ ERRO: {device.name} — {e} ═══")
            log_entry.status = EasySetupLog.Status.FAILED
            log_entry.report = {"error": str(e)}
            log_entry.finished_at = tz.now()
            log_entry.save(update_fields=["status", "report", "finished_at"])
            results.append({"device": device.name, "error": str(e)})

    total_ok = sum(1 for r in results if r.get("steps", {}).get("login", {}).get("ok"))
    return {
        "success": True,
        "task_id": task_id,
        "devices_ok": total_ok,
        "devices_total": len(results),
    }


@shared_task(bind=True)
def run_easy_setup_task(self, device_ids: list[int], task_id: str) -> dict:
    """
    Task Celery ass?ncrona que distribui o Easy Setup por device.
    Cada catraca roda em sua pr?pria subtask para permitir execu??o paralela.
    """
    from src.core.control_id.infra.control_id_django_app.models import Device

    devices = list(Device.objects.filter(id__in=device_ids, is_active=True))
    if not devices:
        return {"success": False, "error": "Nenhuma catraca ativa encontrada"}

    dispatched_ids = [device.id for device in devices]
    group(
        run_easy_setup_for_device.s(device_id=device.id, task_id=task_id)
        for device in devices
    ).apply_async()

    return {
        "success": True,
        "task_id": task_id,
        "devices_ok": 0,
        "devices_total": len(dispatched_ids),
        "dispatched_devices": dispatched_ids,
    }


@shared_task(bind=True)
def run_easy_setup_for_device(self, device_id: int, task_id: str) -> dict:
    """
    Task Celery de execu??o do Easy Setup para um ?nico device.
    """
    return _run_easy_setup_for_device(device_id=device_id, task_id=task_id)


@shared_task(bind=True)
def run_config_sync(self) -> dict:
    """
    Task Celery para sincronização de configurações das catracas.
    Usa os métodos sync dos mixins que chamam get_configuration.fcgi corretamente.

    Returns:
        dict: Resultado da sincronização com estatísticas
    """
    try:
        from src.core.control_id.infra.control_id_django_app.models import Device
        from .mixins.system_config_mixin import SystemConfigSyncMixin
        from .mixins.hardware_config_mixin import HardwareConfigSyncMixin
        from .mixins.security_config_mixin import SecurityConfigSyncMixin
        from .mixins.ui_config_mixin import UIConfigSyncMixin
        from src.core.control_id_monitor.infra.control_id_monitor_django_app.mixins import (
            MonitorConfigSyncMixin,
        )
        from .mixins.catra_config_mixin import CatraConfigSyncMixin
        from .mixins.push_server_config_mixin import PushServerConfigSyncMixin

        devices = list(Device.objects.filter(is_active=True))

        if not devices:
            return {"success": False, "error": "Nenhuma catraca ativa encontrada"}

        print("[CELERY_SYNC] Iniciando sincronização de configurações")
        print(f"[CELERY_SYNC] Dispositivos ativos: {len(devices)}")

        stats = {
            "devices": len(devices),
            "system_synced": 0,
            "hardware_synced": 0,
            "security_synced": 0,
            "ui_synced": 0,
            "monitor_synced": 0,
            "catra_synced": 0,
            "push_server_synced": 0,
            "errors": [],
        }

        for device in devices:
            print(f"[CELERY_SYNC] Sincronizando device: {device.name}")

            # System Config
            try:
                mixin = SystemConfigSyncMixin()
                mixin.set_device(device)
                result = mixin.sync_system_config_from_catraca()
                if result.status_code == 200:
                    stats["system_synced"] += 1
                    print(f"[CELERY_SYNC] ✓ SystemConfig sincronizado")
                else:
                    stats["errors"].append(f"SystemConfig {device.name}: {result.data}")
            except Exception as e:
                stats["errors"].append(f"SystemConfig {device.name}: {str(e)}")
                print(f"[CELERY_SYNC] ✗ Erro SystemConfig: {str(e)}")

            # Hardware Config
            try:
                mixin = HardwareConfigSyncMixin()
                mixin.set_device(device)
                result = mixin.sync_hardware_config_from_catraca()
                if result.status_code == 200:
                    stats["hardware_synced"] += 1
                    print(f"[CELERY_SYNC] ✓ HardwareConfig sincronizado")
                else:
                    stats["errors"].append(
                        f"HardwareConfig {device.name}: {result.data}"
                    )
            except Exception as e:
                stats["errors"].append(f"HardwareConfig {device.name}: {str(e)}")
                print(f"[CELERY_SYNC] ✗ Erro HardwareConfig: {str(e)}")

            # Security Config
            try:
                mixin = SecurityConfigSyncMixin()
                mixin.set_device(device)
                result = mixin.sync_security_config_from_catraca()
                if result.status_code == 200:
                    stats["security_synced"] += 1
                    print(f"[CELERY_SYNC] ✓ SecurityConfig sincronizado")
                else:
                    stats["errors"].append(
                        f"SecurityConfig {device.name}: {result.data}"
                    )
            except Exception as e:
                stats["errors"].append(f"SecurityConfig {device.name}: {str(e)}")
                print(f"[CELERY_SYNC] ✗ Erro SecurityConfig: {str(e)}")

            # UI Config
            try:
                mixin = UIConfigSyncMixin()
                mixin.set_device(device)
                result = mixin.sync_ui_config_from_catraca()
                if result.status_code == 200:
                    stats["ui_synced"] += 1
                    print(f"[CELERY_SYNC] ✓ UIConfig sincronizado")
                else:
                    stats["errors"].append(f"UIConfig {device.name}: {result.data}")
            except Exception as e:
                stats["errors"].append(f"UIConfig {device.name}: {str(e)}")
                print(f"[CELERY_SYNC] ✗ Erro UIConfig: {str(e)}")

            # Monitor Config (opcional - nem todos os dispositivos têm)
            try:
                mixin = MonitorConfigSyncMixin()
                mixin.set_device(device)
                result = mixin.sync_monitor_config_from_catraca()

                # Verifica se é uma situação normal (não configurado) ou erro real
                is_missing = (
                    result.data.get("is_configuration_missing", False)
                    if hasattr(result, "data") and isinstance(result.data, dict)
                    else False
                )

                if result.status_code == 200:
                    stats["monitor_synced"] += 1
                    print("[CELERY_SYNC] ✓ MonitorConfig sincronizado")
                elif result.status_code == 404 and is_missing:
                    # 404 com flag is_configuration_missing = situação normal
                    print(
                        f"[CELERY_SYNC] ℹ️  MonitorConfig não configurado no device {device.name} (normal)"
                    )
                else:
                    # Erro real
                    stats["errors"].append(
                        f"MonitorConfig {device.name}: {result.data}"
                    )
                    print(f"[CELERY_SYNC] ✗ Erro MonitorConfig: {result.data}")
            except Exception as e:
                stats["errors"].append(f"MonitorConfig {device.name}: {str(e)}")
                print(f"[CELERY_SYNC] ✗ Erro MonitorConfig: {str(e)}")

            # Catra Config
            try:
                mixin = CatraConfigSyncMixin()
                mixin.set_device(device)
                result = mixin.sync_catra_config_from_catraca()
                if result.status_code == 200:
                    stats["catra_synced"] += 1
                    print(f"[CELERY_SYNC] ✓ CatraConfig sincronizado")
                else:
                    stats["errors"].append(f"CatraConfig {device.name}: {result.data}")
            except Exception as e:
                stats["errors"].append(f"CatraConfig {device.name}: {str(e)}")
                print(f"[CELERY_SYNC] ✗ Erro CatraConfig: {str(e)}")

            # Push Server Config
            try:
                mixin = PushServerConfigSyncMixin()
                mixin.set_device(device)
                result = mixin.sync_push_server_config_from_catraca()
                if result.status_code == 200:
                    stats["push_server_synced"] += 1
                    print(f"[CELERY_SYNC] ✓ PushServerConfig sincronizado")
                else:
                    stats["errors"].append(
                        f"PushServerConfig {device.name}: {result.data}"
                    )
            except Exception as e:
                stats["errors"].append(f"PushServerConfig {device.name}: {str(e)}")
                print(f"[CELERY_SYNC] ✗ Erro PushServerConfig: {str(e)}")

        print("[CELERY_SYNC] Sincronização concluída")
        print(f"[CELERY_SYNC] Stats: {stats}")

        return {"success": True, "message": "Sincronização concluída", "stats": stats}
    except Exception as e:
        return {"success": False, "error": f"Erro na task de sincronização: {str(e)}"}
