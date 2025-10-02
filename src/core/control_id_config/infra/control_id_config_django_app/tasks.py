from celery import shared_task


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
        from src.core.control_id_monitor.infra.control_id_monitor_django_app.mixins import MonitorConfigSyncMixin
        from .mixins.catra_config_mixin import CatraConfigSyncMixin
        from .mixins.push_server_config_mixin import PushServerConfigSyncMixin
        
        devices = list(Device.objects.filter(is_active=True))
        
        if not devices:
            return {"success": False, "error": "Nenhuma catraca ativa encontrada"}
        
        print("[CELERY_SYNC] Iniciando sincronização de configurações")
        print(f"[CELERY_SYNC] Dispositivos ativos: {len(devices)}")
        
        stats = {
            'devices': len(devices),
            'system_synced': 0,
            'hardware_synced': 0,
            'security_synced': 0,
            'ui_synced': 0,
            'monitor_synced': 0,
            'catra_synced': 0,
            'push_server_synced': 0,
            'errors': []
        }
        
        for device in devices:
            print(f"[CELERY_SYNC] Sincronizando device: {device.name}")
            
            # System Config
            try:
                mixin = SystemConfigSyncMixin()
                mixin.set_device(device)
                result = mixin.sync_system_config_from_catraca()
                if result.status_code == 200:
                    stats['system_synced'] += 1
                    print(f"[CELERY_SYNC] ✓ SystemConfig sincronizado")
                else:
                    stats['errors'].append(f"SystemConfig {device.name}: {result.data}")
            except Exception as e:
                stats['errors'].append(f"SystemConfig {device.name}: {str(e)}")
                print(f"[CELERY_SYNC] ✗ Erro SystemConfig: {str(e)}")
            
            # Hardware Config
            try:
                mixin = HardwareConfigSyncMixin()
                mixin.set_device(device)
                result = mixin.sync_hardware_config_from_catraca()
                if result.status_code == 200:
                    stats['hardware_synced'] += 1
                    print(f"[CELERY_SYNC] ✓ HardwareConfig sincronizado")
                else:
                    stats['errors'].append(f"HardwareConfig {device.name}: {result.data}")
            except Exception as e:
                stats['errors'].append(f"HardwareConfig {device.name}: {str(e)}")
                print(f"[CELERY_SYNC] ✗ Erro HardwareConfig: {str(e)}")
            
            # Security Config
            try:
                mixin = SecurityConfigSyncMixin()
                mixin.set_device(device)
                result = mixin.sync_security_config_from_catraca()
                if result.status_code == 200:
                    stats['security_synced'] += 1
                    print(f"[CELERY_SYNC] ✓ SecurityConfig sincronizado")
                else:
                    stats['errors'].append(f"SecurityConfig {device.name}: {result.data}")
            except Exception as e:
                stats['errors'].append(f"SecurityConfig {device.name}: {str(e)}")
                print(f"[CELERY_SYNC] ✗ Erro SecurityConfig: {str(e)}")
            
            # UI Config
            try:
                mixin = UIConfigSyncMixin()
                mixin.set_device(device)
                result = mixin.sync_ui_config_from_catraca()
                if result.status_code == 200:
                    stats['ui_synced'] += 1
                    print(f"[CELERY_SYNC] ✓ UIConfig sincronizado")
                else:
                    stats['errors'].append(f"UIConfig {device.name}: {result.data}")
            except Exception as e:
                stats['errors'].append(f"UIConfig {device.name}: {str(e)}")
                print(f"[CELERY_SYNC] ✗ Erro UIConfig: {str(e)}")
            
            # Monitor Config (opcional - nem todos os dispositivos têm)
            try:
                mixin = MonitorConfigSyncMixin()
                mixin.set_device(device)
                result = mixin.sync_monitor_config_from_catraca()
                
                # Verifica se é uma situação normal (não configurado) ou erro real
                is_missing = result.data.get('is_configuration_missing', False) if hasattr(result, 'data') and isinstance(result.data, dict) else False
                
                if result.status_code == 200:
                    stats['monitor_synced'] += 1
                    print("[CELERY_SYNC] ✓ MonitorConfig sincronizado")
                elif result.status_code == 404 and is_missing:
                    # 404 com flag is_configuration_missing = situação normal
                    print(f"[CELERY_SYNC] ℹ️  MonitorConfig não configurado no device {device.name} (normal)")
                else:
                    # Erro real
                    stats['errors'].append(f"MonitorConfig {device.name}: {result.data}")
                    print(f"[CELERY_SYNC] ✗ Erro MonitorConfig: {result.data}")
            except Exception as e:
                stats['errors'].append(f"MonitorConfig {device.name}: {str(e)}")
                print(f"[CELERY_SYNC] ✗ Erro MonitorConfig: {str(e)}")
            
            # Catra Config
            try:
                mixin = CatraConfigSyncMixin()
                mixin.set_device(device)
                result = mixin.sync_catra_config_from_catraca()
                if result.status_code == 200:
                    stats['catra_synced'] += 1
                    print(f"[CELERY_SYNC] ✓ CatraConfig sincronizado")
                else:
                    stats['errors'].append(f"CatraConfig {device.name}: {result.data}")
            except Exception as e:
                stats['errors'].append(f"CatraConfig {device.name}: {str(e)}")
                print(f"[CELERY_SYNC] ✗ Erro CatraConfig: {str(e)}")
            
            # Push Server Config
            try:
                mixin = PushServerConfigSyncMixin()
                mixin.set_device(device)
                result = mixin.sync_push_server_config_from_catraca()
                if result.status_code == 200:
                    stats['push_server_synced'] += 1
                    print(f"[CELERY_SYNC] ✓ PushServerConfig sincronizado")
                else:
                    stats['errors'].append(f"PushServerConfig {device.name}: {result.data}")
            except Exception as e:
                stats['errors'].append(f"PushServerConfig {device.name}: {str(e)}")
                print(f"[CELERY_SYNC] ✗ Erro PushServerConfig: {str(e)}")
        
        print("[CELERY_SYNC] Sincronização concluída")
        print(f"[CELERY_SYNC] Stats: {stats}")
        
        return {
            "success": True,
            "message": "Sincronização concluída",
            "stats": stats
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Erro na task de sincronização: {str(e)}"
        }


