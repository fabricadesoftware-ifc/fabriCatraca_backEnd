from src.core.__seedwork__.infra import ControlIDSyncMixin
from rest_framework.response import Response
from rest_framework import status


class SecurityConfigSyncMixin(ControlIDSyncMixin):
    """Mixin para sincronização de configurações de segurança"""
    
    def update_security_config_in_catraca(self, instance):
        """Atualiza configurações de segurança na catraca"""
        try:
            def bool_to_str(value):
                return "1" if value else "0"
            
            payload = {
                "identifier": {
                    "multi_factor_authentication": bool_to_str(getattr(instance, 'multi_factor_authentication_enabled', False)),
                    "verbose_logging": bool_to_str(getattr(instance, 'verbose_logging_enabled', True))
                }
            }
            
            # Usa o helper com retry automático de sessão
            response = self._make_request("set_configuration.fcgi", json_data=payload)
            
            if response.status_code == 200:
                return Response(response.json(), status=status.HTTP_200_OK)
            else:
                return Response({
                    "success": False,
                    "error": f"Erro ao atualizar configuração: {response.status_code}",
                    "details": response.text
                }, status=response.status_code)
                
        except Exception as e:
            return Response({
                "success": False,
                "error": f"Exceção ao atualizar configuração: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def sync_security_config_from_catraca(self):
        """Sincroniza configurações de segurança da catraca IDBLOCK"""
        try:
            from ..models import SecurityConfig
            import logging
            logger = logging.getLogger(__name__)
            
            # Payload CORRETO para IDBLOCK
            # identifier: verbose_logging, log_type, multi_factor_authentication
            payload = {
                "identifier": [
                    "verbose_logging",
                    "log_type",
                    "multi_factor_authentication"
                ]
            }
            
            logger.info(f"[SECURITY_CONFIG_SYNC] Solicitando config da IDBLOCK: {payload}")
            
            # Usa o helper com retry automático de sessão
            response = self._make_request("get_configuration.fcgi", json_data=payload)
            
            if response.status_code == 200:
                full_response = response.json()
                # Configurações de segurança vêm da seção 'identifier'
                config_data = full_response.get('identifier', {}) if isinstance(full_response, dict) else {}
                logger.info(f"[SECURITY_CONFIG_SYNC] Resposta identifier: {config_data}")
            else:
                logger.error(f"[SECURITY_CONFIG_SYNC] Erro {response.status_code}: {response.text}")
                return Response({
                    "success": False,
                    "message": f"Erro ao obter configurações: {response.status_code}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            if not config_data:
                logger.warning("[SECURITY_CONFIG_SYNC] API retornou dados vazios - usando defaults")

            def to_bool(v, default=False):
                """Converte string '0'/'1' para bool."""
                if v is None:
                    return bool(default)
                if isinstance(v, bool):
                    return v
                if isinstance(v, str):
                    # Para IDBLOCK: "0" = False, "1" = True
                    return v.strip() in ("1", "true", "True")
                if isinstance(v, (int, float)):
                    return v != 0
                return bool(v)
            
            # Verifica se o modelo SecurityConfig tem os campos corretos
            # NOTA: Assumindo que SecurityConfig tem campos verbose_logging, log_type, multi_factor_authentication
            # Se não, precisaremos adaptar os nomes dos campos
            config, created = SecurityConfig.objects.update_or_create(
                device=self.device,
                defaults={
                    # Campos DISPONÍVEIS na IDBLOCK (seção identifier)
                    # NOTA: Aqui estou assumindo que os campos do model são:
                    # verbose_logging, log_type, multi_factor_authentication
                    # Se forem diferentes, precisaremos ajustar
                    'password_only': False,                 # Não existe na IDBLOCK
                    'hide_password_only': False,            # Não existe na IDBLOCK
                    'password_only_tip': '',                # Não existe na IDBLOCK
                    'hide_name_on_identification': False,   # Não existe na IDBLOCK
                    'denied_transaction_code': '',          # Não existe na IDBLOCK
                    'send_code_when_not_identified': False, # Não existe na IDBLOCK
                    'send_code_when_not_authorized': False  # Não existe na IDBLOCK
                }
            )
            
            logger.info(f"[SECURITY_CONFIG_SYNC] Config {'criada' if created else 'atualizada'}")
            
            return Response({
                "success": True,
                "message": f"Configuração de segurança {'criada' if created else 'atualizada'} com sucesso",
                "config_id": config.id,
                "note": "IDBLOCK não tem campos password_only, hide_password_only, etc. Usando defaults."
            })
                
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception("[SECURITY_CONFIG_SYNC] Exceção:")
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


