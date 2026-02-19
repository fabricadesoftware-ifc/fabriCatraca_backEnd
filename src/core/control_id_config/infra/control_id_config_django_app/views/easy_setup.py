"""
Easy Setup — Reset e reconfiguração completa de catracas selecionadas.

GET  /api/config/easy-setup/  → Lista devices disponíveis
POST /api/config/easy-setup/  → Executa setup nos devices selecionados

Fluxo por device:
  1. Login
  2. Factory reset (reset_to_factory_default.fcgi, keep_network_info=true)
  3. Aguardar reboot + re-login
  4. Acertar data/hora
  5. Configurar monitor (push notifications)
  6. Enviar configurações do device (local_identification, operation_mode, etc.)
  7. Enviar todos os dados do banco (users, groups, regras, etc.)
  8. Enviar PINs de identificação
"""

import logging
import time as _time

import requests
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from src.core.__seedwork__.infra.catraca_sync import ControlIDSyncMixin
from src.core.control_Id.infra.control_id_django_app.models import (
    AccessRule,
    AccessRuleTimeZone,
    Area,
    Card,
    CustomGroup,
    Device,
    GroupAccessRule,
    Portal,
    PortalAccessRule,
    Template,
    TimeSpan,
    TimeZone,
    UserAccessRule,
    UserGroup,
)
from src.core.control_id_config.infra.control_id_config_django_app.models import (
    CatraConfig,
    HardwareConfig,
    PushServerConfig,
    SecurityConfig,
    SystemConfig,
    UIConfig,
)
from src.core.control_id_monitor.infra.control_id_monitor_django_app.models import (
    MonitorConfig,
)
from src.core.user.infra.user_django_app.models import User

logger = logging.getLogger(__name__)

# ── Credenciais padrão de fábrica da Control iD ────────────────────────────
_FACTORY_LOGIN = "admin"
_FACTORY_PASSWORD = "admin"

# Coluna usada no WHERE de destroy_objects para cada tabela.
# Tabelas de junção NÃO possuem coluna 'id' na Control iD.
_TABLE_WHERE_COL = {
    "user_groups": "user_id",
    "user_access_rules": "user_id",
    "group_access_rules": "group_id",
    "portal_access_rules": "portal_id",
    "access_rule_time_zones": "access_rule_id",
}

# ── Ordem de push (entidades-pai primeiro, relações depois) ─────────────────
PUSH_ORDER = [
    "users",
    "time_zones",
    "time_spans",
    "access_rules",
    "groups",
    "areas",
    "portals",
    "user_groups",
    "user_access_rules",
    "group_access_rules",
    "portal_access_rules",
    "access_rule_time_zones",
    "cards",
    "templates",
    "pins",
]


# ═══════════════════════════════════════════════════════════════════════════════
#  Helper — Motor de setup por device
# ═══════════════════════════════════════════════════════════════════════════════


