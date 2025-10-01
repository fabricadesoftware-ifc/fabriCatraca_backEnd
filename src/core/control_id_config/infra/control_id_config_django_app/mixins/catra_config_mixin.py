from src.core.__seedwork__.infra import ControlIDSyncMixin
from rest_framework.response import Response
from rest_framework import status


class CatraConfigSyncMixin(ControlIDSyncMixin):
    """Mixin para sincronização de configurações da catraca (seção 'catra')"""
    
    def update_catra_config_in_catraca(self, instance):
        """Atualiza configurações da catraca no dispositivo"""
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            def bool_to_str(value):
                return "1" if value else "0"
            
            payload = {
                "catra": {
                    "anti_passback": bool_to_str(instance.anti_passback),
                    "daily_reset": bool_to_str(instance.daily_reset),
                    "gateway": instance.gateway,
                    "operation_mode": instance.operation_mode
                }
            }
            
            logger.info(f"[CATRA_CONFIG] Enviando para catraca: {payload}")
            
            # Usa o helper com retry automático de sessão
            response = self._make_request("set_configuration.fcgi", json_data=payload)
            
            logger.info(f"[CATRA_CONFIG] Resposta - Status: {response.status_code}, Body: {response.text}")
            
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
            logging.getLogger(__name__).exception("[CATRA_CONFIG] Exceção ao atualizar:")
            return Response({
                "success": False,
                "error": f"Exceção ao atualizar configuração: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def sync_catra_config_from_catraca(self):
        """Sincroniza configurações da catraca do dispositivo IDBLOCK"""
        try:
            from ..models import CatraConfig
            import logging
            logger = logging.getLogger(__name__)
            
            # Payload CORRETO para IDBLOCK - seção 'catra'
            payload = {
                "catra": [
                    "anti_passback",
                    "daily_reset",
                    "gateway",
                    "operation_mode"
                ]
            }
            
            logger.info(f"[CATRA_CONFIG_SYNC] Solicitando config da IDBLOCK: {payload}")
            
            # Usa o helper com retry automático de sessão
            response = self._make_request("get_configuration.fcgi", json_data=payload)
            
            if response.status_code == 200:
                full_response = response.json()
                config_data = full_response.get('catra', {}) if isinstance(full_response, dict) else {}
                logger.info(f"[CATRA_CONFIG_SYNC] Resposta da catraca: {config_data}")
            else:
                logger.error(f"[CATRA_CONFIG_SYNC] Erro {response.status_code}: {response.text}")
                return Response({
                    "success": False,
                    "message": f"Erro ao obter configurações: {response.status_code}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            if not config_data:
                logger.warning("[CATRA_CONFIG_SYNC] API retornou dados vazios - usando defaults")

            def to_bool(v, default=False):
                """Converte string '0'/'1' para bool."""
                if v is None:
                    return bool(default)
                if isinstance(v, bool):
                    return v
                if isinstance(v, str):
                    return v.strip() in ("1", "true", "True")
                if isinstance(v, (int, float)):
                    return v != 0
                return bool(v)
            
            # Atualiza ou cria configuração local com dados reais da catraca
            config, created = CatraConfig.objects.update_or_create(
                device=self.device,
                defaults={
                    'anti_passback': to_bool(config_data.get('anti_passback'), False),
                    'daily_reset': to_bool(config_data.get('daily_reset'), False),
                    'gateway': config_data.get('gateway', 'clockwise'),
                    'operation_mode': config_data.get('operation_mode', 'blocked')
                }
            )
            
            logger.info(f"[CATRA_CONFIG_SYNC] Config {'criada' if created else 'atualizada'}: "
                       f"anti_passback={config.anti_passback}, gateway={config.gateway}, mode={config.operation_mode}")
            
            return Response({
                "success": True,
                "message": f"Configuração da catraca {'criada' if created else 'atualizada'} com sucesso",
                "config_id": config.id
            })
                
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception("[CATRA_CONFIG_SYNC] Exceção:")
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
