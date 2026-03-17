from typing import Dict, List, Any, Tuple
from src.core.control_Id.infra.control_id_django_app.models import Device


def collect_config_data(devices) -> Dict[int, Dict[str, Any]]:
    """
    Coleta dados de configuração de todos os dispositivos ativos.
    
    Args:
        devices: Lista de dispositivos ativos
        
    Returns:
        Dict com dados de configuração por dispositivo
    """
    config_data = {}
    
    print("[CONFIG_SYNC] Iniciando coleta de configurações")
    
    for device in devices:
        try:
            # Cria uma instância do ControlIDSyncMixin para este dispositivo
            from src.core.__seedwork__.infra import ControlIDSyncMixin
            sync_mixin = ControlIDSyncMixin()
            sync_mixin.set_device(device)
            device_id = device.id
            
            print(f"[CONFIG_SYNC] Coletando configurações do dispositivo {device.name}")
            
            # Coleta configurações usando get_configuration.fcgi
            general = {}
            identifier = {}
            monitor = {}
            try:
                # Usa get_configuration.fcgi especificando os campos necessários
                import requests
                sess = sync_mixin.login()
                
                # Payload solicitando seções completas
                # Array vazio retorna TODOS os campos disponíveis
                payload = {
                    "general": [],
                    "identifier": [],
                    "monitor": []
                }
                
                response = requests.post(
                    sync_mixin.get_url(f"get_configuration.fcgi?session={sess}"),
                    json=payload
                )
                if response.status_code == 200:
                    cfg_payload = response.json() or {}
                    general = cfg_payload.get('general', {})
                    identifier = cfg_payload.get('identifier', {})
                    monitor = cfg_payload.get('monitor', {})
                    print(f"[CONFIG_SYNC] Configurações obtidas com sucesso do dispositivo {device.name}")
                    print(f"[CONFIG_SYNC] 🔍 DEBUG - Response JSON COMPLETO:")
                    import json
                    print(json.dumps(cfg_payload, indent=2))
                    print(f"[CONFIG_SYNC] 🔍 DEBUG - Valores RAW da API:")
                    print(f"[CONFIG_SYNC]   online (raw): {repr(general.get('online'))}")
                    print(f"[CONFIG_SYNC]   beep_enabled (raw): {repr(general.get('beep_enabled'))}")
                    print(f"[CONFIG_SYNC]   clear_expired_users (raw): {repr(general.get('clear_expired_users'))}")
                else:
                    print(f"[CONFIG_SYNC] Erro ao obter configurações: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"[CONFIG_SYNC] Erro ao coletar configurações: {str(e)}")
            
            # Função auxiliar para converter valores booleanos da API
            def to_bool(v, default=False):
                """Converte string '0'/'1' da API Control iD para bool."""
                if v is None:
                    return bool(default)
                if isinstance(v, bool):
                    return v
                if isinstance(v, str):
                    # Retorna True APENAS se string for "1", "true" ou "True"
                    return v.strip() in ("1", "true", "True")
                # Para números: 0 = False, qualquer outro = True
                if isinstance(v, (int, float)):
                    return v != 0
                return bool(v)
            
            # Configurações do sistema
            system_config = {
                'auto_reboot_hour': general.get('auto_reboot_hour', 3),
                'auto_reboot_minute': general.get('auto_reboot_minute', 0),
                'clear_expired_users': to_bool(general.get('clear_expired_users'), False),
                'url_reboot_enabled': to_bool(general.get('url_reboot_enabled'), True),
                'keep_user_image': to_bool(general.get('keep_user_image'), True),
                'catra_timeout': general.get('catra_timeout', 30),
                'online': to_bool(general.get('online'), True),
                'local_identification': to_bool(general.get('local_identification'), True),
                'language': general.get('language', 'pt'),
                'daylight_savings_time_start': general.get('daylight_savings_time_start'),
                'daylight_savings_time_end': general.get('daylight_savings_time_end'),
                'web_server_enabled': to_bool(general.get('web_server_enabled'), True)
            }
            
            # Debug: Mostrar conversões
            print(f"[CONFIG_SYNC] 🔍 DEBUG - Valores CONVERTIDOS:")
            print(f"[CONFIG_SYNC]   online: {repr(general.get('online'))} → {system_config['online']} (type: {type(system_config['online']).__name__})")
            print(f"[CONFIG_SYNC]   clear_expired_users: {repr(general.get('clear_expired_users'))} → {system_config['clear_expired_users']} (type: {type(system_config['clear_expired_users']).__name__})")
            
            # Configurações de hardware
            hardware_config = {
                'beep_enabled': to_bool(general.get('beep_enabled'), True),
                'ssh_enabled': to_bool(general.get('ssh_enabled'), False),
                'relayN_enabled': to_bool(general.get('relayN_enabled'), False),
                'relayN_timeout': general.get('relayN_timeout', 5),
                'relayN_auto_close': to_bool(general.get('relayN_auto_close'), True),
                'door_sensorN_enabled': to_bool(general.get('door_sensorN_enabled'), False),
                'door_sensorN_idle': general.get('door_sensorN_idle', 10),
                'doorN_interlock': to_bool(general.get('doorN_interlock'), False),
                'bell_enabled': to_bool(general.get('bell_enabled'), False),
                'bell_relay': general.get('bell_relay', 2),
                'exception_mode': general.get('exception_mode', 'none') if general.get('exception_mode', 'none') in ['none', 'emergency', 'lock_down'] else 'none',
                'doorN_exception_mode': to_bool(general.get('doorN_exception_mode'), False)
            }
            
            # Configurações de segurança
            security_config = {
                'password_only': to_bool(general.get('password_only'), False),
                'hide_password_only': to_bool(general.get('hide_password_only'), False),
                'password_only_tip': general.get('password_only_tip', ''),
                'hide_name_on_identification': to_bool(general.get('hide_name_on_identification'), False),
                'denied_transaction_code': general.get('denied_transaction_code', 0),
                'send_code_when_not_identified': to_bool(general.get('send_code_when_not_identified'), False),
                'send_code_when_not_authorized': to_bool(general.get('send_code_when_not_authorized'), False),
                'verbose_logging_enabled': to_bool(identifier.get('verbose_logging'), True),
                'log_type': to_bool(identifier.get('log_type', 0), False),
                'multi_factor_authentication_enabled': to_bool(identifier.get('multi_factor_authentication'), False),
            }
            
            # Configurações de UI
            ui_config = {
                'screen_always_on': to_bool(general.get('screen_always_on'), False)
            }
            
            config_data[device_id] = {
                'device': device,
                'system': system_config,
                'hardware': hardware_config,
                'security': security_config,
                'ui': ui_config,
                # Bloco bruto de monitor (sem persistência por enquanto)
                'monitor': monitor
            }
            
        except Exception as e:
            print(f"[CONFIG_SYNC] Erro ao coletar dados do dispositivo {device.name}: {str(e)}")
            continue
    
    print(f"[CONFIG_SYNC] Coletadas configurações de {len(config_data)} dispositivos")
    return config_data


def persist_config_data(config_data: Dict[int, Dict[str, Any]]) -> Dict[str, int]:
    """
    Persiste dados de configuração no banco de dados Django.
    
    Args:
        config_data: Dados de configuração coletados
        
    Returns:
        Dict com estatísticas de persistência
    """
    from django.db import transaction
    from .models import SystemConfig, HardwareConfig, SecurityConfig, UIConfig
    from src.core.control_id_monitor.infra.control_id_monitor_django_app.models import MonitorConfig
    
    stats = {
        'system_created': 0,
        'system_updated': 0,
        'hardware_created': 0,
        'hardware_updated': 0,
        'security_created': 0,
        'security_updated': 0,
        'ui_created': 0,
        'ui_updated': 0,
        'monitor_created': 0,
        'monitor_updated': 0,
    }
    
    print("[CONFIG_SYNC] Iniciando persistência de configurações")
    
    with transaction.atomic():
        for device_id, configs in config_data.items():
            device = configs['device']
            
            try:
                # Sistema
                print(f"[CONFIG_SYNC] 💾 Persistindo SystemConfig para device {device.name}")
                print(f"[CONFIG_SYNC]   Dados a persistir: online={configs['system']['online']} (type: {type(configs['system']['online']).__name__})")
                
                system_config, created = SystemConfig.objects.update_or_create(
                    device=device,
                    defaults=configs['system']
                )
                
                # Verificar valor salvo no banco
                system_config.refresh_from_db()
                print(f"[CONFIG_SYNC]   Valor SALVO no banco: online={system_config.online} (type: {type(system_config.online).__name__})")
                
                if created:
                    stats['system_created'] += 1
                    print(f"[CONFIG_SYNC]   ✅ SystemConfig CRIADO")
                else:
                    stats['system_updated'] += 1
                    print(f"[CONFIG_SYNC]   ✅ SystemConfig ATUALIZADO")
                
                # Hardware
                hardware_config, created = HardwareConfig.objects.update_or_create(
                    device=device,
                    defaults=configs['hardware']
                )
                if created:
                    stats['hardware_created'] += 1
                else:
                    stats['hardware_updated'] += 1
                
                # Segurança
                security_config, created = SecurityConfig.objects.update_or_create(
                    device=device,
                    defaults=configs['security']
                )
                if created:
                    stats['security_created'] += 1
                else:
                    stats['security_updated'] += 1
                
                # UI
                ui_config, created = UIConfig.objects.update_or_create(
                    device=device,
                    defaults=configs['ui']
                )
                if created:
                    stats['ui_created'] += 1
                else:
                    stats['ui_updated'] += 1

                # Monitor (persistimos campos fortes)
                monitor_payload = configs.get('monitor') or {}
                monitor_defaults = {
                    'request_timeout': monitor_payload.get('request_timeout', 1000),
                    'hostname': monitor_payload.get('hostname', ''),
                    'port': str(monitor_payload.get('port', '')) if monitor_payload.get('port') is not None else '',
                    'path': monitor_payload.get('path', 'api/notifications'),
                    'inform_access_event_id': monitor_payload.get('inform_access_event_id', 0),
                    'alive_interval': monitor_payload.get('alive_interval', 30000),
                }
                monitor_config, created = MonitorConfig.objects.update_or_create(
                    device=device,
                    defaults=monitor_defaults
                )
                if created:
                    stats['monitor_created'] += 1
                else:
                    stats['monitor_updated'] += 1
                    
            except Exception as e:
                print(f"[CONFIG_SYNC] Erro ao persistir configurações do dispositivo {device.name}: {str(e)}")
                continue
    
    print(f"""[CONFIG_SYNC] Persistência concluída:
    Sistema: {stats['system_created']} criadas, {stats['system_updated']} atualizadas
    Hardware: {stats['hardware_created']} criadas, {stats['hardware_updated']} atualizadas
    Segurança: {stats['security_created']} criadas, {stats['security_updated']} atualizadas
    UI: {stats['ui_created']} criadas, {stats['ui_updated']} atualizadas
    Monitor: {stats['monitor_created']} criadas, {stats['monitor_updated']} atualizadas
""")
    
    return stats


def sync_all_configs() -> Dict[str, Any]:
    """
    Executa sincronização completa de configurações.
    
    Returns:
        Dict com resultado da sincronização
    """
    devices = list(Device.objects.filter(is_active=True))
    
    if not devices:
        return {"success": False, "error": "Nenhuma catraca ativa encontrada"}
    
    try:
        # Coleta dados
        config_data = collect_config_data(devices)
        
        if not config_data:
            return {"success": False, "error": "Nenhuma configuração coletada"}
        
        # Persiste dados
        stats = persist_config_data(config_data)
        
        return {
            "success": True,
            "message": "Sincronização de configurações concluída com sucesso",
            "stats": {
                "devices": len(devices),
                "configs_processed": len(config_data),
                **stats
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Erro durante sincronização de configurações: {str(e)}"
        }
