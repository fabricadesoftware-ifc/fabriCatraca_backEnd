from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
import logging

from .models import MonitorConfig
from src.core.control_Id.infra.control_id_django_app.models import Device
from .serializers import MonitorConfigSerializer
from .mixins import MonitorConfigSyncMixin
from .notification_handlers import monitor_handler

logger = logging.getLogger(__name__)


@extend_schema(tags=["Monitor (Push Logs)"])
class MonitorConfigViewSet(MonitorConfigSyncMixin, viewsets.ModelViewSet):
    """
    ViewSet para MonitorConfig - Sistema de Push de Logs em Tempo Real

    O Monitor permite que a catraca ENVIE logs automaticamente para um servidor,
    ao invés de termos que ficar sincronizando manualmente.

    Endpoints principais:
    - POST /api/monitor/monitor-configs/ - Cria config e envia para catraca
    - PATCH /api/monitor/monitor-configs/{id}/ - Atualiza config e envia
    - POST /api/monitor/monitor-configs/{id}/sync-from-catraca/ - Sincroniza da catraca
    - GET /api/monitor/monitor-configs/{id}/probe/ - Debug: vê config raw da catraca
    - GET /api/monitor/monitor-configs/probe-by-device/{device_id}/ - Debug por device
    """

    queryset = MonitorConfig.objects.all()
    serializer_class = MonitorConfigSerializer
    filterset_fields = ["device", "hostname"]
    search_fields = ["device__name", "hostname"]
    ordering_fields = ["device__name", "created_at"]
    ordering = ["device__name"]

    def create(self, request, *args, **kwargs):
        """
        Cria uma nova configuração de monitor E envia para a catraca

        Se falhar na catraca, reverte a criação no banco
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        # Envia para a catraca
        self.set_device(instance.device)
        response = self.update_monitor_config_in_catraca(instance)

        if response.status_code != status.HTTP_200_OK:
            instance.delete()  # Reverte se falhar na catraca
            return response

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """
        Atualiza configuração de monitor E envia para a catraca
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        # Envia para a catraca
        self.set_device(instance.device)
        response = self.update_monitor_config_in_catraca(instance)

        if response.status_code != status.HTTP_200_OK:
            return response

        # Retorna a configuração atualizada
        return Response(serializer.data)

    @extend_schema(
        summary="Sincronizar configurações de monitor da catraca",
        description="""
        Busca as configurações atuais do monitor diretamente da catraca
        e atualiza o MonitorConfig local.

        Útil para:
        - Descobrir se o monitor está configurado na catraca
        - Sincronizar configurações alteradas diretamente na catraca
        - Verificar URL de notificação configurada
        """,
        responses={
            200: {
                "description": "Configuração sincronizada com sucesso",
                "examples": {
                    "application/json": {
                        "success": True,
                        "message": "Configuração de monitor atualizada com sucesso",
                        "config_id": 1,
                        "is_configured": True,
                        "full_url": "http://api.exemplo.com:8000/api/notifications",
                        "monitor_data": {
                            "request_timeout": "1000",
                            "hostname": "api.exemplo.com",
                            "port": "8000",
                            "path": "api/notifications",
                        },
                    }
                },
            }
        },
    )
    @action(detail=True, methods=["post"])
    def sync_from_catraca(self, request, pk=None):
        """Sincroniza da catraca e persiste no banco"""
        instance = self.get_object()
        self.set_device(instance.device)
        return self.sync_monitor_into_model()

    @extend_schema(
        summary="Debug: Obter configuração raw da catraca",
        description="""
        Retorna o payload bruto do bloco monitor via get_configuration.fcgi.

        Útil para:
        - Debug e troubleshooting
        - Ver exatamente o que a catraca retorna
        - Verificar campos disponíveis na catraca
        """,
        responses={
            200: {
                "description": "Payload raw obtido com sucesso",
                "examples": {
                    "application/json": {
                        "success": True,
                        "monitor": {
                            "request_timeout": "1000",
                            "hostname": "api.exemplo.com",
                            "port": "8000",
                            "path": "api/notifications",
                        },
                        "message": "Configurações de monitor obtidas com sucesso",
                    }
                },
            }
        },
    )
    @action(detail=True, methods=["get"], url_path="probe")
    def probe_from_catraca(self, request, pk=None):
        """Debug: retorna payload raw da catraca SEM persistir"""
        instance = self.get_object()
        self.set_device(instance.device)
        return self.sync_monitor_config_from_catraca()

    @extend_schema(
        summary="Debug: Obter configuração raw por device_id",
        description="""
        Retorna o payload bruto do bloco monitor para um device específico,
        SEM necessidade de ter MonitorConfig criado.

        Útil para:
        - Descobrir se uma catraca tem monitor configurado antes de criar o config
        - Debug de dispositivos sem MonitorConfig no banco
        """,
        parameters=[
            OpenApiParameter(
                name="device_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="ID do dispositivo/catraca",
            ),
        ],
        responses={
            200: {"description": "Payload raw obtido com sucesso"},
            404: {"description": "Dispositivo não encontrado"},
        },
    )
    @action(
        detail=False, methods=["get"], url_path="probe-by-device/(?P<device_id>\\d+)"
    )
    def probe_by_device(self, request, device_id=None):
        """Debug: retorna payload raw da catraca por device_id"""
        try:
            device = Device.objects.get(id=device_id)
        except Device.DoesNotExist:
            return Response(
                {"error": "Dispositivo não encontrado", "device_id": device_id},
                status=status.HTTP_404_NOT_FOUND,
            )

        self.set_device(device)
        return self.sync_monitor_config_from_catraca()

    @extend_schema(
        summary="Ativar monitor (configurar servidor de notificações)",
        description="""
        Ativa o sistema de push de logs configurando o servidor onde
        a catraca enviará notificações em tempo real.

        Exemplo de body:
        {
            "hostname": "api.exemplo.com",
            "port": "8000",
            "path": "/api/monitor/events",
            "request_timeout": 5000
        }

        Após ativado, a catraca enviará notificações HTTP POST para:
        http://api.exemplo.com:8000/api/monitor/events
        """,
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "hostname": {"type": "string", "example": "api.exemplo.com"},
                    "port": {"type": "string", "example": "8000"},
                    "path": {"type": "string", "example": "/api/monitor/events"},
                    "request_timeout": {"type": "integer", "example": 5000},
                },
                "required": ["hostname", "port"],
            }
        },
    )
    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        """Ativa o monitor configurando servidor de notificações"""
        instance = self.get_object()

        # Valida e atualiza os dados
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Verifica se hostname foi fornecido
        if not serializer.validated_data.get("hostname"):
            return Response(
                {
                    "error": "hostname é obrigatório para ativar o monitor",
                    "hint": "Forneça o hostname/IP do servidor que receberá as notificações",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance = serializer.save()

        # Envia para a catraca
        self.set_device(instance.device)
        response = self.update_monitor_config_in_catraca(instance)

        if response.status_code != status.HTTP_200_OK:
            return response

        return Response(
            {
                "success": True,
                "message": "Monitor ativado com sucesso!",
                "notification_url": instance.full_url,
                "config": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Desativar monitor",
        description="""
        Desativa o sistema de push de logs limpando as configurações
        do servidor de notificações na catraca.

        A catraca para de enviar notificações após esta ação.
        """,
    )
    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        """Desativa o monitor limpando configurações"""
        instance = self.get_object()

        # Limpa as configurações
        instance.hostname = ""
        instance.port = ""
        instance.path = "api/notifications"
        instance.save()

        # Envia para a catraca
        self.set_device(instance.device)
        response = self.update_monitor_config_in_catraca(instance)

        if response.status_code != status.HTTP_200_OK:
            return response

        return Response(
            {
                "success": True,
                "message": "Monitor desativado com sucesso",
                "config": MonitorConfigSerializer(instance).data,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================================
# VIEW PARA RECEBER NOTIFICAÇÕES DA CATRACA (PUSH ENDPOINT)
# ============================================================================


@extend_schema(
    tags=["Monitor (Push Logs) - Webhook"],
    summary="Recebe notificações da catraca (PUSH)",
    description="""
    **Endpoint para receber notificações em tempo real da catraca**

    Este endpoint é configurado na catraca através do MonitorConfig e recebe
    automaticamente notificações quando ocorrem mudanças em:

    - **access_logs**: Logs de acesso (entrada/saída de pessoas)
    - **templates**: Templates biométricos
    - **cards**: Cartões RFID
    - **alarm_logs**: Logs de alarme

    A catraca faz uma requisição POST para esta URL sempre que há uma mudança
    (inserção, atualização ou deleção) nas tabelas acima.

    **Como configurar:**
    1. Crie um MonitorConfig com hostname, port e path
    2. Use o método `activate()` para enviar a config para a catraca
    3. A catraca começará a enviar notificações para este endpoint

    **Formato esperado:**
    ```json
    {
        "object_changes": [
            {
                "object": "access_logs",
                "type": "inserted",
                "values": {
                    "id": "519",
                    "time": "1532977090",
                    "event": "12",
                    "device_id": "478435",
                    "identifier_id": "0",
                    "user_id": "0",
                    "portal_id": "1",
                    "card_value": "0",
                    "log_type_id": "-1"
                }
            }
        ],
        "device_id": 478435
    }
    ```

    **Tipos de mudança (type):**
    - `inserted`: Novo registro criado
    - `updated`: Registro atualizado
    - `deleted`: Registro deletado

    **Tipos de objeto (object):**
    - `access_logs`: Logs de acesso
    - `templates`: Biometria
    - `cards`: Cartões RFID
    - `alarm_logs`: Alarmes
    """,
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "object_changes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "object": {
                                "type": "string",
                                "enum": [
                                    "access_logs",
                                    "templates",
                                    "cards",
                                    "alarm_logs",
                                ],
                            },
                            "type": {
                                "type": "string",
                                "enum": ["inserted", "updated", "deleted"],
                            },
                            "values": {"type": "object"},
                        },
                    },
                },
                "device_id": {"type": "integer"},
            },
            "required": ["object_changes", "device_id"],
        }
    },
    examples=[
        OpenApiExample(
            name="Access Log Insert",
            description="Notificação de novo log de acesso",
            value={
                "object_changes": [
                    {
                        "object": "access_logs",
                        "type": "inserted",
                        "values": {
                            "id": "519",
                            "time": "1532977090",
                            "event": "12",
                            "device_id": "478435",
                            "user_id": "123",
                            "portal_id": "1",
                            "card_value": "123456789",
                        },
                    }
                ],
                "device_id": 478435,
            },
        ),
        OpenApiExample(
            name="Multiple Changes",
            description="Múltiplas mudanças em uma notificação",
            value={
                "object_changes": [
                    {
                        "object": "access_logs",
                        "type": "inserted",
                        "values": {
                            "id": "520",
                            "time": "1532977100",
                            "event": "12",
                            "device_id": "478435",
                        },
                    },
                    {
                        "object": "access_logs",
                        "type": "inserted",
                        "values": {
                            "id": "521",
                            "time": "1532977110",
                            "event": "12",
                            "device_id": "478435",
                        },
                    },
                ],
                "device_id": 478435,
            },
        ),
    ],
    responses={
        200: {
            "description": "Notificação processada com sucesso",
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "device_id": {"type": "integer"},
                "total_changes": {"type": "integer"},
                "processed": {"type": "integer"},
                "results": {"type": "array"},
            },
        },
        400: {"description": "Payload inválido"},
        500: {"description": "Erro ao processar notificação"},
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])  # A catraca não envia autenticação
def receive_dao_notification(request):
    """
    Recebe notificações DAO (Data Access Object) da catraca

    Este é o endpoint configurado no monitor da catraca.
    Ele é chamado automaticamente sempre que há mudanças em:
    - access_logs, templates, cards, alarm_logs
    """
    try:
        logger.info("📥 [MONITOR] Recebendo notificação da catraca")
        logger.info(f"📥 [MONITOR] Payload completo: {request.data}")

        # Valida payload básico
        if not isinstance(request.data, dict):
            logger.error("❌ [MONITOR] Payload não é um dict")
            return Response(
                {"success": False, "error": "Payload deve ser um objeto JSON"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device_id = request.data.get("device_id")
        object_changes = request.data.get("object_changes")

        if not device_id:
            logger.error("❌ [MONITOR] device_id ausente")
            return Response(
                {"success": False, "error": "device_id é obrigatório"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(object_changes, list):
            logger.error("❌ [MONITOR] object_changes não é uma lista")
            return Response(
                {"success": False, "error": "object_changes deve ser uma lista"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Processa notificação
        result = monitor_handler.process_notification(request.data)

        if result.get("success"):
            logger.info(
                f"✅ [MONITOR] Notificação processada com sucesso: {result.get('processed')} itens"
            )
            return Response(result, status=status.HTTP_200_OK)
        else:
            error_detail = (
                result.get("error") or result.get("errors") or "Erro desconhecido"
            )
            logger.error(f"❌ [MONITOR] Erro processando notificação: {error_detail}")
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        logger.error(f"❌ [MONITOR] Exceção não tratada: {e}", exc_info=True)
        return Response(
            {"success": False, "error": f"Erro interno: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def receive_auxiliary_notification(request):
    """
    Recebe notificações auxiliares da catraca (operation_mode, device_is_alive).

    Esses endpoints são chamados pelo firmware após reboot ou troca de
    modo de operação. Apenas loga e retorna 200 para o device não ficar
    re-tentando.
    """
    logger.info(
        f"📥 [MONITOR] Notificação auxiliar recebida: "
        f"{request.path} — {request.data}"
    )
    return Response({"success": True})


# ============================================================================
# VIEW PARA RECEBER EVENTOS DE GIRO DA CATRACA (catra_event)
# ============================================================================


_CATRA_EVENT_NAMES = {
    7: "TURN_LEFT",
    8: "TURN_RIGHT",
    9: "GIVE_UP",
}


@extend_schema(
    tags=["Monitor (Push Logs) - Webhook"],
    summary="Recebe eventos de giro da catraca iDBlock (catra_event)",
    description="""
    Endpoint exclusivo para a catraca iDBlock que recebe eventos de
    confirmação de giro. Os eventos possíveis são:

    - **EVENT_TURN_LEFT (type 7)**: giro à esquerda (entrada ou saída).
    - **EVENT_TURN_RIGHT (type 8)**: giro à direita (entrada ou saída).
    - **EVENT_GIVE_UP (type 9)**: usuário identificado mas desistiu de passar.

    O campo opcional `access_event_id` associa o evento ao registro
    correspondente na tabela access_events (quando `inform_access_event_id=1`).

    Cada evento recebido é salvo como AccessLog para que o fluxo de
    passagens possa ser monitorado no frontend.
    """,
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "event": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "integer", "example": 7},
                        "name": {"type": "string", "example": "TURN LEFT"},
                        "time": {"type": "integer", "example": 1484126902},
                        "uuid": {"type": "string", "example": "0e039178"},
                    },
                },
                "access_event_id": {"type": "integer", "example": 15},
                "device_id": {"type": "integer", "example": 935107},
                "time": {"type": "integer", "example": 1484126902},
            },
            "required": ["event", "device_id", "time"],
        }
    },
    responses={
        200: {"description": "Evento processado com sucesso"},
        400: {"description": "Payload inválido"},
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
def receive_catra_event(request):
    """
    Recebe eventos de giro (catra_event) da catraca iDBlock.

    Salva cada evento como um AccessLog para monitoramento de fluxo.
    """
    from datetime import datetime, timezone as dt_timezone
    from src.core.control_Id.infra.control_id_django_app.models import (
        AccessLogs,
        Device,
        Portal,
    )
    from .models import MonitorConfig

    try:
        payload = request.data
        logger.info(f"📥 [CATRA_EVENT] Payload recebido: {payload}")

        if not isinstance(payload, dict):
            return Response(
                {"success": False, "error": "Payload deve ser um objeto JSON"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        event_data = payload.get("event")
        device_id = payload.get("device_id")
        event_time = payload.get("time")

        if not event_data or not device_id:
            return Response(
                {"success": False, "error": "event e device_id são obrigatórios"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        event_type = event_data.get("type", 0)
        event_name = event_data.get("name", _CATRA_EVENT_NAMES.get(event_type, "UNKNOWN"))
        event_uuid = event_data.get("uuid", "")
        access_event_id = payload.get("access_event_id")

        # ── Resolve device ──
        device = Device.objects.filter(id=device_id).first()
        if not device:
            monitor_cfg = MonitorConfig.objects.select_related("device").first()
            if monitor_cfg:
                device = monitor_cfg.device
        if not device:
            device = Device.objects.filter(is_default=True).first() or Device.objects.filter(is_active=True).first()
        if not device:
            logger.error(f"❌ [CATRA_EVENT] Nenhum device para device_id={device_id}")
            return Response(
                {"success": False, "error": f"Device {device_id} não encontrado"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Timestamp ──
        timestamp = (
            datetime.fromtimestamp(int(event_time), tz=dt_timezone.utc)
            if event_time
            else datetime.now(tz=dt_timezone.utc)
        )

        # ── Resolve portal ──
        raw_portal_id = (
            payload.get("portal_id")
            or payload.get("door_id")
            or event_data.get("portal_id")
            or event_data.get("door_id")
        )
        portal = None
        if raw_portal_id is not None:
            try:
                portal_id = int(raw_portal_id)
                if portal_id > 0:
                    portal = Portal.objects.filter(id=portal_id).first()
                    if not portal:
                        logger.warning(
                            f"⚠️ [CATRA_EVENT] Portal id={portal_id} não existe no banco"
                        )
            except (TypeError, ValueError):
                logger.warning(
                    f"⚠️ [CATRA_EVENT] portal_id inválido recebido: {raw_portal_id}"
                )

        # ── Mapeia event_type da catraca para EventType do model ──
        # 7 = TURN_LEFT / 8 = TURN_RIGHT → registra como ACESSO_CONCEDIDO (7)
        # 9 = GIVE_UP → registra como DESISTENCIA_DE_ENTRADA (13)
        if event_type == 9:
            model_event_type = 13  # DESISTENCIA_DE_ENTRADA
        else:
            model_event_type = 7   # ACESSO_CONCEDIDO

        # ── Identifier único: uuid do evento ou access_event_id ──
        identifier = event_uuid or str(access_event_id or event_time or "")

        log, created = AccessLogs.objects.update_or_create(
            device=device,
            identifier_id=identifier,
            time=timestamp,
            defaults={
                "event_type": model_event_type,
                "user": None,
                "portal": portal,
                "access_rule": None,
                "card_value": "",
                "qr_code": "",
                "uhf_value": "",
                "pin_value": "",
                "confidence": 0,
                "mask": "",
            },
        )

        action = "created" if created else "already_exists"
        logger.info(
            f"✅ [CATRA_EVENT] {action} — {event_name} (type={event_type}) "
            f"device={device.name} portal={portal.name if portal else raw_portal_id} "
            f"uuid={event_uuid} access_event_id={access_event_id}"
        )

        return Response(
            {
                "success": True,
                "action": action,
                "event_name": event_name,
                "event_type": event_type,
                "model_event_type": model_event_type,
                "device": str(device),
                "portal": portal.name if portal else None,
                "time": str(timestamp),
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        logger.error(f"❌ [CATRA_EVENT] Erro: {e}", exc_info=True)
        return Response(
            {"success": False, "error": f"Erro interno: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
