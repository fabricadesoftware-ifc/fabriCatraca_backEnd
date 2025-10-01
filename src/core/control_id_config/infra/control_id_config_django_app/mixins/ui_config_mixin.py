from src.core.__seedwork__.infra import ControlIDSyncMixin
from rest_framework.response import Response
from rest_framework import status


class UIConfigSyncMixin(ControlIDSyncMixin):
    """Mixin para sincronização de configurações de interface"""
    
    def update_ui_config_in_catraca(self, instance):
        """Atualiza configurações de interface na catraca"""
        
        def bool_to_string(value):
            return "1" if value else "0"
        
        # UI Config: parâmetros específicos podem não existir na API Control iD
        # Por enquanto, não enviar nada e retornar sucesso
        response = Response({"success": True, "message": "UI config atualizada localmente (sem parâmetros específicos na API da catraca)"})
        return response
    
    def sync_ui_config_from_catraca(self):
        """Sincroniza configurações de interface da catraca"""
        try:
            from ..models import UIConfig
            
            # Payload especificando parâmetros de UI
            payload = {"general": []}
            
            # Usa o helper com retry automático de sessão
            response = self._make_request("get_configuration.fcgi", json_data=payload)
            
            if response.status_code == 200:
                config_data = response.json().get('general', {})
            else:
                return Response({
                    "success": False,
                    "message": f"Erro ao obter configurações: {response.status_code}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            catraca_config = [config_data] if config_data else []
            
            # NOTA: screen_always_on NÃO está disponível na API dessa catraca
            # Sempre cria/atualiza com valor padrão False
            config, created = UIConfig.objects.update_or_create(
                device=self.device,
                defaults={
                    'screen_always_on': False  # Campo não disponível na API
                }
            )
            
            return Response({
                "success": True,
                "message": f"Configuração de interface {'criada' if created else 'atualizada'} com sucesso",
                "config_id": config.id,
                "warning": "Campo screen_always_on não disponível na API desta catraca"
            })
                
        except Exception as e:
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


