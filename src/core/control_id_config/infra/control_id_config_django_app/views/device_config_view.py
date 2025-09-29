from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema
from src.core.control_Id.infra.control_id_django_app.models import Device
from ..models import SystemConfig, HardwareConfig, SecurityConfig, UIConfig
from ..mixins import (
    SystemConfigSyncMixin, 
    HardwareConfigSyncMixin, 
    SecurityConfigSyncMixin, 
    UIConfigSyncMixin
)


class DeviceConfigView(
    SystemConfigSyncMixin,
    HardwareConfigSyncMixin, 
    SecurityConfigSyncMixin,
    UIConfigSyncMixin,
    APIView
):
    """View unificada para gerenciar todas as configurações de um dispositivo"""
    
    @extend_schema(
        summary="Obter configurações do dispositivo",
        description="Retorna todas as configurações de um dispositivo específico"
    )
    def get(self, request, device_id):
        """Obtém todas as configurações de um dispositivo"""
        try:
            device = Device.objects.get(id=device_id)
            
            # Busca todas as configurações do dispositivo
            system_config = SystemConfig.objects.filter(device=device).first()
            hardware_config = HardwareConfig.objects.filter(device=device).first()
            security_config = SecurityConfig.objects.filter(device=device).first()
            ui_config = UIConfig.objects.filter(device=device).first()
            
            return Response({
                "device_id": device.id,
                "device_name": device.name,
                "system_config": {
                    "auto_reboot_hour": system_config.auto_reboot_hour if system_config else None,
                    "auto_reboot_minute": system_config.auto_reboot_minute if system_config else None,
                    "clear_expired_users": system_config.clear_expired_users if system_config else None,
                    "url_reboot_enabled": system_config.url_reboot_enabled if system_config else None,
                    "keep_user_image": system_config.keep_user_image if system_config else None,
                    "catra_timeout": system_config.catra_timeout if system_config else None,
                    "online": system_config.online if system_config else None,
                    "local_identification": system_config.local_identification if system_config else None,
                    "language": system_config.language if system_config else None,
                    "daylight_savings_time_start": system_config.daylight_savings_time_start if system_config else None,
                    "daylight_savings_time_end": system_config.daylight_savings_time_end if system_config else None,
                    "web_server_enabled": system_config.web_server_enabled if system_config else None
                },
                "hardware_config": {
                    "beep_enabled": hardware_config.beep_enabled if hardware_config else None,
                    "ssh_enabled": hardware_config.ssh_enabled if hardware_config else None,
                    "relayN_enabled": hardware_config.relayN_enabled if hardware_config else None,
                    "relayN_timeout": hardware_config.relayN_timeout if hardware_config else None,
                    "relayN_auto_close": hardware_config.relayN_auto_close if hardware_config else None,
                    "door_sensorN_enabled": hardware_config.door_sensorN_enabled if hardware_config else None,
                    "door_sensorN_idle": hardware_config.door_sensorN_idle if hardware_config else None,
                    "doorN_interlock": hardware_config.doorN_interlock if hardware_config else None,
                    "bell_enabled": hardware_config.bell_enabled if hardware_config else None,
                    "bell_relay": hardware_config.bell_relay if hardware_config else None,
                    "exception_mode": hardware_config.exception_mode if hardware_config else None,
                    "doorN_exception_mode": hardware_config.doorN_exception_mode if hardware_config else None
                },
                "security_config": {
                    "password_only": security_config.password_only if security_config else None,
                    "hide_password_only": security_config.hide_password_only if security_config else None,
                    "password_only_tip": security_config.password_only_tip if security_config else None,
                    "hide_name_on_identification": security_config.hide_name_on_identification if security_config else None,
                    "denied_transaction_code": security_config.denied_transaction_code if security_config else None,
                    "send_code_when_not_identified": security_config.send_code_when_not_identified if security_config else None,
                    "send_code_when_not_authorized": security_config.send_code_when_not_authorized if security_config else None
                },
                "ui_config": {
                    "screen_always_on": ui_config.screen_always_on if ui_config else None
                }
            })
            
        except Device.DoesNotExist:
            return Response(
                {"error": "Dispositivo não encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Erro ao obter configurações: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Sincronizar configurações da catraca",
        description="Sincroniza todas as configurações de um dispositivo com a catraca"
    )
    def post(self, request, device_id):
        """Sincroniza configurações da catraca"""
        try:
            device = Device.objects.get(id=device_id)
            self.set_device(device)
            
            # Sincroniza todas as configurações
            system_response = self.sync_system_config_from_catraca()
            hardware_response = self.sync_hardware_config_from_catraca()
            security_response = self.sync_security_config_from_catraca()
            ui_response = self.sync_ui_config_from_catraca()
            
            return Response({
                "message": "Sincronização de configurações concluída",
                "results": {
                    "system_config": system_response.data,
                    "hardware_config": hardware_response.data,
                    "security_config": security_response.data,
                    "ui_config": ui_response.data
                }
            })
            
        except Device.DoesNotExist:
            return Response(
                {"error": "Dispositivo não encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Erro ao sincronizar configurações: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


