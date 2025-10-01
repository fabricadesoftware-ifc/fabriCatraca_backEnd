from src.core.__seedwork__.infra import ControlIDSyncMixin
from rest_framework.response import Response
from rest_framework import status


class SystemConfigSyncMixin(ControlIDSyncMixin):
    """Mixin para sincronização de configurações do sistema"""
    
    def update_system_config_in_catraca(self, instance):
        """Atualiza configurações do sistema na catraca"""
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            def bool_to_str(value):
                return "1" if value else "0"
            
            payload = {
                "general": {
                    "catra_timeout": str(instance.catra_timeout or 30000),
                    "online": bool_to_str(instance.online),
                    "local_identification": bool_to_str(instance.local_identification),
                    "language": str(instance.language or "pt_BR")
                }
            }
            
            logger.info(f"[SYSTEM_CONFIG] Enviando para catraca: {payload}")
            
            # Usa o helper com retry automático de sessão
            response = self._make_request("set_configuration.fcgi", json_data=payload)
            
            logger.info(f"[SYSTEM_CONFIG] Resposta da catraca - Status: {response.status_code}, Body: {response.text}")
            
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
    
    def sync_system_config_from_catraca(self):
        """Sincroniza configurações do sistema da catraca IDBLOCK"""
        try:
            from ..models import SystemConfig
            import logging
            logger = logging.getLogger(__name__)
            
            # Payload CORRETO para IDBLOCK - apenas campos disponíveis em 'general'
            payload = {
                "general": [
                    "online",
                    "auto_reboot",
                    "catra_timeout",
                    "local_identification",
                    "exception_mode",
                    "language",
                    "daylight_savings_time_start",
                    "daylight_savings_time_end"
                ]
            }
            
            logger.info(f"[SYSTEM_CONFIG_SYNC] Solicitando config da IDBLOCK: {payload}")
            
            # Usa o helper com retry automático de sessão
            response = self._make_request("get_configuration.fcgi", json_data=payload)
            
            if response.status_code == 200:
                full_response = response.json()
                config_data = full_response.get('general', {}) if isinstance(full_response, dict) else {}
                logger.info(f"[SYSTEM_CONFIG_SYNC] Resposta da catraca: {config_data}")
            else:
                logger.error(f"[SYSTEM_CONFIG_SYNC] Erro {response.status_code}: {response.text}")
                return Response({
                    "success": False,
                    "message": f"Erro ao obter configurações: {response.status_code}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            if not config_data:
                logger.warning("[SYSTEM_CONFIG_SYNC] API retornou dados vazios - usando defaults")
            
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
            
            # Atualiza ou cria configuração local com dados reais da catraca
            config, created = SystemConfig.objects.update_or_create(
                device=self.device,
                defaults={
                    # Campos DISPONÍVEIS na IDBLOCK
                    'online': to_bool(config_data.get('online'), True),
                    'catra_timeout': int(str(config_data.get('catra_timeout', 30)) or 30),
                    'local_identification': to_bool(config_data.get('local_identification'), True),
                    'language': config_data.get('language', 'pt').replace('_BR', ''),
                    'daylight_savings_time_start': config_data.get('daylight_savings_time_start') or None,
                    'daylight_savings_time_end': config_data.get('daylight_savings_time_end') or None,
                    # Campos NÃO DISPONÍVEIS na IDBLOCK (valores fixos padrão)
                    'auto_reboot_hour': 3,          # Não existe na IDBLOCK
                    'auto_reboot_minute': 0,        # Não existe na IDBLOCK
                    'clear_expired_users': False,   # Não existe na IDBLOCK
                    'url_reboot_enabled': True,     # Não existe na IDBLOCK
                    'keep_user_image': True,        # Não existe na IDBLOCK
                    'web_server_enabled': True      # Não existe na IDBLOCK
                }
            )
            
            logger.info(f"[SYSTEM_CONFIG_SYNC] Config {'criada' if created else 'atualizada'}: "
                       f"online={config.online}, catra_timeout={config.catra_timeout}")
            
            return Response({
                "success": True,
                "message": f"Configuração do sistema {'criada' if created else 'atualizada'} com sucesso",
                "config_id": config.id
            })
                
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception("[SYSTEM_CONFIG_SYNC] Exceção:")
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

