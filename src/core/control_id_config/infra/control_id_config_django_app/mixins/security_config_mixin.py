from src.core.__seedwork__.infra import ControlIDSyncMixin
from rest_framework.response import Response
from rest_framework import status


class SecurityConfigSyncMixin(ControlIDSyncMixin):
    """Mixin para sincronização de configurações de segurança"""
    
    def update_security_config_in_catraca(self, instance):
        """Atualiza configurações de segurança na catraca"""
        response = self.update_objects(
            "general",
            {
                "password_only": instance.password_only,
                "hide_password_only": instance.hide_password_only,
                "password_only_tip": instance.password_only_tip,
                "hide_name_on_identification": instance.hide_name_on_identification,
                "denied_transaction_code": instance.denied_transaction_code,
                "send_code_when_not_identified": instance.send_code_when_not_identified,
                "send_code_when_not_authorized": instance.send_code_when_not_authorized
            }
        )
        return response
    
    def sync_security_config_from_catraca(self):
        """Sincroniza configurações de segurança da catraca"""
        try:
            from ..models import SecurityConfig
            
            catraca_config = self.load_objects("general")
            
            if catraca_config:
                config_data = catraca_config[0]
                
                config, created = SecurityConfig.objects.update_or_create(
                    device=self.device,
                    defaults={
                        'password_only': config_data.get('password_only', False),
                        'hide_password_only': config_data.get('hide_password_only', False),
                        'password_only_tip': config_data.get('password_only_tip', ''),
                        'hide_name_on_identification': config_data.get('hide_name_on_identification', False),
                        'denied_transaction_code': config_data.get('denied_transaction_code', ''),
                        'send_code_when_not_identified': config_data.get('send_code_when_not_identified', False),
                        'send_code_when_not_authorized': config_data.get('send_code_when_not_authorized', False)
                    }
                )
                
                return Response({
                    "success": True,
                    "message": f"Configuração de segurança {'criada' if created else 'atualizada'} com sucesso",
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


