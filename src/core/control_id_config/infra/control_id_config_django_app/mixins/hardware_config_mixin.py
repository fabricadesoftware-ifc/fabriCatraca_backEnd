from src.core.__seedwork__.infra import ControlIDSyncMixin
from rest_framework.response import Response
from rest_framework import status


class HardwareConfigSyncMixin(ControlIDSyncMixin):
    """Mixin para sincronização de configurações de hardware"""
    
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
            
            catraca_config = self.load_objects("general")
            
            if catraca_config:
                config_data = catraca_config[0]
                
                config, created = HardwareConfig.objects.update_or_create(
                    device=self.device,
                    defaults={
                        'beep_enabled': config_data.get('beep_enabled', True),
                        'ssh_enabled': config_data.get('ssh_enabled', False),
                        'relayN_enabled': config_data.get('relayN_enabled', False),
                        'relayN_timeout': config_data.get('relayN_timeout', 5),
                        'relayN_auto_close': config_data.get('relayN_auto_close', True),
                        'door_sensorN_enabled': config_data.get('door_sensorN_enabled', False),
                        'door_sensorN_idle': config_data.get('door_sensorN_idle', 10),
                        'doorN_interlock': config_data.get('doorN_interlock', False),
                        'bell_enabled': config_data.get('bell_enabled', False),
                        'bell_relay': config_data.get('bell_relay', 1),
                        'exception_mode': config_data.get('exception_mode', False),
                        'doorN_exception_mode': config_data.get('doorN_exception_mode', False)
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


