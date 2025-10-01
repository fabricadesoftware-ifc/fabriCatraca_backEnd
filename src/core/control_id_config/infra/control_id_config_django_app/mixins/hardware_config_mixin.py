from src.core.__seedwork__.infra import ControlIDSyncMixin
from rest_framework.response import Response
from rest_framework import status


class HardwareConfigSyncMixin(ControlIDSyncMixin):
    """Mixin para sincronização de configurações de hardware"""
    
    def update_hardware_config_in_catraca(self, instance):
        """Atualiza configurações de hardware na catraca"""
        try:
            # Converte valores para formato esperado pela API
            def bool_to_str(value):
                return "1" if value else "0"
            
            def exception_mode_to_str(value):
                return "emergency" if value else "none"
            
            payload = {
                "general": {
                    "beep_enabled": bool_to_str(instance.beep_enabled),
                    "ssh_enabled": bool_to_str(instance.ssh_enabled),
                    "bell_enabled": bool_to_str(instance.bell_enabled),
                    "bell_relay": str(instance.bell_relay),
                    "exception_mode": exception_mode_to_str(instance.exception_mode),
                }
            }
            
            # Usa o helper com retry automático de sessão
            response = self._make_request("set_configuration.fcgi", json_data=payload)
            
            if response.status_code == 200:
                return Response(response.json(), status=status.HTTP_200_OK)
            else:
                return Response({
                    "success": False,
                    "error": f"Erro ao atualizar configuração: {response.status_code}",
                    "details": response.text
                }, status=response.status_code)
                
        except Exception as e:
            return Response({
                "success": False,
                "error": f"Exceção ao atualizar configuração: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def sync_hardware_config_from_catraca(self):
        """Sincroniza configurações de hardware da catraca IDBLOCK"""
        try:
            from ..models import HardwareConfig
            import logging
            logger = logging.getLogger(__name__)
            
            # Payload CORRETO para IDBLOCK
            # general: beep_enabled, bell_enabled, bell_relay, exception_mode
            # alarm: siren_enabled, siren_relay
            payload = {
                "general": ["beep_enabled", "bell_enabled", "bell_relay", "exception_mode"],
                "alarm": ["siren_enabled", "siren_relay"]
            }
            
            logger.info(f"[HARDWARE_CONFIG_SYNC] Solicitando config da IDBLOCK: {payload}")
            
            # Usa o helper com retry automático de sessão
            response = self._make_request("get_configuration.fcgi", json_data=payload)
            
            if response.status_code == 200:
                try:
                    full_response = response.json()
                    general_data = full_response.get('general', {}) if isinstance(full_response, dict) else {}
                    alarm_data = full_response.get('alarm', {}) if isinstance(full_response, dict) else {}
                    logger.info(f"[HARDWARE_CONFIG_SYNC] general: {general_data}, alarm: {alarm_data}")
                except Exception as json_error:
                    logger.error(f"[HARDWARE_CONFIG_SYNC] Erro JSON: {json_error}")
                    return Response({
                        "success": False,
                        "message": f"Erro ao fazer parse da resposta JSON: {json_error}"
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                # Combina dados de diferentes seções
                config_data = {**general_data, **alarm_data}
            else:
                logger.error(f"[HARDWARE_CONFIG_SYNC] Erro {response.status_code}: {response.text}")
                return Response({
                    "success": False,
                    "message": f"Erro ao obter configurações: {response.status_code}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            if not config_data:
                logger.warning("[HARDWARE_CONFIG_SYNC] API retornou dados vazios - usando defaults")

            def to_bool(v, default=False):
                """Converte string '0'/'1' para bool."""
                if v is None:
                    return bool(default)
                if isinstance(v, bool):
                    return v
                if isinstance(v, str):
                    # Para IDBLOCK: "0" = False, "1" = True
                    return v.strip() in ("1", "true", "True")
                if isinstance(v, (int, float)):
                    return v != 0
                return bool(v)
            
            # exception_mode: "none" = desabilitado, "emergency"/"lock_down" = habilitado
            exception_mode_value = config_data.get('exception_mode', 'none')
            exception_mode_enabled = exception_mode_value not in ['', 'none', '0', 0, False]
            
            config, created = HardwareConfig.objects.update_or_create(
                device=self.device,
                defaults={
                    # Campos DISPONÍVEIS na IDBLOCK
                    'beep_enabled': to_bool(config_data.get('beep_enabled'), True),
                    'bell_enabled': to_bool(config_data.get('bell_enabled'), False),
                    'bell_relay': int(config_data.get('bell_relay', 1) or 1),
                    'exception_mode': exception_mode_enabled,
                    # Campos NÃO DISPONÍVEIS na IDBLOCK (valores fixos padrão)
                    'ssh_enabled': False,           # Não existe na IDBLOCK
                    'relayN_enabled': False,        # Não existe na IDBLOCK
                    'relayN_timeout': 5,            # Não existe na IDBLOCK
                    'relayN_auto_close': True,      # Não existe na IDBLOCK
                    'door_sensorN_enabled': False,  # Não existe na IDBLOCK
                    'door_sensorN_idle': 10,        # Não existe na IDBLOCK
                    'doorN_interlock': False,       # Não existe na IDBLOCK
                    'doorN_exception_mode': False   # Não existe na IDBLOCK
                }
            )
            
            logger.info(f"[HARDWARE_CONFIG_SYNC] Config {'criada' if created else 'atualizada'}: "
                       f"beep={config.beep_enabled}, bell={config.bell_enabled}, exception_mode={config.exception_mode}")
            
            return Response({
                "success": True,
                "message": f"Configuração de hardware {'criada' if created else 'atualizada'} com sucesso",
                "config_id": config.id
            })
                
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception("[HARDWARE_CONFIG_SYNC] Exceção:")
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


