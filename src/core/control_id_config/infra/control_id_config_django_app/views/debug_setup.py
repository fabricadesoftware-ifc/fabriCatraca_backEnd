"""
Debug Setup — Envia etapas INDIVIDUAIS para a catraca para diagnóstico.

POST /api/control_id_config/debug-setup/

Uso:
  A catraca DEVE estar de fábrica (já resetada manualmente).
  Envie cada passo isoladamente e teste a catraca entre passos.

Body (JSON):
  {
    "device_id": 1,
    "step": "nome_do_passo"
  }

Passos disponíveis (enviar um de cada vez, testar a catraca entre cada):

  ── Dados (push individual) ──────────────────────────────────
  "push_users"                → Cria apenas users
  "push_time_zones"           → Cria apenas time_zones
  "push_time_spans"           → Cria apenas time_spans
  "push_access_rules"         → Cria apenas access_rules (type≥1)
  "push_groups"               → Cria apenas groups
  "push_areas"                → Cria apenas areas
  "push_portals"              → Cria apenas portals
  "push_user_groups"          → Cria relação user↔group
  "push_user_access_rules"    → Cria relação user↔access_rule
  "push_group_access_rules"   → Cria relação group↔access_rule
  "push_portal_access_rules"  → Cria relação portal↔access_rule
  "push_access_rule_time_zones" → Cria relação access_rule↔time_zone
  "push_cards"                → Cria cards
  "push_templates"            → Cria templates (biometria)
  "push_pins"                 → Cria PINs

  ── Configurações (uma de cada vez) ──────────────────────────
  "config_general"            → set_configuration seção general
  "config_catra"              → set_configuration seção catra
  "config_identifier"         → set_configuration seção identifier
  "config_push_server"        → set_configuration seção push_server
  "config_all"                → Todas as configs de uma vez (configure_device_settings)

  ── Utilitários ──────────────────────────────────────────────
  "disable_identifier"        → Desabilita pin/card (pin=0, card=0)
  "set_datetime"              → Acerta relógio + NTP
  "configure_monitor"         → Configura push notifications
  "read_access_rules"         → Lê access_rules atuais da catraca (apenas leitura)
  "read_config"               → Lê configuração atual da catraca (apenas leitura)
  "read_users"                → Lê users atuais da catraca (apenas leitura)
  "list_steps"                → Lista todos os passos disponíveis

  ── Combo (push tudo de uma vez, sem configs) ────────────────
  "push_all_data"             → Destroy + create TODOS os dados (sem tocar configs)
"""

import logging
import time as _time

import requests
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from src.core.control_Id.infra.control_id_django_app.models import Device
from .easy_setup import _EasySetupEngine, PUSH_ORDER

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  Mapa de passos disponíveis
# ═══════════════════════════════════════════════════════════════════════════════

