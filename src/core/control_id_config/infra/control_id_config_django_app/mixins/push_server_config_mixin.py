from src.core.__seedwork__.infra import ControlIDSyncMixin
from rest_framework.response import Response
from rest_framework import status


class PushServerConfigSyncMixin(ControlIDSyncMixin):
    """Mixin para sincronização de configurações do servidor Push"""
    
    def update_push_server_config_in_catraca(self, instance):
        """Atualiza configurações do servidor Push no dispositivo"""
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            payload = {
                "push_server": {
                    "push_request_timeout": str(instance.push_request_timeout),
                    "push_request_period": str(instance.push_request_period),
                    "push_remote_address": instance.push_remote_address or ""
                }
            }
            
            logger.info(f"[PUSH_SERVER_CONFIG] Enviando para catraca: {payload}")
            
            # Usa o helper com retry automático de sessão
            response = self._make_request("set_configuration.fcgi", json_data=payload)
            
            logger.info(f"[PUSH_SERVER_CONFIG] Resposta - Status: {response.status_code}, Body: {response.text}")
            
            if response.status_code == 200:
                return Response(response.json(), status=status.HTTP_200_OK)
            else:
                return Response({
                    "success": False,
                    "error": f"Erro ao atualizar configuração: {response.status_code}",
                    "details": response.text
                }, status=response.status_code)
                
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception("[PUSH_SERVER_CONFIG] Exceção ao atualizar:")
            return Response({
                "success": False,
                "error": f"Exceção ao atualizar configuração: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def sync_push_server_config_from_catraca(self):
        """Sincroniza configurações do servidor Push do dispositivo IDBLOCK"""
        try:
            from ..models import PushServerConfig
            import logging
            logger = logging.getLogger(__name__)
            
            # Payload CORRETO para IDBLOCK - seção 'push_server'
            payload = {
                "push_server": [
                    "push_request_timeout",
                    "push_request_period",
                    "push_remote_address"
                ]
            }
            
            logger.info(f"[PUSH_SERVER_CONFIG_SYNC] Solicitando config da IDBLOCK: {payload}")
            
            # Usa o helper com retry automático de sessão
            response = self._make_request("get_configuration.fcgi", json_data=payload)
            
            if response.status_code == 200:
                full_response = response.json()
                config_data = full_response.get('push_server', {}) if isinstance(full_response, dict) else {}
                logger.info(f"[PUSH_SERVER_CONFIG_SYNC] Resposta da catraca: {config_data}")
            else:
                logger.error(f"[PUSH_SERVER_CONFIG_SYNC] Erro {response.status_code}: {response.text}")
                return Response({
                    "success": False,
                    "message": f"Erro ao obter configurações: {response.status_code}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            if not config_data:
                logger.warning("[PUSH_SERVER_CONFIG_SYNC] API retornou dados vazios - usando defaults")
            
            # Atualiza ou cria configuração local com dados reais da catraca
            config, created = PushServerConfig.objects.update_or_create(
                device=self.device,
                defaults={
                    'push_request_timeout': int(config_data.get('push_request_timeout', 15000) or 15000),
                    'push_request_period': int(config_data.get('push_request_period', 60) or 60),
                    'push_remote_address': config_data.get('push_remote_address', '')
                }
            )
            
            logger.info(f"[PUSH_SERVER_CONFIG_SYNC] Config {'criada' if created else 'atualizada'}: "
                       f"timeout={config.push_request_timeout}ms, period={config.push_request_period}s, "
                       f"address={config.push_remote_address or '(vazio)'}")
            
            return Response({
                "success": True,
                "message": f"Configuração Push Server {'criada' if created else 'atualizada'} com sucesso",
                "config_id": config.id
            })
                
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception("[PUSH_SERVER_CONFIG_SYNC] Exceção:")
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
