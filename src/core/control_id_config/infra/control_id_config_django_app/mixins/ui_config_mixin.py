from src.core.__seedwork__.infra import ControlIDSyncMixin
from rest_framework.response import Response
from rest_framework import status


class UIConfigSyncMixin(ControlIDSyncMixin):
    """Mixin para sincronização de configurações de interface"""
    
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
            
            catraca_config = self.load_objects("general")
            
            if catraca_config:
                config_data = catraca_config[0]
                
                config, created = UIConfig.objects.update_or_create(
                    device=self.device,
                    defaults={
                        'screen_always_on': config_data.get('screen_always_on', False)
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


