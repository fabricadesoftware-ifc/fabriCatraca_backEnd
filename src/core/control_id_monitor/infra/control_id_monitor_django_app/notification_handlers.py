"""
Handlers para processar notificações recebidas do Monitor da Catraca

O Monitor é um sistema PUSH onde a catraca envia automaticamente:
- Logs de acesso (access_logs)
- Templates (biometria)
- Cartões (cards)
- Alarmes (alarm_logs)

Quando há inserção, alteração ou deleção dessas entidades.
"""

from typing import Dict, Any
from copy import deepcopy
from datetime import datetime, timezone as dt_timezone
from zoneinfo import ZoneInfo

from django.db import transaction
import logging

from .access_verification import access_verifier

logger = logging.getLogger(__name__)
DEVICE_LOCAL_TIMEZONE = ZoneInfo("America/Sao_Paulo")


class MonitorNotificationHandler:
    """
    Processa notificações enviadas pela catraca via Monitor

    Formato esperado:
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
                    ...
                }
            }
        ],
        "device_id": 478435
    }
    """

    def __init__(self):
        self.handlers = {
            "access_logs": self._handle_access_log,
            "templates": self._handle_template,
            "cards": self._handle_card,
            "alarm_logs": self._handle_alarm_log,
        }

    def process_notification(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa uma notificação recebida da catraca

        Args:
            payload: JSON enviado pela catraca

        Returns:
            dict: Resultado do processamento
        """
        try:
            sentido = payload.get(
                "name"
            )  # Campo opcional que pode indicar direção do acesso
            device_id = payload.get("device_id")
            object_changes = payload.get("object_changes", [])

            if not device_id:
                logger.error("Notificação sem device_id")
                return {
                    "success": False,
                    "error": "device_id é obrigatório",
                    "processed": 0,
                }

            if not object_changes:
                logger.warning(f"Notificação vazia do device {device_id}")
                return {
                    "success": True,
                    "warning": "Nenhuma mudança recebida",
                    "processed": 0,
                }

            logger.info(
                f"📥 [MONITOR] Recebendo {len(object_changes)} mudanças do device {device_id}"
            )

            results = []
            processed = 0
            errors = []

            with transaction.atomic():
                for change in object_changes:
                    try:
                        result = self._process_single_change(
                            device_id=device_id,
                            change=change,
                            raw_notification=payload,
                            sentido=sentido,
                        )
                        results.append(result)
                        if result.get("success"):
                            processed += 1
                        else:
                            errors.append(result.get("error"))
                    except Exception as e:
                        error_msg = f"Erro processando {change.get('object')}: {str(e)}"
                        logger.error(error_msg, exc_info=True)
                        errors.append(error_msg)

            logger.info(
                f"✅ [MONITOR] Processados {processed}/{len(object_changes)} do device {device_id}"
            )

            return {
                "success": len(errors) == 0,
                "device_id": device_id,
                "total_changes": len(object_changes),
                "processed": processed,
                "errors": errors if errors else None,
                "results": results,
            }

        except Exception as e:
            logger.error(
                f"❌ [MONITOR] Erro geral processando notificação: {e}", exc_info=True
            )
            return {"success": False, "error": str(e), "processed": 0}

    def _process_single_change(
        self,
        device_id: int,
        change: Dict[str, Any],
        raw_notification: Dict[str, Any],
        sentido: str | None = None,
    ) -> Dict[str, Any]:
        """
        Processa uma única mudança de objeto

        Args:
            device_id: ID do dispositivo
            change: Dict com object, type e values

        Returns:
            dict: Resultado do processamento
        """
        object_type = change.get("object")
        change_type = change.get("type")  # inserted, updated, deleted
        values = change.get("values", {})

        if not object_type:
            return {"success": False, "error": "object é obrigatório"}

        if not change_type:
            return {"success": False, "error": "type é obrigatório"}

        handler = self.handlers.get(object_type)

        if not handler:
            logger.warning(f"⚠️ [MONITOR] Tipo de objeto não suportado: {object_type}")
            return {
                "success": False,
                "object": object_type,
                "error": f"Tipo de objeto não suportado: {object_type}",
            }

        logger.debug(f"🔄 [MONITOR] Processando {object_type} - {change_type}")

        return handler(
            device_id,
            change_type,
            values,
            raw_notification=raw_notification,
            raw_change=change,
            sentido=sentido,
        )

    @staticmethod
    def _parse_device_unix_timestamp(time_unix: Any) -> datetime:
        from django.utils import timezone

        if time_unix in (None, ""):
            return timezone.now()

        # A Control iD desta instalacao envia o "unix timestamp" no horario local
        # da catraca (UTC-3), e nao como epoch UTC absoluto. Por isso tratamos o
        # valor como uma data/hora local de Sao Paulo e depois a tornamos aware.
        naive_local = datetime.fromtimestamp(
            int(time_unix),
            tz=dt_timezone.utc,
        ).replace(tzinfo=None)
        return timezone.make_aware(naive_local, DEVICE_LOCAL_TIMEZONE)

    def _handle_access_log(
        self,
        device_id: int,
        change_type: str,
        values: Dict[str, Any],
        raw_notification: Dict[str, Any] | None = None,
        raw_change: Dict[str, Any] | None = None,
        sentido: str | None = None,
    ) -> Dict[str, Any]:
        """
        Processa mudanças em access_logs

        Campos principais:
        - id: ID único do log
        - time: Timestamp Unix
        - event: Código do evento (12=acesso liberado, etc)
        - device_id: ID do dispositivo
        - user_id: ID do usuário
        - portal_id: ID do portal (lado da catraca)
        - card_value: Valor do cartão RFID
        """
        from src.core.control_id.infra.control_id_django_app.models import (
            AccessLogs,
            Device,
            Portal,
            AccessRule,
        )
        from src.core.user.infra.user_django_app.models import User

        try:
            # ── Resolve o device ──
            # O device_id do payload é o ID interno da catraca (ex: 478435),
            # que NÃO necessariamente é o id do Model Device no Django.
            # Tentamos: 1) por id direto  2) via MonitorConfig  3) device padrão
            device = Device.objects.filter(id=device_id).first()

            if not device:
                # Tenta encontrar via MonitorConfig (a catraca pode ter um device_id diferente)
                from .models import MonitorConfig

                monitor_cfg = MonitorConfig.objects.select_related("device").first()
                if monitor_cfg:
                    device = monitor_cfg.device
                    logger.info(
                        f"🔄 [ACCESS_LOG] device_id={device_id} não encontrado direto, "
                        f"usando device do MonitorConfig: {device.name} (id={device.id})"  # type: ignore[attr-defined]
                    )

            if not device:
                # Fallback: usa o device padrão ou o primeiro ativo
                device = Device.objects.filter(is_default=True).first()
                if not device:
                    device = Device.objects.filter(is_active=True).first()
                if device:
                    logger.info(
                        f"🔄 [ACCESS_LOG] device_id={device_id} não encontrado, "
                        f"usando fallback: {device.name} (id={device.id})"  # type: ignore[attr-defined]
                    )

            if not device:
                logger.error(
                    f"❌ [ACCESS_LOG] Nenhum device encontrado para device_id={device_id}"
                )
                return {
                    "success": False,
                    "object": "access_logs",
                    "error": f"Device {device_id} não encontrado e sem fallback disponível",
                }

            log_id = values.get("id")
            time_unix = values.get("time")
            event = values.get("event")

            # ── Resolve portal ──
            # A catraca pode enviar portal_id ou door_id
            portal = None
            portal_id = values.get("portal_id") or values.get("door_id")
            if portal_id is not None:
                try:
                    portal_id_int = int(portal_id)
                    if portal_id_int > 0:
                        portal = Portal.objects.filter(id=portal_id_int).first()
                        if not portal:
                            logger.warning(
                                f"⚠️ [ACCESS_LOG] Portal id={portal_id_int} não existe no banco"
                            )
                except (ValueError, TypeError):
                    logger.warning(f"⚠️ [ACCESS_LOG] portal_id inválido: {portal_id}")

            # ── Resolve user ──
            user = None
            user_id = values.get("user_id")
            if user_id is not None:
                try:
                    user_id_int = int(user_id)
                    if user_id_int > 0:
                        user = User.objects.filter(id=user_id_int).first()
                except (ValueError, TypeError):
                    pass

            # ── Resolve access_rule ──
            access_rule = None
            rule_id = (
                values.get("access_rule_id")
                or values.get("identification_rule_id")
                or values.get("access_rule")
            )
            if rule_id is not None:
                try:
                    rule_id_int = int(rule_id)
                    if rule_id_int > 0:
                        access_rule = AccessRule.objects.filter(id=rule_id_int).first()
                except (ValueError, TypeError):
                    pass

            # Log detalhado dos valores recebidos para debug
            logger.info(f"📋 [ACCESS_LOG] RAW values da catraca: {values}")
            logger.info(
                f"📋 [ACCESS_LOG] Resolução: log_id={log_id}, event={event}, "
                f"device_catraca_id={device_id}→device_django={device.name}(id={device.pk}), "  # type: ignore[attr-defined]
                f"portal_id={portal_id}→portal={'SIM (' + portal.name + ', id=' + str(portal.pk) + ')' if portal else 'NÃO ENCONTRADO'}, "
                f"user_id={user_id}→user={user.name + '(id=' + str(user.pk) + ')' if user else 'N/A'}, "
                f"rule_id={rule_id}→rule={'SIM (' + access_rule.name + ')' if access_rule else 'N/A'}"
            )

            if change_type == "inserted":
                # Converte timestamp Unix para datetime
                # A catraca envia timestamps no fuso horário local (UTC-3),
                # então precisamos tratá-los como tal para evitar conversão indevida
                timestamp = self._parse_device_unix_timestamp(time_unix)

                # Cria ou atualiza o log
                # Lookup: device + identifier_id + time
                # O time no lookup evita colisão quando a catraca
                # limpa seus logs internos e reinicia a contagem de IDs
                log, created = AccessLogs.objects.update_or_create(
                    device=device,
                    identifier_id=str(log_id),
                    time=timestamp,
                    defaults={
                        "event_type": int(event) if event else 10,
                        "user": user,
                        "portal": portal,
                        "access_rule": access_rule,
                        "card_value": values.get("card_value", ""),
                        "qr_code": values.get("qr_code")
                        or values.get("qrcode_value", ""),
                        "uhf_value": values.get("uhf_value")
                        or values.get("uhf_tag", ""),
                        "pin_value": values.get("pin_value", ""),
                        "confidence": values.get("confidence", 0),
                        "mask": values.get("mask", ""),
                        "sentido": sentido or "",
                        "raw_payload": {
                            "source": "dao_notification",
                            "device_id": device_id,
                            "change_type": change_type,
                            "change": deepcopy(raw_change or {}),
                            "notification": deepcopy(raw_notification or {}),
                        },
                    },
                )

                logger.info(
                    f"✅ [ACCESS_LOG] {'Criado' if created else 'Já existia'} log {log_id} do device {device.name}"
                )

                # ── Atualiza ultima passagem do usuario ──
                if created and user:
                    User.objects.filter(id=user.id).update(last_passage_at=timestamp)  # type: ignore[attr-defined]

                # ── Verificação de acesso: loga o MOTIVO no console ──
                if created:
                    try:
                        access_verifier.analyze_access(
                            user_id=user.id if user else None,  # type: ignore[attr-defined]
                            portal_id=portal.id if portal else None,  # type: ignore[attr-defined]
                            event_type=int(event) if event else 0,
                            access_rule_id=access_rule.id if access_rule else None,  # type: ignore[attr-defined]
                            device_name=device.name,
                            access_time=timestamp,
                            device=device,
                        )
                    except Exception as verify_err:
                        logger.warning(
                            f"⚠️ [ACCESS_VERIFY] Erro na verificação de acesso: {verify_err}",
                            exc_info=True,
                        )

                return {
                    "success": True,
                    "object": "access_logs",
                    "action": "created" if created else "already_exists",
                    "log_id": log_id,
                    "device": device.name,
                }

            elif change_type == "updated":
                # Atualiza log existente — ou cria se não existir
                # A catraca pode enviar "updated" mesmo na primeira vez
                # (ex: quando o log é gerado internamente e enviado como update)
                # A catraca envia timestamps no fuso horário local (UTC-3),
                # então precisamos tratá-los como tal para evitar conversão indevida
                timestamp = self._parse_device_unix_timestamp(time_unix)

                # Lookup: device + identifier_id + time
                # O time no lookup evita colisão quando a catraca
                # limpa seus logs internos e reinicia a contagem de IDs
                log, created = AccessLogs.objects.update_or_create(
                    device=device,
                    identifier_id=str(log_id),
                    time=timestamp,
                    defaults={
                        "event_type": int(event) if event else 10,
                        "user": user,
                        "portal": portal,
                        "access_rule": access_rule,
                        "card_value": values.get("card_value", ""),
                        "qr_code": values.get("qr_code")
                        or values.get("qrcode_value", ""),
                        "uhf_value": values.get("uhf_value")
                        or values.get("uhf_tag", ""),
                        "pin_value": values.get("pin_value", ""),
                        "confidence": values.get("confidence", 0),
                        "mask": values.get("mask", ""),
                        "sentido": sentido or "",
                        "raw_payload": {
                            "source": "dao_notification",
                            "device_id": device_id,
                            "change_type": change_type,
                            "change": deepcopy(raw_change or {}),
                            "notification": deepcopy(raw_notification or {}),
                        },
                    },
                )

                action_label = "created (via updated)" if created else "updated"
                logger.info(
                    f"✅ [ACCESS_LOG] {action_label} log {log_id} do device {device.name}"
                )

                # Se foi criado agora, roda a verificação de acesso
                if created:
                    try:
                        access_verifier.analyze_access(
                            user_id=user.pk if user else None,
                            portal_id=portal.pk if portal else None,
                            event_type=int(event) if event else 0,
                            access_rule_id=access_rule.pk if access_rule else None,
                            device_name=device.name,
                            access_time=timestamp,
                            device=device,
                        )
                    except Exception as verify_err:
                        logger.warning(
                            f"⚠️ [ACCESS_VERIFY] Erro na verificação de acesso: {verify_err}",
                            exc_info=True,
                        )

                return {
                    "success": True,
                    "object": "access_logs",
                    "action": action_label,
                    "log_id": log_id,
                }

            elif change_type == "deleted":
                # Remove log
                deleted_count, _ = AccessLogs.objects.filter(
                    device=device, identifier_id=str(log_id)
                ).delete()

                logger.info(
                    f"✅ [ACCESS_LOG] Deletado log {log_id} do device {device.name}"
                )
                return {
                    "success": True,
                    "object": "access_logs",
                    "action": "deleted",
                    "deleted_count": deleted_count,
                }

            else:
                return {
                    "success": False,
                    "object": "access_logs",
                    "error": f"Tipo de mudança desconhecido: {change_type}",
                }

        except Exception as e:
            logger.error(f"❌ [ACCESS_LOG] Erro processando: {e}", exc_info=True)
            return {"success": False, "object": "access_logs", "error": str(e)}

    def _handle_template(
        self, device_id: int, change_type: str, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Processa mudanças em templates (biometria)

        Por enquanto apenas loga, mas pode ser expandido
        """
        logger.info(
            f"📝 [TEMPLATE] {change_type} - Device {device_id} - Template ID {values.get('id')}"
        )

        return {
            "success": True,
            "object": "templates",
            "action": change_type,
            "note": "Template processado (apenas log por enquanto)",
        }

    def _handle_card(
        self, device_id: int, change_type: str, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Processa mudanças em cartões

        Por enquanto apenas loga, mas pode ser expandido
        """
        logger.info(
            f"💳 [CARD] {change_type} - Device {device_id} - Card ID {values.get('id')}"
        )

        return {
            "success": True,
            "object": "cards",
            "action": change_type,
            "note": "Cartão processado (apenas log por enquanto)",
        }

    def _handle_alarm_log(
        self, device_id: int, change_type: str, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Processa mudanças em alarm_logs

        Por enquanto apenas loga, mas pode ser expandido
        """
        logger.info(
            f"🚨 [ALARM] {change_type} - Device {device_id} - Alarm ID {values.get('id')}"
        )

        return {
            "success": True,
            "object": "alarm_logs",
            "action": change_type,
            "note": "Alarme processado (apenas log por enquanto)",
        }


# Instância global para uso nas views
monitor_handler = MonitorNotificationHandler()
