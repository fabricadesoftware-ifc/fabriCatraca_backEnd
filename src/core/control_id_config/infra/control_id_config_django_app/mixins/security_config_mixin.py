from rest_framework import status
from rest_framework.response import Response

from src.core.__seedwork__.infra import ControlIDSyncMixin


class SecurityConfigSyncMixin(ControlIDSyncMixin):
    """Mixin para sincronizacao de configuracoes de seguranca."""

    @staticmethod
    def _to_bool(value, default=False):
        if value is None:
            return bool(default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip() in ("1", "true", "True")
        if isinstance(value, (int, float)):
            return value != 0
        return bool(value)

    def update_security_config_in_catraca(self, instance):
        """Atualiza o bloco `identifier` na catraca."""
        try:
            payload = {
                "identifier": {
                    "multi_factor_authentication": "1"
                    if getattr(instance, "multi_factor_authentication_enabled", False)
                    else "0",
                    "verbose_logging": "1"
                    if getattr(instance, "verbose_logging_enabled", True)
                    else "0",
                    "log_type": "1" if getattr(instance, "log_type", False) else "0",
                }
            }

            response = self._make_request("set_configuration.fcgi", json_data=payload)

            if response.status_code == 200:
                return Response(response.json(), status=status.HTTP_200_OK)

            return Response(
                {
                    "success": False,
                    "error": f"Erro ao atualizar configuracao: {response.status_code}",
                    "details": response.text,
                },
                status=response.status_code,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": f"Excecao ao atualizar configuracao: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def sync_security_config_from_catraca(self):
        """Sincroniza o bloco `identifier` da catraca para o banco."""
        try:
            from ..models import SecurityConfig
            import logging

            logger = logging.getLogger(__name__)
            payload = {
                "identifier": [
                    "verbose_logging",
                    "log_type",
                    "multi_factor_authentication",
                ]
            }

            logger.info(f"[SECURITY_CONFIG_SYNC] Solicitando config da catraca: {payload}")
            response = self._make_request("get_configuration.fcgi", json_data=payload)

            if response.status_code != 200:
                logger.error(
                    f"[SECURITY_CONFIG_SYNC] Erro {response.status_code}: {response.text}"
                )
                return Response(
                    {
                        "success": False,
                        "message": f"Erro ao obter configuracoes: {response.status_code}",
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            full_response = response.json()
            config_data = (
                full_response.get("identifier", {}) if isinstance(full_response, dict) else {}
            )
            logger.info(f"[SECURITY_CONFIG_SYNC] Resposta identifier: {config_data}")

            config, created = SecurityConfig.objects.update_or_create(
                device=self.device,
                defaults={
                    "verbose_logging_enabled": self._to_bool(
                        config_data.get("verbose_logging"), True
                    ),
                    "log_type": self._to_bool(config_data.get("log_type"), False),
                    "multi_factor_authentication_enabled": self._to_bool(
                        config_data.get("multi_factor_authentication"), False
                    ),
                },
            )

            logger.info(
                "[SECURITY_CONFIG_SYNC] Config %s: verbose=%s log_type=%s mfa=%s",
                "criada" if created else "atualizada",
                config.verbose_logging_enabled,
                config.log_type,
                config.multi_factor_authentication_enabled,
            )

            return Response(
                {
                    "success": True,
                    "message": f"Configuracao de seguranca {'criada' if created else 'atualizada'} com sucesso",
                    "config_id": config.id,
                }
            )
        except Exception as e:
            import logging

            logging.getLogger(__name__).exception("[SECURITY_CONFIG_SYNC] Excecao:")
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