AVAILABLE_STEPS = {
    # Push individual de dados
    "push_users": "Cria apenas users na catraca",
    "push_time_zones": "Cria apenas time_zones",
    "push_time_spans": "Cria apenas time_spans",
    "push_access_rules": "Cria apenas access_rules (type≥1)",
    "push_groups": "Cria apenas groups",
    "push_areas": "Cria apenas areas",
    "push_portals": "Cria apenas portals",
    "push_user_groups": "Cria relação user↔group",
    "push_user_access_rules": "Cria relação user↔access_rule",
    "push_group_access_rules": "Cria relação group↔access_rule",
    "push_portal_access_rules": "Cria relação portal↔access_rule",
    "push_access_rule_time_zones": "Cria relação access_rule↔time_zone",
    "push_cards": "Cria cards (cartões RFID)",
    "push_templates": "Cria templates (biometria)",
    "push_pins": "Cria PINs dos usuários",
    # Configurações
    "config_general": "Envia seção 'general' (local_identification, language, etc.)",
    "config_catra": "Envia seção 'catra' (operation_mode, anti_passback, etc.)",
    "config_identifier": "Envia seção 'identifier' (pin_enabled, card_enabled, mfa, etc.)",
    "config_push_server": "Envia seção 'push_server'",
    "config_all": "Envia TODAS as configurações de uma vez",
    # Destroy individual (apaga UMA tabela)
    "destroy_users": "APAGA todos os users da catraca",
    "destroy_time_zones": "APAGA todos os time_zones",
    "destroy_time_spans": "APAGA todos os time_spans",
    "destroy_access_rules": "APAGA todos os access_rules",
    "destroy_groups": "APAGA todos os groups (⚠️ SUSPEITO)",
    "destroy_areas": "APAGA todos os areas",
    "destroy_portals": "APAGA todos os portals",
    "destroy_user_groups": "APAGA relações user↔group",
    "destroy_user_access_rules": "APAGA relações user↔access_rule",
    "destroy_group_access_rules": "APAGA relações group↔access_rule",
    "destroy_portal_access_rules": "APAGA relações portal↔access_rule",
    "destroy_access_rule_time_zones": "APAGA relações access_rule↔time_zone",
    "destroy_cards": "APAGA todos os cards",
    "destroy_templates": "APAGA todos os templates",
    "destroy_pins": "APAGA todos os pins",
    # Utilitários
    "disable_identifier": "Desabilita pin/card (seta ambos para 0)",
    "set_datetime": "Acerta relógio + configura NTP",
    "configure_monitor": "Configura monitor (push notifications)",
    "read_access_rules": "Lê access_rules atuais da catraca (somente leitura)",
    "read_config": "Lê TODA a configuração atual da catraca (somente leitura)",
    "read_users": "Lê users atuais da catraca (somente leitura)",
    "read_all": "Lê TODOS os dados da catraca (users, groups, rules, etc.)",
    "list_steps": "Lista todos os passos disponíveis",
    # Combo
    "push_all_data": "Destroy + create TODOS os dados (sem tocar em configs)",
    "push_safe": "Push SEGURO: corrige type=0, destroi apenas juncoes, cria por cima",
    # Preview (apenas mostra o que seria enviado, SEM enviar)
    "preview_db_data": "Mostra TODOS os dados que seriam enviados (sem enviar nada)",
    # Fix
    "fix_access_rules": "Corrige access_rules type=0 para type=1 (sem destruir nada)",
}


# ═══════════════════════════════════════════════════════════════════════════════
#  Engine de Debug — extende _EasySetupEngine
# ═══════════════════════════════════════════════════════════════════════════════


