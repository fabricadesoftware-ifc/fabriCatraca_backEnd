from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def run_easy_setup_task(self, device_ids: list[int], task_id: str) -> dict:
    """
    Task Celery assíncrona para execução do Easy Setup.
    Cada device recebe seu próprio EasySetupLog com relatório detalhado.
    """
    from django.utils import timezone as tz

    from src.core.control_Id.infra.control_id_django_app.models import Device
    from .models import EasySetupLog
    from .views.easy_setup import _EasySetupEngine

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
        log_entry.save(update_fields=["status"])

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
def run_config_sync(self) -> dict:
    """
    Task Celery para sincronização de configurações das catracas.
    Usa os métodos sync dos mixins que chamam get_configuration.fcgi corretamente.

    Returns:
        dict: Resultado da sincronização com estatísticas
    """
    try:
        from src.core.control_Id.infra.control_id_django_app.models import Device
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
