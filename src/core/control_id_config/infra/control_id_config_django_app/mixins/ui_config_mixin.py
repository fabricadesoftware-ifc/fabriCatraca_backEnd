from src.core.__seedwork__.infra import ControlIDSyncMixin
from rest_framework.response import Response
from rest_framework import status


class UIConfigSyncMixin(ControlIDSyncMixin):
    """Mixin para sincronização de configurações de interface"""
    
    def update_ui_config_in_catraca(self, instance):
        """Atualiza configurações de interface na catraca"""
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            def bool_to_str(value):
                return "1" if value else "0"
            
            payload = {
                "general": {
                    "screen_always_on": bool_to_str(instance.screen_always_on),
                }
            }
            
            logger.info(f"[UI_CONFIG] Enviando para catraca: {payload}")
            
            # Usa o helper com retry automático de sessão
            response = self._make_request("set_configuration.fcgi", json_data=payload)
            
            logger.info(f"[UI_CONFIG] Resposta - Status: {response.status_code}, Body: {response.text}")
            
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
            logging.getLogger(__name__).exception("[UI_CONFIG] Exceção ao atualizar:")
            return Response({
                "success": False,
                "error": f"Exceção ao atualizar configuração: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def sync_ui_config_from_catraca(self):
        """Sincroniza configurações de interface da catraca"""
        try:
            from ..models import UIConfig
            
            # Buscar parâmetro screen_always_on da seção 'general'
            payload = {"general": ["screen_always_on"]}
            
            # Usa o helper com retry automático de sessão
            response = self._make_request("get_configuration.fcgi", json_data=payload)
            
            if response.status_code == 200:
                config_data = response.json().get('general', {})
            else:
                return Response({
                    "success": False,
                    "message": f"Erro ao obter configurações: {response.status_code}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Extrair valor de screen_always_on (pode vir como int 0/1)
            screen_always_on_value = config_data.get('screen_always_on', 0)
            # Converter para boolean (aceita int ou bool)
            screen_always_on = bool(int(screen_always_on_value)) if isinstance(screen_always_on_value, (int, str)) else bool(screen_always_on_value)
            
            # Criar ou atualizar configuração com valor real da catraca
            config, created = UIConfig.objects.update_or_create(
                device=self.device,
                defaults={
                    'screen_always_on': screen_always_on
                }
            )
            
            return Response({
                "success": True,
                "message": f"Configuração de interface {'criada' if created else 'atualizada'} com sucesso",
                "config_id": config.id,
                "screen_always_on": screen_always_on
            })
                
        except Exception as e:
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