class _EasySetupEngine(ControlIDSyncMixin):
    """
    Herda ControlIDSyncMixin para reutilizar login, _make_request, etc.
    Opera em UM device por vez (set_device antes de cada uso).
    """

    # ── 1. Factory reset ────────────────────────────────────────────────────
    def factory_reset(self):
        """
        Reseta a catraca para configuração de fábrica mantendo config de rede.
        Usa reset_to_factory_default.fcgi com keep_network_info=true.
        Aguarda reboot e faz login novamente.
        """
        result = {}

        # Enviar comando de factory reset
        try:
            sess = self.login()
            resp = requests.post(
                self.get_url(f"reset_to_factory_default.fcgi?session={sess}"),
                json={"keep_network_info": True},
                timeout=30,
            )
            if resp.status_code != 200:
                return {
                    "ok": False,
                    "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
                }
            result["reset_sent"] = True
        except Exception as e:
            return {"ok": False, "error": f"Erro ao enviar factory reset: {e}"}

        # Invalidar sessão e aguardar reboot
        self.session = None
        logger.info(
            f"[EASY_SETUP] [{self.device.name}] "
            "Factory reset enviado, aguardando reboot (~15s)..."
        )
        _time.sleep(15)

        # Polling até o device voltar online
        credentials_to_try = [
            (self.device.username, self.device.password),
            (_FACTORY_LOGIN, _FACTORY_PASSWORD),
        ]

        for attempt in range(12):
            for login_user, login_pass in credentials_to_try:
                try:
                    resp = requests.post(
                        self.get_url("login.fcgi"),
                        json={"login": login_user, "password": login_pass},
                        timeout=5,
                    )
                    if resp.status_code == 200 and resp.json().get("session"):
                        self.session = resp.json()["session"]
                        used_defaults = (
                            login_user != self.device.username
                            or login_pass != self.device.password
                        )
                        result["ok"] = True
                        result["reboot_attempts"] = attempt + 1
                        if used_defaults:
                            result["used_default_credentials"] = True
                            result["warning"] = (
                                "Factory reset resetou credenciais para admin/admin. "
                                "Atualize username/password do device no Django."
                            )
                        logger.info(
                            f"[EASY_SETUP] [{self.device.name}] "
                            f"Online após reboot (tentativa {attempt + 1})"
                        )
                        return result
                except Exception:
                    pass

            logger.debug(
                f"[EASY_SETUP] [{self.device.name}] "
                f"Tentativa {attempt + 1}/12 — device ainda reiniciando..."
            )
            _time.sleep(5)

        result["ok"] = False
        result["error"] = "Device não voltou após factory reset (timeout ~75s)"
        return result

    # ── 2. Acertar data/hora ────────────────────────────────────────────────
    def set_datetime(self):
        """
        Sincroniza relógio da catraca com o servidor.
        Usa set_system_time.fcgi (endpoint oficial) + habilita NTP UTC-3.
        """
        result = {}

        try:
            now = timezone.localtime()

            # Passo 1 — Setar data/hora manualmente via set_system_time.fcgi
            time_payload = {
                "day": now.day,
                "month": now.month,
                "year": now.year,
                "hour": now.hour,
                "minute": now.minute,
                "second": now.second,
            }
            resp = self._make_request("set_system_time.fcgi", json_data=time_payload)
            result["set_time"] = {
                "ok": resp.status_code == 200,
                "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
            }

            # Passo 2 — Habilitar NTP com fuso horário de Brasília (UTC-3)
            ntp_payload = {
                "ntp": {
                    "enabled": "1",
                    "timezone": "UTC-3",
                }
            }
            ntp_resp = self._make_request(
                "set_configuration.fcgi", json_data=ntp_payload
            )
            result["ntp"] = {
                "ok": ntp_resp.status_code == 200,
                "timezone": "UTC-3",
                "enabled": True,
            }

            result["ok"] = result["set_time"]["ok"]
            return result

        except Exception as e:
            result["ok"] = False
            result["error"] = str(e)
            return result

    # ── 3. Configurar monitor ───────────────────────────────────────────────
    def configure_monitor(self):
        """Envia configuração de monitor (push) para a catraca."""
        try:
            monitor = MonitorConfig.objects.filter(device=self.device).first()
            if not monitor or not monitor.is_configured:
                return {
                    "ok": False,
                    "error": "MonitorConfig não configurado para este device",
                }

            payload = {
                "monitor": {
                    "hostname": str(monitor.hostname or ""),
                    "port": str(monitor.port or ""),
                    "path": str(monitor.path or ""),
                    "request_timeout": str(monitor.request_timeout or 1000),
                }
            }
            resp = self._make_request("set_configuration.fcgi", json_data=payload)
            return {
                "ok": resp.status_code == 200,
                "full_url": monitor.full_url,
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── 4. Enviar configurações do device ───────────────────────────────────
    def configure_device_settings(self):
        """
        Envia TODAS as configurações salvas no banco para a catraca.

        Após factory reset a catraca perde configurações críticas como:
        - general.local_identification (necessário para processar PIN/cartão)
        - catra.operation_mode (modo de operação da gaveta)
        - identifier (MFA, log type)
        - hardware (beep, ssh)
        - push_server
        - general.screen_always_on (UI)

        Monta UM ÚNICO payload consolidado e envia via set_configuration.fcgi.
        """
        device = self.device
        result = {"sections": {}}

        def bool_to_str(value):
            return "1" if value else "0"

        payload = {}

        # ── general (SystemConfig + HardwareConfig + UIConfig) ──
        general = {}

        sys_cfg = SystemConfig.objects.filter(device=device).first()
        if sys_cfg:
            general["catra_timeout"] = str(sys_cfg.catra_timeout or 30000)
            general["online"] = bool_to_str(sys_cfg.online)
            general["local_identification"] = bool_to_str(sys_cfg.local_identification)
            general["language"] = str(sys_cfg.language or "pt_BR")
            result["sections"]["system"] = True
        else:
            # Defaults seguros — local_identification DEVE ser 1
            general["local_identification"] = "1"
            general["online"] = "1"
            general["language"] = "pt_BR"
            result["sections"]["system"] = "defaults"

        hw_cfg = HardwareConfig.objects.filter(device=device).first()
        if hw_cfg:
            general["beep_enabled"] = bool_to_str(hw_cfg.beep_enabled)
            general["ssh_enabled"] = bool_to_str(hw_cfg.ssh_enabled)
            general["bell_enabled"] = bool_to_str(hw_cfg.bell_enabled)
            general["bell_relay"] = str(hw_cfg.bell_relay)
            general["exception_mode"] = "emergency" if hw_cfg.exception_mode else "none"
            result["sections"]["hardware"] = True

        # NOTA: screen_always_on não é suportado pelo firmware IDBLOCK
        # (causa "Node or attribute not found"), então não é enviado aqui.

        if general:
            payload["general"] = general

        # ── catra (CatraConfig) ──
        catra_cfg = CatraConfig.objects.filter(device=device).first()
        if catra_cfg:
            payload["catra"] = {
                "anti_passback": bool_to_str(catra_cfg.anti_passback),
                "daily_reset": bool_to_str(catra_cfg.daily_reset),
                "gateway": catra_cfg.gateway,
                "operation_mode": catra_cfg.operation_mode,
            }
            result["sections"]["catra"] = True
        else:
            # Default seguro
            payload["catra"] = {
                "operation_mode": "blocked",
                "anti_passback": "0",
                "daily_reset": "0",
                "gateway": "clockwise",
            }
            result["sections"]["catra"] = "defaults"

        # ── identifier (SecurityConfig + métodos de identificação) ──
        identifier_cfg = {}
        sec_cfg = SecurityConfig.objects.filter(device=device).first()
        if sec_cfg:
            identifier_cfg["multi_factor_authentication"] = bool_to_str(
                getattr(sec_cfg, "multi_factor_authentication_enabled", False)
            )
            identifier_cfg["verbose_logging"] = bool_to_str(
                getattr(sec_cfg, "verbose_logging_enabled", True)
            )
            result["sections"]["security"] = True

        # Métodos de identificação habilitados.
        # PIN e ID+Senha são mutuamente exclusivos:
        #   pin_identification_enabled=1 → modo PIN
        #   pin_identification_enabled=0 → modo ID+Senha
        identifier_cfg.setdefault("card_identification_enabled", "1")
        identifier_cfg.setdefault("pin_identification_enabled", "1")

        payload["identifier"] = identifier_cfg
        result["sections"]["identifier_methods"] = True

        # ── push_server (PushServerConfig) ──
        ps_cfg = PushServerConfig.objects.filter(device=device).first()
        if ps_cfg:
            payload["push_server"] = {
                "push_request_timeout": str(ps_cfg.push_request_timeout),
                "push_request_period": str(ps_cfg.push_request_period),
                "push_remote_address": ps_cfg.push_remote_address or "",
            }
            result["sections"]["push_server"] = True

        # ── Envia tudo de uma vez ──
        try:
            resp = self._make_request("set_configuration.fcgi", json_data=payload)
            result["ok"] = resp.status_code == 200
            result["payload_sections"] = list(payload.keys())
            if resp.status_code != 200:
                result["detail"] = resp.text[:300]
        except Exception as e:
            result["ok"] = False
            result["error"] = str(e)

        return result

    # ── 5. Coletar dados do banco ───────────────────────────────────────────
    def collect_db_data(self):
        """
        Coleta todos os dados do Django DB que precisam ser enviados
        para esta catraca.
        """
        device = self.device

        # Usuários vinculados a este device
        users_qs = User.objects.filter(devices=device).exclude(
            is_staff=True, is_superuser=True
        )
        user_ids = set(users_qs.values_list("id", flat=True))

        data = {}

        # Users
        users_list = []
        pins_list = []
        for u in users_qs:
            payload = {"id": u.id, "name": u.name}
            if u.registration:
                payload["registration"] = u.registration
            if u.user_type_id is not None:
                payload["user_type_id"] = u.user_type_id
            users_list.append(payload)

            if u.pin:
                pins_list.append({"user_id": u.id, "value": u.pin})

        data["users"] = users_list
        data["pins"] = pins_list

        # TimeZones
        data["time_zones"] = list(TimeZone.objects.values("id", "name"))

        # TimeSpans — API Control iD espera 0/1 nos dias, não true/false
        raw_spans = TimeSpan.objects.values(
            "id",
            "time_zone_id",
            "start",
            "end",
            "sun",
            "mon",
            "tue",
            "wed",
            "thu",
            "fri",
            "sat",
            "hol1",
            "hol2",
            "hol3",
        )
        day_fields = (
            "sun",
            "mon",
            "tue",
            "wed",
            "thu",
            "fri",
            "sat",
            "hol1",
            "hol2",
            "hol3",
        )
        data["time_spans"] = [
            {k: (int(v) if k in day_fields else v) for k, v in span.items()}
            for span in raw_spans
        ]

        # AccessRules — type DEVE ser >= 1 (0 causa "Invalid op type" no firmware)
        raw_rules = AccessRule.objects.values("id", "name", "type", "priority")
        data["access_rules"] = [
            {**rule, "type": max(rule["type"], 1)} for rule in raw_rules
        ]

        # Groups
        data["groups"] = list(CustomGroup.objects.values("id", "name"))

        # Areas
        data["areas"] = list(Area.objects.values("id", "name"))

        # Portals
        data["portals"] = list(
            Portal.objects.values("id", "name", "area_from_id", "area_to_id")
        )

        # Relações (filtradas por users deste device onde aplicável)
        data["user_groups"] = list(
            UserGroup.objects.filter(user_id__in=user_ids).values("user_id", "group_id")
        )

        data["user_access_rules"] = list(
            UserAccessRule.objects.filter(user_id__in=user_ids).values(
                "user_id", "access_rule_id"
            )
        )

        data["group_access_rules"] = list(
            GroupAccessRule.objects.values("group_id", "access_rule_id")
        )

        data["portal_access_rules"] = list(
            PortalAccessRule.objects.values("portal_id", "access_rule_id")
        )

        data["access_rule_time_zones"] = list(
            AccessRuleTimeZone.objects.values("access_rule_id", "time_zone_id")
        )

        # Cards
        data["cards"] = list(
            Card.objects.filter(user_id__in=user_ids).values("user_id", "value")
        )

        # Templates (biometria)
        data["templates"] = list(
            Template.objects.filter(user_id__in=user_ids).values("user_id", "template")
        )

        return data

    # ── 6. Enviar dados para catraca ────────────────────────────────────────
    def _destroy_table(self, table):
        """Limpa uma tabela da catraca antes de inserir novos dados."""
        col = _TABLE_WHERE_COL.get(table, "id")
        where = {table: {col: {">=": 0}}}
        try:
            sess = self.login()
            resp = requests.post(
                self.get_url(f"destroy_objects.fcgi?session={sess}"),
                json={"object": table, "where": where},
                timeout=30,
            )
            if resp.status_code != 200:
                logger.warning(
                    f"[EASY_SETUP] destroy_objects({table}) falhou: "
                    f"HTTP {resp.status_code} — {resp.text[:300]}"
                )
            else:
                logger.debug(
                    f"[EASY_SETUP] destroy_objects({table}) OK — {resp.text[:100]}"
                )
            return resp.status_code == 200
        except Exception as exc:
            logger.warning(
                f"[EASY_SETUP] destroy_objects({table}) exception: {exc}"
            )
            return False

    def push_data(self, data):
        """
        Envia os dados coletados para a catraca na ordem correta de FK.

        Duas fases:
          1. DESTROY ALL em ordem reversa (junction → parent) — respeita FK
          2. CREATE ALL em ordem direta (parent → junction)

        Isso garante que factory defaults (como access_rule type=0)
        sejam removidos mesmo quando há FK entre tabelas.
        """
        results = {}

        # ── Fase 1: Destroy ALL em ordem reversa de FK ──────────────────
        logger.info(f"[EASY_SETUP] [{self.device.name}] Fase 1 — destroy (reverse)...")
        for table in reversed(PUSH_ORDER):
            self._destroy_table(table)

        # ── Fase 2: Create em ordem direta de FK ────────────────────────
        logger.info(f"[EASY_SETUP] [{self.device.name}] Fase 2 — create (forward)...")
        for table in PUSH_ORDER:
            values = data.get(table, [])
            if not values:
                results[table] = {"ok": True, "count": 0, "skipped": True}
                continue

            try:
                sess = self.login()
                resp = requests.post(
                    self.get_url(f"create_objects.fcgi?session={sess}"),
                    json={"object": table, "values": values},
                    timeout=60,
                )
                results[table] = {
                    "ok": resp.status_code == 200,
                    "count": len(values),
                    "status": resp.status_code,
                }
                if resp.status_code != 200:
                    body = resp.text[:500]
                    results[table]["detail"] = body
                    logger.warning(
                        f"[EASY_SETUP] create_objects({table}) falhou: "
                        f"HTTP {resp.status_code} — {body}"
                    )
            except Exception as e:
                results[table] = {
                    "ok": False,
                    "count": len(values),
                    "error": str(e),
                }

        return results

    # ── Orquestrador completo ───────────────────────────────────────────────
    def run_full_setup(self):
        """
        Executa o setup completo num único device.
        Retorna dict com resultado de cada etapa.
        """
        report = {"device": self.device.name, "steps": {}}
        t0 = _time.monotonic()

        # Etapa 1 — Login
        try:
            self.login(force_new=True)
            report["steps"]["login"] = {"ok": True}
        except Exception as e:
            report["steps"]["login"] = {"ok": False, "error": str(e)}
            report["elapsed_s"] = round(_time.monotonic() - t0, 2)
            return report

        # Etapa 2 — Factory reset (mantém rede)
        logger.info(
            f"[EASY_SETUP] [{self.device.name}] Factory reset (keep_network)..."
        )
        report["steps"]["factory_reset"] = self.factory_reset()
        if not report["steps"]["factory_reset"].get("ok"):
            logger.error(
                f"[EASY_SETUP] [{self.device.name}] Factory reset FALHOU — abortando"
            )
            report["elapsed_s"] = round(_time.monotonic() - t0, 2)
            return report

        # Etapa 3 — Acertar data/hora
        logger.info(f"[EASY_SETUP] [{self.device.name}] Acertando relógio...")
        report["steps"]["datetime"] = self.set_datetime()

        # Etapa 4 — Configurar monitor
        logger.info(f"[EASY_SETUP] [{self.device.name}] Configurando monitor...")
        report["steps"]["monitor"] = self.configure_monitor()

        # Etapa 5 — Enviar configurações do device (local_identification, operation_mode, etc.)
        logger.info(f"[EASY_SETUP] [{self.device.name}] Enviando configurações...")
        report["steps"]["device_settings"] = self.configure_device_settings()

        # Etapa 6 — Coletar e enviar dados
        logger.info(f"[EASY_SETUP] [{self.device.name}] Coletando dados do DB...")
        db_data = self.collect_db_data()

        logger.info(f"[EASY_SETUP] [{self.device.name}] Enviando dados para catraca...")
        report["steps"]["push"] = self.push_data(db_data)

        report["elapsed_s"] = round(_time.monotonic() - t0, 2)

        # Resumo rápido
        push = report["steps"]["push"]
        total_pushed = sum(v.get("count", 0) for v in push.values() if v.get("ok"))
        total_errors = sum(
            1 for v in push.values() if not v.get("ok") and not v.get("skipped")
        )
        report["summary"] = {
            "records_pushed": total_pushed,
            "tables_with_errors": total_errors,
        }

        return report


# ═══════════════════════════════════════════════════════════════════════════════
#  Views
# ═══════════════════════════════════════════════════════════════════════════════


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def easy_setup(request):
    """
    GET  → Lista devices disponíveis para setup.
    POST → Executa reset + reconfiguração nos devices selecionados.
           Body: {"device_ids": [1, 2, 3]}  (todos se omitido)
    """
    if request.method == "GET":
        return _list_devices(request)
    return _execute_setup(request)


def _list_devices(request):
    """Retorna devices ativos com informações úteis para o frontend."""
    devices = Device.objects.filter(is_active=True).order_by("name")
    device_list = []

    for d in devices:
        monitor = MonitorConfig.objects.filter(device=d).first()
        user_count = d.users.exclude(is_staff=True, is_superuser=True).count()

        device_list.append(
            {
                "id": d.id,
                "name": d.name,
                "ip": d.ip,
                "is_default": d.is_default,
                "user_count": user_count,
                "monitor_configured": monitor.is_configured if monitor else False,
                "monitor_url": monitor.full_url
                if monitor and monitor.is_configured
                else None,
                "selected": True,  # Por padrão todas marcadas
            }
        )

    return Response(
        {
            "devices": device_list,
            "total": len(device_list),
            "hint": 'POST com {"device_ids": [1,2]} para executar o setup. '
            "Omita device_ids para executar em todos.",
        }
    )


def _execute_setup(request):
    """Executa o Easy Setup nos devices selecionados."""
    device_ids = request.data.get("device_ids")

    if device_ids:
        devices = Device.objects.filter(id__in=device_ids, is_active=True)
        missing = set(device_ids) - set(devices.values_list("id", flat=True))
        if missing:
            return Response(
                {
                    "error": f"Devices não encontrados ou inativos: {list(missing)}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
    else:
        devices = Device.objects.filter(is_active=True)

    if not devices.exists():
        return Response(
            {"error": "Nenhuma catraca ativa encontrada"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    engine = _EasySetupEngine()
    results = []

    for device in devices:
        logger.info(
            f"[EASY_SETUP] ═══ Iniciando setup: {device.name} ({device.ip}) ═══"
        )
        engine.set_device(device)
        report = engine.run_full_setup()
        results.append(report)
        logger.info(
            f"[EASY_SETUP] ═══ Concluído: {device.name} em {report.get('elapsed_s', '?')}s ═══"
        )

    # Resumo geral
    total_ok = sum(1 for r in results if r.get("steps", {}).get("login", {}).get("ok"))

    return Response(
        {
            "success": True,
            "message": f"Easy Setup concluído em {len(results)} device(s)",
            "devices_ok": total_ok,
            "devices_total": len(results),
            "results": results,
        }
    )
