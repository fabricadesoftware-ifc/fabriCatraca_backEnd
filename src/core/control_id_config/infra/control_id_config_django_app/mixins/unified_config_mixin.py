from src.core.__seedwork__.infra import ControlIDSyncMixin
from rest_framework.response import Response
from rest_framework import status


def to_bool(value, default=False):
    """
    Converte valores string da API do Control iD para boolean.
    API retorna "0" para False e "1" para True.
    """
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        # Retorna True APENAS se string for "1", "true" ou "True"
        return value.strip() in ("1", "true", "True")
    # Para números: 0 = False, qualquer outro = True
    if isinstance(value, (int, float)):
        return value != 0
    return bool(value)


class UnifiedConfigSyncMixin(ControlIDSyncMixin):
    """Mixin unificado para sincronização de todas as configurações"""
    
    # Métodos de configuração do sistema
    def update_system_config_in_catraca(self, instance):
        """Atualiza configurações do sistema na catraca"""
        response = self.update_objects(
            "general",
            {
                "auto_reboot_hour": instance.auto_reboot_hour,
                "auto_reboot_minute": instance.auto_reboot_minute,
                "clear_expired_users": instance.clear_expired_users,
                "url_reboot_enabled": instance.url_reboot_enabled,
                "keep_user_image": instance.keep_user_image,
                "catra_timeout": instance.catra_timeout,
                "online": instance.online,
                "local_identification": instance.local_identification,
                "language": instance.language,
                "daylight_savings_time_start": instance.daylight_savings_time_start,
                "daylight_savings_time_end": instance.daylight_savings_time_end,
                "web_server_enabled": instance.web_server_enabled
            }
        )
        return response
    
    def sync_system_config_from_catraca(self):
        """Sincroniza configurações do sistema da catraca"""
        try:
            from ..models import SystemConfig
            import requests
            
            # Usa get_configuration.fcgi em vez de load_objects
            sess = self.login()
            response = requests.post(
                self.get_url(f"get_configuration.fcgi?session={sess}"),
                json={"monitor": {}}
            )
            
            if response.status_code == 200:
                config_data = response.json().get('general', {})
            else:
                return Response({
                    "success": False,
                    "message": f"Erro ao obter configurações: {response.status_code}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            if config_data:
                
                # Atualiza ou cria configuração local
                config, created = SystemConfig.objects.update_or_create(
                    device=self.device,
                    defaults={
                        'auto_reboot_hour': config_data.get('auto_reboot_hour', 3),
                        'auto_reboot_minute': config_data.get('auto_reboot_minute', 0),
                        'clear_expired_users': to_bool(config_data.get('clear_expired_users'), False),
                        'url_reboot_enabled': to_bool(config_data.get('url_reboot_enabled'), True),
                        'keep_user_image': to_bool(config_data.get('keep_user_image'), True),
                        'catra_timeout': config_data.get('catra_timeout', 30),
                        'online': to_bool(config_data.get('online'), True),
                        'local_identification': to_bool(config_data.get('local_identification'), True),
                        'language': config_data.get('language', 'pt'),
                        'daylight_savings_time_start': config_data.get('daylight_savings_time_start'),
                        'daylight_savings_time_end': config_data.get('daylight_savings_time_end'),
                        'web_server_enabled': to_bool(config_data.get('web_server_enabled'), True)
                    }
                )
                
                return Response({
                    "success": True,
                    "message": f"Configuração do sistema {'criada' if created else 'atualizada'} com sucesso",
                    "config_id": config.id
                })
            else:
                return Response({
                    "success": False,
                    "message": "Nenhuma configuração encontrada na catraca"
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Métodos de configuração de hardware
    def update_hardware_config_in_catraca(self, instance):
        """Atualiza configurações de hardware na catraca"""
        response = self.update_objects(
            "general",
            {
                "beep_enabled": instance.beep_enabled,
                "ssh_enabled": instance.ssh_enabled,
                "relayN_enabled": instance.relayN_enabled,
                "relayN_timeout": instance.relayN_timeout,
                "relayN_auto_close": instance.relayN_auto_close,
                "door_sensorN_enabled": instance.door_sensorN_enabled,
                "door_sensorN_idle": instance.door_sensorN_idle,
                "doorN_interlock": instance.doorN_interlock,
                "bell_enabled": instance.bell_enabled,
                "bell_relay": instance.bell_relay,
                "exception_mode": instance.exception_mode,
                "doorN_exception_mode": instance.doorN_exception_mode
            }
        )
        return response
    
    def sync_hardware_config_from_catraca(self):
        """Sincroniza configurações de hardware da catraca"""
        try:
            from ..models import HardwareConfig
            import requests
            
            # Usa get_configuration.fcgi em vez de load_objects
            sess = self.login()
            response = requests.post(
                self.get_url(f"get_configuration.fcgi?session={sess}"),
                json={}
            )
            
            if response.status_code == 200:
                config_data = response.json().get('general', {})
            else:
                return Response({
                    "success": False,
                    "message": f"Erro ao obter configurações: {response.status_code}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            if config_data:
                
                config, created = HardwareConfig.objects.update_or_create(
                    device=self.device,
                    defaults={
                        'beep_enabled': to_bool(config_data.get('beep_enabled'), True),
                        'ssh_enabled': to_bool(config_data.get('ssh_enabled'), False),
                        'relayN_enabled': to_bool(config_data.get('relayN_enabled'), False),
                        'relayN_timeout': config_data.get('relayN_timeout', 5),
                        'relayN_auto_close': to_bool(config_data.get('relayN_auto_close'), True),
                        'door_sensorN_enabled': to_bool(config_data.get('door_sensorN_enabled'), False),
                        'door_sensorN_idle': config_data.get('door_sensorN_idle', 10),
                        'doorN_interlock': to_bool(config_data.get('doorN_interlock'), False),
                        'bell_enabled': to_bool(config_data.get('bell_enabled'), False),
                        'bell_relay': config_data.get('bell_relay', 1),
                        'exception_mode': to_bool(config_data.get('exception_mode'), False),
                        'doorN_exception_mode': to_bool(config_data.get('doorN_exception_mode'), False)
                    }
                )
                
                return Response({
                    "success": True,
                    "message": f"Configuração de hardware {'criada' if created else 'atualizada'} com sucesso",
                    "config_id": config.id
                })
            else:
                return Response({
                    "success": False,
                    "message": "Nenhuma configuração encontrada na catraca"
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Métodos de configuração de segurança
    def update_security_config_in_catraca(self, instance):
        """Atualiza configurações de segurança na catraca"""
        response = self.update_objects(
            "general",
            {
                "password_only": instance.password_only,
                "hide_password_only": instance.hide_password_only,
                "password_only_tip": instance.password_only_tip,
                "hide_name_on_identification": instance.hide_name_on_identification,
                "denied_transaction_code": instance.denied_transaction_code,
                "send_code_when_not_identified": instance.send_code_when_not_identified,
                "send_code_when_not_authorized": instance.send_code_when_not_authorized
            }
        )
        return response
    
    def sync_security_config_from_catraca(self):
        """Sincroniza configurações de segurança da catraca"""
        try:
            from ..models import SecurityConfig
            import requests
            
            # Usa get_configuration.fcgi em vez de load_objects
            sess = self.login()
            response = requests.post(
                self.get_url(f"get_configuration.fcgi?session={sess}"),
                json={}
            )
            
            if response.status_code == 200:
                config_data = response.json().get('general', {})
            else:
                return Response({
                    "success": False,
                    "message": f"Erro ao obter configurações: {response.status_code}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            if config_data:
                
                config, created = SecurityConfig.objects.update_or_create(
                    device=self.device,
                    defaults={
                        'password_only': to_bool(config_data.get('password_only'), False),
                        'hide_password_only': to_bool(config_data.get('hide_password_only'), False),
                        'password_only_tip': config_data.get('password_only_tip', ''),
                        'hide_name_on_identification': to_bool(config_data.get('hide_name_on_identification'), False),
                        'denied_transaction_code': config_data.get('denied_transaction_code', ''),
                        'send_code_when_not_identified': to_bool(config_data.get('send_code_when_not_identified'), False),
                        'send_code_when_not_authorized': to_bool(config_data.get('send_code_when_not_authorized'), False)
                    }
                )
                
                return Response({
                    "success": True,
                    "message": f"Configuração de segurança {'criada' if created else 'atualizada'} com sucesso",
                    "config_id": config.id
                })
            else:
                return Response({
                    "success": False,
                    "message": "Nenhuma configuração encontrada na catraca"
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Métodos de configuração de UI
    def update_ui_config_in_catraca(self, instance):
        """Atualiza configurações de interface na catraca"""
        response = self.update_objects(
            "general",
            {
                "screen_always_on": instance.screen_always_on
            }
        )
        return response
    
    def sync_ui_config_from_catraca(self):
        """Sincroniza configurações de interface da catraca"""
        try:
            from ..models import UIConfig
            import requests
            
            # Usa get_configuration.fcgi em vez de load_objects
            sess = self.login()
            response = requests.post(
                self.get_url(f"get_configuration.fcgi?session={sess}"),
                json={}
            )
            
            if response.status_code == 200:
                config_data = response.json().get('general', {})
            else:
                return Response({
                    "success": False,
                    "message": f"Erro ao obter configurações: {response.status_code}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            if config_data:
                
                config, created = UIConfig.objects.update_or_create(
                    device=self.device,
                    defaults={
                        'screen_always_on': to_bool(config_data.get('screen_always_on'), False)
                    }
                )
                
                return Response({
                    "success": True,
                    "message": f"Configuração de interface {'criada' if created else 'atualizada'} com sucesso",
                    "config_id": config.id
                })
            else:
                return Response({
                    "success": False,
                    "message": "Nenhuma configuração encontrada na catraca"
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    # ==========================
    # Monitor configuration
    # ==========================
    def sync_monitor_config_from_catraca(self):
        """Obtém configurações de monitor via get_configuration.fcgi (sem persistência em DB)."""
        try:
            # Estratégia multi-payload conforme documentação
            payloads = [
                # 1) Bloco direto
                {"monitor": {}},
                # 2) Bloco direto com fields explícitos
                {"monitor": {"fields": [
                    "request_timeout", "hostname", "port", "path",
                    "inform_access_event_id", "alive_interval"
                ]}},
                # 3) Via config.modules (name/fields)
                {"config": {"modules": [{
                    "name": "monitor",
                    "fields": [
                        "request_timeout", "hostname", "port", "path",
                        "inform_access_event_id", "alive_interval"
                    ]
                }]}},
                # 4) Sem filtro (devolve tudo)
                {},
            ]

            last_raw = None
            last_meta = {}
            for body in payloads:
                # Usa _make_request que tem retry automático em caso de sessão expirada
                resp = self._make_request("get_configuration.fcgi", method="POST", json_data=body)
                if resp.status_code != 200:
                    # Armazena erro para debug
                    last_raw = {"error": f"Status {resp.status_code}", "payload": body}
                    continue
                raw = resp.json() or {}
                last_raw = raw

                # Caminho 1: plano
                monitor = raw.get("monitor", {}) if isinstance(raw, dict) else {}
                if isinstance(monitor, dict) and monitor:
                    return Response({"success": True, "monitor": monitor})

                # Caminho 2: hierárquico
                if isinstance(raw.get("config"), dict):
                    modules = raw["config"].get("modules") or raw["config"].get("module")
                    if isinstance(modules, list):
                        parsed = {}
                        for mod in modules:
                            name = mod.get("name") or mod.get("module")
                            if name == "monitor":
                                # Algumas respostas vêm em param[name,value], outras em fields dict
                                params = mod.get("param") or []
                                if isinstance(params, list):
                                    for p in params:
                                        k = p.get("name")
                                        v = p.get("value")
                                        if k is not None:
                                            parsed[k] = v
                                fields_block = mod.get("fields") or mod.get("values") or {}
                                if isinstance(fields_block, dict):
                                    parsed.update(fields_block)
                        if parsed:
                            return Response({"success": True, "monitor": parsed})

                last_meta = {"top_level_keys": list(raw.keys())}
                if isinstance(raw.get("config"), dict):
                    mods = raw["config"].get("modules") or raw["config"].get("module")
                    if isinstance(mods, list):
                        last_meta["module_names"] = [m.get("name") or m.get("module") for m in mods]

            return Response({
                "success": True,
                "monitor": {},
                "_debug": last_meta,
                "_raw": last_raw,
            })
        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update_monitor_config_in_catraca(self, values: dict) -> Response:
        """Atualiza configurações de monitor via set_configuration.fcgi."""
        try:
            # 1) Descobre quais chaves existem no device para o bloco monitor
            probe = self._make_request("get_configuration.fcgi", method="POST", json_data={"monitor": {}})
            
            # Se a catraca não suporta o bloco monitor, retorna erro mais claro
            if probe.status_code == 400:
                return Response({
                    "success": False,
                    "error": "Dispositivo não suporta configurações de monitor (API retornou 400)",
                    "detail": "O módulo 'monitor' não está disponível neste dispositivo"
                }, status=status.HTTP_404_NOT_FOUND)
            
            probe.raise_for_status()
            current_monitor = (probe.json() or {}).get("monitor", {})
            if not isinstance(current_monitor, dict) or not current_monitor:
                return Response({
                    "success": False,
                    "error": "Dispositivo não retornou bloco 'monitor' no get_configuration",
                }, status=status.HTTP_404_NOT_FOUND)
            allowed_keys = set(current_monitor.keys())

            # 2) Se cliente mandou subset (como Postman), só normalize para string
            filtered = {k: ("" if v is None else str(v)) for k, v in (values or {}).items()}

            if not filtered:
                return Response({
                    "success": False,
                    "error": "Nenhum parâmetro informado para atualizar",
                }, status=status.HTTP_400_BAD_REQUEST)

            response = self._make_request("set_configuration.fcgi", method="POST", json_data={"monitor": filtered})
            if response.status_code != 200:
                return Response({
                    "success": False,
                    "error": response.text or "Erro ao salvar configurações de monitor"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response({"success": True})
        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def sync_monitor_into_model(self):
        """Carrega monitor da catraca e persiste em MonitorConfig (campos fortes)."""
        try:
            from ..models import MonitorConfig
            res = self.sync_monitor_config_from_catraca()
            if getattr(res, 'status_code', 200) != 200:
                return res
            data = getattr(res, 'data', {}) or {}
            monitor = data.get('monitor') or {}
            # Não persiste se veio vazio, para não apagar valores existentes
            if not isinstance(monitor, dict) or not monitor:
                return Response({
                    'success': False,
                    'error': "Bloco 'monitor' veio vazio do dispositivo; nada foi alterado",
                }, status=status.HTTP_204_NO_CONTENT)
            defaults = {
                'request_timeout': monitor.get('request_timeout', 1000),
                'hostname': monitor.get('hostname', ''),
                'port': str(monitor.get('port', '')) if monitor.get('port') is not None else '',
                'path': monitor.get('path', 'api/notifications'),
                'inform_access_event_id': monitor.get('inform_access_event_id', 0),
                'alive_interval': monitor.get('alive_interval', 30000),
            }
            obj, created = MonitorConfig.objects.update_or_create(
                device=self.device,
                defaults=defaults
            )
            return Response({
                'success': True,
                'created': created,
                'monitor_config_id': obj.id,
            })
        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)