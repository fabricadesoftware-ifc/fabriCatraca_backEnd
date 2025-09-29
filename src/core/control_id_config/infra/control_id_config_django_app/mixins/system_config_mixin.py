from src.core.__seedwork__.infra import ControlIDSyncMixin
from rest_framework.response import Response
from rest_framework import status


class SystemConfigSyncMixin(ControlIDSyncMixin):
    """Mixin para sincronização de configurações do sistema"""
    
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
            
            catraca_config = self.load_objects("general")
            
            if catraca_config:
                config_data = catraca_config[0]  # Assume que há apenas uma configuração
                
                # Atualiza ou cria configuração local
                config, created = SystemConfig.objects.update_or_create(
                    device=self.device,
                    defaults={
                        'auto_reboot_hour': config_data.get('auto_reboot_hour', 3),
                        'auto_reboot_minute': config_data.get('auto_reboot_minute', 0),
                        'clear_expired_users': config_data.get('clear_expired_users', False),
                        'url_reboot_enabled': config_data.get('url_reboot_enabled', True),
                        'keep_user_image': config_data.get('keep_user_image', True),
                        'catra_timeout': config_data.get('catra_timeout', 30),
                        'online': config_data.get('online', True),
                        'local_identification': config_data.get('local_identification', True),
                        'language': config_data.get('language', 'pt'),
                        'daylight_savings_time_start': config_data.get('daylight_savings_time_start'),
                        'daylight_savings_time_end': config_data.get('daylight_savings_time_end'),
                        'web_server_enabled': config_data.get('web_server_enabled', True)
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

