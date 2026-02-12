from rest_framework import status
from rest_framework.response import Response
from src.core.__seedwork__.infra.catraca_sync import ControlIDSyncMixin
import logging

logger = logging.getLogger(__name__)


class MonitorConfigSyncMixin(ControlIDSyncMixin):
    """
    Mixin para sincronização de configurações de Monitor com a catraca

    O Monitor é um sistema PUSH onde a CATRACA envia logs automaticamente
    para um servidor configurado, ao invés de termos que ficar sincronizando.

    Isso é muito mais eficiente porque:
    - Logs chegam em tempo real quando alguém passa
    - Não precisa ficar fazendo polling/sync periódico
    - Reduz carga no servidor e na catraca
    - Permite notificações instantâneas
    """

    # Campos obrigatórios que TODA catraca Control iD suporta no bloco monitor
    MONITOR_BASE_FIELDS = ["hostname", "port", "path", "request_timeout"]

    # Campos opcionais que só alguns modelos/firmwares suportam
    MONITOR_OPTIONAL_FIELDS = ["alive_interval", "inform_access_event_id"]

    def update_monitor_config_in_catraca(self, instance):
        """
        Atualiza configurações de monitor NA CATRACA

        Envia via set_configuration.fcgi o bloco 'monitor' com:
        - request_timeout: tempo de timeout das requisições HTTP
        - hostname: servidor que vai receber as notificações
        - port: porta do servidor
        - path: endpoint/path onde enviar
        """
        try:
            # Monta o payload APENAS com os campos básicos suportados
            monitor_data = {}

            if (
                hasattr(instance, "request_timeout")
                and instance.request_timeout is not None
            ):
                monitor_data["request_timeout"] = str(instance.request_timeout)

            if hasattr(instance, "hostname"):
                monitor_data["hostname"] = str(instance.hostname or "")

            if hasattr(instance, "port"):
                monitor_data["port"] = str(instance.port or "")

            if hasattr(instance, "path"):
                monitor_data["path"] = str(instance.path or "")

            if not monitor_data:
                return Response(
                    {
                        "success": False,
                        "error": "Nenhum campo de monitor para atualizar",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            payload = {"monitor": monitor_data}

            logger.info(f"[MONITOR_CONFIG] Enviando para catraca: {payload}")

            response = self._make_request("set_configuration.fcgi", json_data=payload)

            logger.info(
                f"[MONITOR_CONFIG] Resposta - Status: {response.status_code}, Body: {response.text}"
            )

            if response.status_code == 200:
                return Response(response.json(), status=status.HTTP_200_OK)
            else:
                return Response(
                    {
                        "success": False,
                        "error": f"Erro ao atualizar configuração: {response.status_code}",
                        "details": response.text,
                    },
                    status=response.status_code,
                )

        except Exception as e:
            logger.exception("[MONITOR_CONFIG] Exceção ao atualizar:")
            return Response(
                {
                    "success": False,
                    "error": f"Exceção ao atualizar configuração: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def sync_monitor_config_from_catraca(self):
        """
        Sincroniza configurações de monitor DA CATRACA para o sistema

        Busca via get_configuration.fcgi o bloco 'monitor'.
        Primeiro tenta apenas os campos básicos (hostname, port, path, request_timeout).
        Se a catraca retornar erro, o módulo monitor pode não existir nesse firmware.
        """
        try:
            # Passo 1: Pedir apenas os campos BÁSICOS que toda catraca suporta
            payload = {"monitor": list(self.MONITOR_BASE_FIELDS)}

            logger.info(
                f"[MONITOR_CONFIG_SYNC] Solicitando config da catraca: {payload}"
            )

            response = self._make_request("get_configuration.fcgi", json_data=payload)

            if response.status_code != 200:
                error_text = response.text
                logger.warning(
                    f"[MONITOR_CONFIG_SYNC] Erro {response.status_code}: {error_text}"
                )

                # Se HTTP 400 com "Node or attribute not found" → módulo monitor não existe
                if response.status_code == 400 and "not found" in error_text.lower():
                    return Response(
                        {
                            "success": False,
                            "error": "Módulo monitor não disponível neste firmware/modelo de catraca",
                            "hint": "Este equipamento pode não suportar o sistema de monitor nativo. "
                            "Verifique o firmware ou use o push_server como alternativa.",
                            "is_configuration_missing": True,
                        },
                        status=status.HTTP_404_NOT_FOUND,
                    )

                return Response(
                    {
                        "success": False,
                        "error": f"Erro ao buscar configurações: HTTP {response.status_code}",
                        "details": error_text,
                    },
                    status=response.status_code,
                )

            data = response.json() or {}
            monitor_data = data.get("monitor", {})

            logger.info(f"[MONITOR_CONFIG_SYNC] Resposta da catraca: {monitor_data}")

            # Passo 2 (opcional): Tentar buscar campos extras sem quebrar
            for field in self.MONITOR_OPTIONAL_FIELDS:
                try:
                    extra_response = self._make_request(
                        "get_configuration.fcgi", json_data={"monitor": [field]}
                    )
                    if extra_response.status_code == 200:
                        extra_data = extra_response.json() or {}
                        extra_monitor = extra_data.get("monitor", {})
                        if isinstance(extra_monitor, dict) and field in extra_monitor:
                            monitor_data[field] = extra_monitor[field]
                except Exception:
                    pass  # Campo não suportado, ignora silenciosamente

            if isinstance(monitor_data, dict) and monitor_data:
                return Response(
                    {
                        "success": True,
                        "monitor": monitor_data,
                        "message": "Configurações de monitor obtidas com sucesso",
                    },
                    status=status.HTTP_200_OK,
                )

            return Response(
                {
                    "success": False,
                    "error": "Dispositivo não tem monitor configurado",
                    "hint": "Monitor é opcional. Use POST /monitor-configs/ para configurar.",
                    "is_configuration_missing": True,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        except Exception as e:
            logger.exception("[MONITOR_CONFIG_SYNC] Exceção:")
            return Response(
                {
                    "success": False,
                    "error": f"Erro ao sincronizar configurações: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def sync_monitor_into_model(self):
        """
        Sincroniza da catraca e persiste no model MonitorConfig

        Busca as configurações da catraca e atualiza/cria o MonitorConfig local
        """
        try:
            from ..models import MonitorConfig

            # Busca da catraca
            response = self.sync_monitor_config_from_catraca()

            if response.status_code != 200:
                return response

            monitor_data = response.data.get("monitor", {})

            if not monitor_data:
                return Response(
                    {"success": False, "error": "Nenhum dado de monitor retornado"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Atualiza ou cria o MonitorConfig
            config, created = MonitorConfig.objects.update_or_create(
                device=self.device,
                defaults={
                    "request_timeout": int(monitor_data.get("request_timeout", 1000)),
                    "hostname": monitor_data.get("hostname", ""),
                    "port": monitor_data.get("port", ""),
                    "path": monitor_data.get("path", "api/notifications"),
                },
            )

            action = "criada" if created else "atualizada"

            return Response(
                {
                    "success": True,
                    "message": f"Configuração de monitor {action} com sucesso",
                    "config_id": config.id,
                    "is_configured": config.is_configured,
                    "full_url": config.full_url,
                    "monitor_data": monitor_data,
                },
                status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": f"Erro ao persistir configuração: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