class _DebugSetupEngine(_EasySetupEngine):
    """
    Extende o engine do Easy Setup com métodos individuais para debug.
    """

    # ── Push individual de uma tabela ─────────────────────────────────────
    def push_single_table(self, table, data):
        """
        Envia dados de UMA tabela específica para a catraca.
        NÃO faz destroy — apenas create.
        """
        values = data.get(table, [])
        if not values:
            return {
                "ok": True,
                "table": table,
                "count": 0,
                "skipped": True,
                "message": f"Nenhum dado para '{table}' no banco",
            }

        try:
            sess = self.login()
            resp = requests.post(
                self.get_url(f"create_objects.fcgi?session={sess}"),
                json={"object": table, "values": values},
                timeout=60,
            )
            result = {
                "ok": resp.status_code == 200,
                "table": table,
                "count": len(values),
                "status_code": resp.status_code,
                "values_sent": values,
            }
            if resp.status_code == 200:
                result["response"] = resp.json()
            else:
                result["detail"] = resp.text[:500]
            return result
        except Exception as e:
            return {
                "ok": False,
                "table": table,
                "count": len(values),
                "error": str(e),
            }

    # ── Ler objetos da catraca ────────────────────────────────────────────
    def read_objects(self, table, fields=None):
        """Lê todos os objetos de uma tabela da catraca."""
        try:
            sess = self.login()
            payload = {"object": table}
            if fields:
                payload["fields"] = fields
            resp = requests.post(
                self.get_url(f"load_objects.fcgi?session={sess}"),
                json=payload,
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "ok": True,
                    "table": table,
                    "data": data,
                    "count": len(data.get(table, [])),
                }
            return {
                "ok": False,
                "table": table,
                "status_code": resp.status_code,
                "detail": resp.text[:500],
            }
        except Exception as e:
            return {"ok": False, "table": table, "error": str(e)}

    # ── Ler configuração da catraca ───────────────────────────────────────
    def read_configuration(self, sections=None):
        """Lê configuração atual da catraca."""
        try:
            sess = self.login()

            if sections is None:
                # A API Control iD exige lista de campos por seção
                sections = {
                    "general": [
                        "online",
                        "local_identification",
                        "language",
                        "catra_timeout",
                        "beep_enabled",
                        "ssh_enabled",
                        "bell_enabled",
                        "bell_relay",
                        "exception_mode",
                    ],
                    "identifier": [
                        "pin_identification_enabled",
                        "card_identification_enabled",
                        "multi_factor_authentication",
                        "verbose_logging",
                    ],
                    "catra": [
                        "anti_passback",
                        "daily_reset",
                        "gateway",
                        "operation_mode",
                    ],
                    "push_server": [
                        "push_request_timeout",
                        "push_request_period",
                        "push_remote_address",
                    ],
                    "monitor": [
                        "hostname",
                        "port",
                        "path",
                        "request_timeout",
                    ],
                    "ntp": [
                        "enabled",
                        "timezone",
                    ],
                }

            resp = requests.post(
                self.get_url(f"get_configuration.fcgi?session={sess}"),
                json=sections,
                timeout=30,
            )
            if resp.status_code == 200:
                return {"ok": True, "config": resp.json()}
            return {
                "ok": False,
                "status_code": resp.status_code,
                "detail": resp.text[:500],
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── Enviar config individual por seção ────────────────────────────────
    def send_config_section(self, section_name):
        """
        Monta e envia apenas UMA seção de configuração.
        Retorna payload enviado + resposta da catraca.
        """
        device = self.device
        payload = {}

        def bool_to_str(value):
            return "1" if value else "0"

        from src.core.control_id_config.infra.control_id_config_django_app.models import (
            CatraConfig,
            HardwareConfig,
            PushServerConfig,
            SecurityConfig,
            SystemConfig,
        )

        if section_name == "general":
            general = {}
            sys_cfg = SystemConfig.objects.filter(device=device).first()
            if sys_cfg:
                general["catra_timeout"] = str(sys_cfg.catra_timeout or 30000)
                general["online"] = bool_to_str(sys_cfg.online)
                general["local_identification"] = bool_to_str(
                    sys_cfg.local_identification
                )
                general["language"] = str(sys_cfg.language or "pt_BR")
            else:
                general["local_identification"] = "1"
                general["online"] = "1"
                general["language"] = "pt_BR"

            hw_cfg = HardwareConfig.objects.filter(device=device).first()
            if hw_cfg:
                general["beep_enabled"] = bool_to_str(hw_cfg.beep_enabled)
                general["ssh_enabled"] = bool_to_str(hw_cfg.ssh_enabled)
                general["bell_enabled"] = bool_to_str(hw_cfg.bell_enabled)
                general["bell_relay"] = str(hw_cfg.bell_relay)
                general["exception_mode"] = (
                    "emergency" if hw_cfg.exception_mode else "none"
                )

            payload["general"] = general

        elif section_name == "catra":
            catra_cfg = CatraConfig.objects.filter(device=device).first()
            if catra_cfg:
                payload["catra"] = {
                    "anti_passback": bool_to_str(catra_cfg.anti_passback),
                    "daily_reset": bool_to_str(catra_cfg.daily_reset),
                    "gateway": catra_cfg.gateway,
                    "operation_mode": catra_cfg.operation_mode,
                }
            else:
                payload["catra"] = {
                    "operation_mode": "blocked",
                    "anti_passback": "0",
                    "daily_reset": "0",
                    "gateway": "clockwise",
                }

        elif section_name == "identifier":
            identifier_cfg = {}
            sec_cfg = SecurityConfig.objects.filter(device=device).first()
            if sec_cfg:
                identifier_cfg["multi_factor_authentication"] = bool_to_str(
                    getattr(sec_cfg, "multi_factor_authentication_enabled", False)
                )
                identifier_cfg["verbose_logging"] = bool_to_str(
                    getattr(sec_cfg, "verbose_logging_enabled", True)
                )
                identifier_cfg["log_type"] = str(getattr(sec_cfg, "log_type", 1))
            identifier_cfg.setdefault("card_identification_enabled", "1")
            identifier_cfg.setdefault("pin_identification_enabled", "1")
            payload["identifier"] = identifier_cfg

        elif section_name == "push_server":
            ps_cfg = PushServerConfig.objects.filter(device=device).first()
            if ps_cfg:
                payload["push_server"] = {
                    "push_request_timeout": str(ps_cfg.push_request_timeout),
                    "push_request_period": str(ps_cfg.push_request_period),
                    "push_remote_address": ps_cfg.push_remote_address or "",
                }
            else:
                return {
                    "ok": True,
                    "section": section_name,
                    "skipped": True,
                    "message": "PushServerConfig não encontrado no banco",
                }

        else:
            return {
                "ok": False,
                "error": f"Seção desconhecida: {section_name}",
            }

        # Enviar
        try:
            resp = self._make_request("set_configuration.fcgi", json_data=payload)
            result = {
                "ok": resp.status_code == 200,
                "section": section_name,
                "payload_sent": payload,
                "status_code": resp.status_code,
            }
            if resp.status_code == 200:
                result["response"] = resp.json()
            else:
                result["detail"] = resp.text[:500]
            return result
        except Exception as e:
            return {
                "ok": False,
                "section": section_name,
                "payload_sent": payload,
                "error": str(e),
            }


# ═══════════════════════════════════════════════════════════════════════════════
#  View principal
# ═══════════════════════════════════════════════════════════════════════════════


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def debug_setup(request):
    """
    GET  → Lista passos disponíveis com descrições.
    POST → Executa UM passo específico na catraca.
           Body: {"device_id": 1, "step": "push_users"}
    """
    if request.method == "GET":
        return Response(
            {
                "info": "Debug Setup — envie passos individuais para a catraca",
                "usage": 'POST com {"device_id": <id>, "step": "<nome_do_passo>"}',
                "available_steps": AVAILABLE_STEPS,
                "workflow_sugerido": [
                    "1. read_config       → Ver config atual (fábrica)",
                    "2. read_access_rules → Ver rules (deve ter 1 rule type=0 padrão)",
                    "3. read_users        → Ver users (deve ter user teste)",
                    "4. push_users        → Testar catraca ✋",
                    "5. push_groups       → Testar catraca ✋",
                    "6. push_time_zones   → Testar catraca ✋",
                    "7. push_time_spans   → Testar catraca ✋",
                    "8. push_access_rules → Testar catraca ✋ ⚠️ SUSPEITO",
                    "9. push_areas        → Testar catraca ✋",
                    "10. push_portals     → Testar catraca ✋",
                    "11. push_user_groups → Testar catraca ✋",
                    "12. push_user_access_rules   → Testar catraca ✋",
                    "13. push_group_access_rules  → Testar catraca ✋",
                    "14. push_portal_access_rules → Testar catraca ✋",
                    "15. push_access_rule_time_zones → Testar catraca ✋",
                    "16. push_cards       → Testar catraca ✋",
                    "17. push_pins        → Testar catraca ✋",
                    "18. config_general   → Testar catraca ✋ ⚠️ SUSPEITO",
                    "19. config_catra     → Testar catraca ✋ ⚠️ SUSPEITO",
                    "20. config_identifier → Testar catraca ✋ ⚠️ SUSPEITO",
                    "21. config_push_server → Testar catraca ✋",
                ],
                "dica": "Envie UM passo, teste a catraca manualmente. "
                "Se ainda funcionar, envie o próximo. "
                "Quando quebrar, você achou o culpado!",
            }
        )

    # POST — Executar passo
    device_id = request.data.get("device_id")
    step = request.data.get("step")

    if not device_id:
        return Response(
            {"error": "device_id é obrigatório"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not step:
        return Response(
            {"error": "step é obrigatório", "available_steps": list(AVAILABLE_STEPS.keys())},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if step == "list_steps":
        return Response({"available_steps": AVAILABLE_STEPS})

    if step not in AVAILABLE_STEPS:
        return Response(
            {
                "error": f"Step desconhecido: '{step}'",
                "available_steps": list(AVAILABLE_STEPS.keys()),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Buscar device
    try:
        device = Device.objects.get(id=device_id, is_active=True)
    except Device.DoesNotExist:
        return Response(
            {"error": f"Device {device_id} não encontrado ou inativo"},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Criar engine e executar
    engine = _DebugSetupEngine()
    engine.set_device(device)

    logger.info(
        f"[DEBUG_SETUP] ═══ Executando step '{step}' em {device.name} ({device.ip}) ═══"
    )

    try:
        # Login primeiro
        engine.login(force_new=True)
    except Exception as e:
        return Response(
            {"error": f"Falha no login: {e}", "device": device.name},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    t0 = _time.monotonic()

    # ── Executar o passo solicitado ───────────────────────────────────────

    # Coleta dados do banco (necessário para push_*)
    db_data = None
    if step.startswith("push_"):
        db_data = engine.collect_db_data()

    result = _execute_step(engine, step, db_data)
    elapsed = round(_time.monotonic() - t0, 2)

    logger.info(
        f"[DEBUG_SETUP] Step '{step}' concluído em {elapsed}s — "
        f"ok={result.get('ok', '?')}"
    )

    return Response(
        {
            "device": device.name,
            "device_ip": device.ip,
            "step": step,
            "step_description": AVAILABLE_STEPS[step],
            "result": result,
            "elapsed_s": elapsed,
            "next_action": "🔎 Teste a catraca agora! Se funcionar, envie o próximo step.",
        }
    )


def _execute_step(engine, step, db_data=None):
    """Despacha execução para o método correto."""

    # ── Push individual ───────────────────────────────────────────────────
    push_table_map = {
        "push_users": "users",
        "push_time_zones": "time_zones",
        "push_time_spans": "time_spans",
        "push_access_rules": "access_rules",
        "push_groups": "groups",
        "push_areas": "areas",
        "push_portals": "portals",
        "push_user_groups": "user_groups",
        "push_user_access_rules": "user_access_rules",
        "push_group_access_rules": "group_access_rules",
        "push_portal_access_rules": "portal_access_rules",
        "push_access_rule_time_zones": "access_rule_time_zones",
        "push_cards": "cards",
        "push_templates": "templates",
        "push_pins": "pins",
    }

    if step in push_table_map:
        table = push_table_map[step]
        return engine.push_single_table(table, db_data)

    # ── Push all data (destroy + create, sem configs) ─────────────────────
    if step == "push_all_data":
        return engine.push_data(db_data)

    # ── Push safe (nova estratégia: sem destroy de entidades-pai) ────────
    if step == "push_safe":
        return engine.push_data(db_data)

    # ── Fix access_rules type=0 ─────────────────────────────────────────
    if step == "fix_access_rules":
        fixed = engine._fix_default_access_rules()
        return {"ok": True, "fixed": fixed}

    # ── Destroy individual de uma tabela ──────────────────────────────────
    destroy_table_map = {
        "destroy_users": "users",
        "destroy_time_zones": "time_zones",
        "destroy_time_spans": "time_spans",
        "destroy_access_rules": "access_rules",
        "destroy_groups": "groups",
        "destroy_areas": "areas",
        "destroy_portals": "portals",
        "destroy_user_groups": "user_groups",
        "destroy_user_access_rules": "user_access_rules",
        "destroy_group_access_rules": "group_access_rules",
        "destroy_portal_access_rules": "portal_access_rules",
        "destroy_access_rule_time_zones": "access_rule_time_zones",
        "destroy_cards": "cards",
        "destroy_templates": "templates",
        "destroy_pins": "pins",
    }

    if step in destroy_table_map:
        table = destroy_table_map[step]
        ok = engine._destroy_table(table)
        return {"ok": ok, "table": table, "action": "destroy"}

    # ── Configurações individuais ─────────────────────────────────────────
    config_section_map = {
        "config_general": "general",
        "config_catra": "catra",
        "config_identifier": "identifier",
        "config_push_server": "push_server",
    }

    if step in config_section_map:
        section = config_section_map[step]
        return engine.send_config_section(section)

    if step == "config_all":
        return engine.configure_device_settings()

    # ── Utilitários ───────────────────────────────────────────────────────
    if step == "disable_identifier":
        return engine.disable_identifier()

    if step == "set_datetime":
        return engine.set_datetime()

    if step == "configure_monitor":
        return engine.configure_monitor()

    if step == "read_access_rules":
        return engine.read_objects(
            "access_rules", fields=["id", "name", "type", "priority"]
        )

    if step == "read_users":
        return engine.read_objects("users", fields=["id", "name", "registration"])

    if step == "read_config":
        return engine.read_configuration()

    if step == "read_all":
        results = {}
        for table in PUSH_ORDER:
            results[table] = engine.read_objects(table)
        results["config"] = engine.read_configuration()
        return {"ok": True, "data": results}

    if step == "preview_db_data":
        preview_data = engine.collect_db_data()
        summary = {}
        for table in PUSH_ORDER:
            items = preview_data.get(table, [])
            summary[table] = {
                "count": len(items),
                "sample": items[:3] if items else [],
            }
        return {"ok": True, "tables": summary, "full_data": preview_data}

    return {"ok": False, "error": f"Step '{step}' não implementado"}
