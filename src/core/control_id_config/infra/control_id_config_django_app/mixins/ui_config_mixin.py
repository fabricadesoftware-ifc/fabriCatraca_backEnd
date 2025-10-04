from src.core.__seedwork__.infra import ControlIDSyncMixin
from rest_framework.response import Response
from rest_framework import status


class UIConfigSyncMixin(ControlIDSyncMixin):
    """Mixin para sincronização de configurações de interface"""
    
    def update_ui_config_in_catraca(self, instance):
        """Atualiza configurações de interface na catraca"""
        
        # Envia configurações de UI para a catraca via set_configuration.fcgi
        # Usando a seção 'general' onde screen_always_on está disponível
        response = self.update_objects(
            "general",
            {
                "screen_always_on": instance.screen_always_on,
            },
        )
        return response
    
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


