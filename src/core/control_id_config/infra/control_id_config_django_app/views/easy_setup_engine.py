"""
Easy Setup Engine — Motor de reset e reconfiguração de catracas.

Contém a classe _EasySetupEngine (herda ControlIDSyncMixin) e
constantes auxiliares usadas pelo setup completo.
"""

import logging
import time as _time
from collections.abc import Iterable, Mapping, Sequence
from datetime import timedelta
from typing import Any, Literal, NotRequired, TypedDict

import requests
from django.utils import timezone

from src.core.__seedwork__.infra.catraca_sync import ControlIDSyncMixin
from src.core.control_id.infra.control_id_django_app.models import (
    AccessRule,
    AccessRuleTimeZone,
    Area,
    Card,
    CustomGroup,
    GroupAccessRule,
    Portal,
    PortalAccessRule,
    Template,
    TimeSpan,
    TimeZone,
    UserAccessRule,
    UserGroup,
)
from src.core.control_id.infra.control_id_django_app.models.device import Device
from src.core.control_id_config.infra.control_id_config_django_app.models import (
    CatraConfig,
    HardwareConfig,
    PushServerConfig,
    SecurityConfig,
    SystemConfig,
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
    "user_roles": "user_id",
    "user_groups": "user_id",
    "user_access_rules": "user_id",
    "group_access_rules": "group_id",
    "portal_access_rules": "portal_id",
    "access_rule_time_zones": "access_rule_id",
}

# ── Ordem de push (entidades-pai primeiro, relações depois) ─────────────────
PUSH_ORDER = [
    "users",
    "user_roles",
    "time_zones",
    "time_spans",
    "access_rules",
    "groups",
    "areas",
    "portals",
    "user_groups",
    "user_access_rules",
    "group_access_rules",
    # ⚠️ access_rule_time_zones DEVE vir ANTES de portal_access_rules!
    # O firmware crasha se um portal é vinculado a uma access_rule que
    # ainda não tem time_zone associado (null reference no firmware).
    "access_rule_time_zones",
    "portal_access_rules",
    "cards",
    "templates",
    "pins",
]

# Tabelas com coluna "id" que suportam upsert (modify_objects).
# Quando já existe um registro com o mesmo ID na catraca (ex: defaults
# criados pelo firmware após factory reset), usa modify_objects para
# ATUALIZAR com os dados corretos do Django DB, em vez de apenas pular.
_UPSERTABLE_TABLES = frozenset(
    {
        "users",
        "time_zones",
        "time_spans",
        "access_rules",
        "groups",
        "areas",
        "portals",
    }
)

_DUPLICATE_ERROR_MARKERS = (
    "unique",
    "constraint",
    "duplicate",
    "already exists",
    "already exist",
    "ja existe",
    "já existe",
)


_CREATE_CHUNK_LADDER = (100, 50, 10, 5, 1)
_MAX_FAILED_ITEM_REPORTS = 20

DevicePayload = dict[str, Any]
PushOperation = Literal["create", "modify", "create_or_modify"]
DuplicateMode = Literal["skip", "modify", "error"]
PushStrategy = Literal["batch", "dynamic_chunks", "create_or_modify", "skipped"]


class ChunkStageReport(TypedDict):
    operation: PushOperation
    chunk_size: int
    chunks: int
    ok_chunks: int
    failed_chunks: int
    records_ok: int
    records_pending: int


class FailedItemReport(TypedDict):
    table: str
    item: DevicePayload
    status: int | None
    detail: str


class PushReport(TypedDict):
    ok: bool
    count: int
    created: int
    modified: int
    skipped_unique: int
    errors: int
    note: str
    strategy: PushStrategy | str
    chunk_plan: list[int]
    stages: list[ChunkStageReport]
    failed_items: list[FailedItemReport]
    failed_items_truncated: bool
    status: NotRequired[int | None]
    skipped: NotRequired[bool]
    applied: NotRequired[int]
    initial_status: NotRequired[int | None]
    initial_detail: NotRequired[str]
    detail: NotRequired[str]
    error: NotRequired[str]


class _EasySetupEngine(ControlIDSyncMixin):
    """
    Herda ControlIDSyncMixin para reutilizar login, _make_request, etc.
    Opera em UM device por vez (set_device antes de cada uso).
    """

    def _wait_for_device_online(
        self,
        max_attempts=24,
        interval_s=5,
        credentials_to_try=None,
    ):
        """
        Aguarda a catraca voltar a responder ao login apos reboot/reset.

        Usa polling ativo em vez de sleep fixo. Login bem-sucedido indica que
        a API ja voltou, embora o firmware ainda possa concluir etapas internas
        depois disso.
        """
        if credentials_to_try is None:
            credentials_to_try = [
                (self.device.username, self.device.password),
                (_FACTORY_LOGIN, _FACTORY_PASSWORD),
            ]

        for attempt in range(1, max_attempts + 1):
            for login_user, login_pass in credentials_to_try:
                try:
                    resp = requests.post(
                        self.get_url("login.fcgi"),
                        json={"login": login_user, "password": login_pass},
                        timeout=5,
                    )
                    if resp.status_code == 200 and resp.json().get("session"):
                        self.session = resp.json()["session"]
                        return {
                            "ok": True,
                            "attempts": attempt,
                            "used_default_credentials": (
                                login_user != self.device.username
                                or login_pass != self.device.password
                            ),
                        }
                except Exception:
                    pass

            logger.debug(
                f"[EASY_SETUP] [{self.device.name}] "
                f"Tentativa {attempt}/{max_attempts} - device ainda indisponivel..."
            )
            _time.sleep(interval_s)

        return {
            "ok": False,
            "error": (
                f"Device nao voltou a responder login apos {max_attempts * interval_s}s"
            ),
        }

    def _looks_like_duplicate_error(self, body):
        body_lower = (body or "").lower()
        return any(marker in body_lower for marker in _DUPLICATE_ERROR_MARKERS)

    def _get_reference_device(self):
        return (
            self.device.__class__.objects.filter(is_default=True).first()
            or self.device.__class__.objects.filter(is_active=True)
            .order_by("id")
            .first()
        )

    def _get_device_scoped_config(self, model, *, predicate=None):
        """
        Busca configuração na seguinte ordem:
        1. configuração do próprio device
        2. configuração do device padrão
        3. primeira configuração válida disponível
        """
        candidates = []

        current = model.objects.filter(device=self.device).first()
        if current:
            candidates.append(current)

        reference_device = self._get_reference_device()
        if reference_device and reference_device != self.device:
            reference = model.objects.filter(device=reference_device).first()
            if reference:
                candidates.append(reference)

        first_available = model.objects.order_by("id").first()
        if first_available:
            candidates.append(first_available)

        seen_ids = set()
        for candidate in candidates:
            if candidate.id in seen_ids:
                continue
            seen_ids.add(candidate.id)
            if predicate is None or predicate(candidate):
                return candidate

        return None

    def _pause_monitor_offline_detection(self, seconds=900):
        paused_until = timezone.now() + timedelta(seconds=seconds)
        monitor, _ = MonitorConfig.objects.update_or_create(
            device=self.device,
            defaults={
                "offline_detection_paused_until": paused_until,
                "is_offline": False,
                "offline_since": None,
            },
        )
        return {
            "ok": True,
            "paused_until": paused_until.isoformat(),
            "config_id": monitor.pk,
        }

    def _persist_applied_configs_to_database(
        self,
        *,
        persist_monitor=False,
        persist_device_settings=False,
    ):
        persisted = {}

        config_specs = []
        if persist_monitor:
            config_specs.append(
                (
                    MonitorConfig,
                    [
                        "request_timeout",
                        "hostname",
                        "port",
                        "path",
                        "heartbeat_timeout_seconds",
                    ],
                    lambda cfg: cfg.is_configured,
                )
            )
        if persist_device_settings:
            config_specs.extend(
                [
                    (
                        SystemConfig,
                        [
                            "auto_reboot_hour",
                            "auto_reboot_minute",
                            "clear_expired_users",
                            "keep_user_image",
                            "url_reboot_enabled",
                            "web_server_enabled",
                            "online",
                            "local_identification",
                            "language",
                            "daylight_savings_time_start",
                            "daylight_savings_time_end",
                            "catra_timeout",
                        ],
                        None,
                    ),
                    (
                        HardwareConfig,
                        [
                            "beep_enabled",
                            "bell_enabled",
                            "bell_relay",
                            "ssh_enabled",
                            "relayN_enabled",
                            "relayN_timeout",
                            "relayN_auto_close",
                            "door_sensorN_enabled",
                            "door_sensorN_idle",
                            "doorN_interlock",
                            "network_interlock_enabled",
                            "network_interlock_api_bypass_enabled",
                            "network_interlock_rex_bypass_enabled",
                            "exception_mode",
                            "doorN_exception_mode",
                        ],
                        None,
                    ),
                    (
                        SecurityConfig,
                        [
                            "password_only",
                            "hide_password_only",
                            "password_only_tip",
                            "hide_name_on_identification",
                            "denied_transaction_code",
                            "send_code_when_not_identified",
                            "send_code_when_not_authorized",
                            "verbose_logging_enabled",
                            "log_type",
                            "multi_factor_authentication_enabled",
                        ],
                        None,
                    ),
                    (
                        CatraConfig,
                        ["anti_passback", "daily_reset", "gateway", "operation_mode"],
                        None,
                    ),
                    (
                        PushServerConfig,
                        [
                            "push_request_timeout",
                            "push_request_period",
                            "push_remote_address",
                        ],
                        None,
                    ),
                ]
            )

        for model, field_names, predicate in config_specs:
            source = self._get_device_scoped_config(model, predicate=predicate)
            if not source:
                continue

            defaults = {
                field_name: getattr(source, field_name) for field_name in field_names
            }
            if model is MonitorConfig:
                defaults.update(
                    {
                        "offline_detection_paused_until": source.offline_detection_paused_until,
                    }
                )

            _, created = model.objects.update_or_create(
                device=self.device,
                defaults=defaults,
            )
            persisted[model.__name__] = {
                "ok": True,
                "created": created,
                "source_device_id": source.device_id,
            }

        return persisted

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

    # ── 2. Desabilitar identifier (pin/card off) ───────────────────────────
    def disable_identifier(self):
        """
        Desabilita métodos de identificação na catraca DEPOIS do push_data.

        Motivo: após factory reset, o firmware restaura
        pin_identification_enabled=1 (factory default) durante sua
        inicialização interna (~6s após boot).  Se chamarmos
        disable_identifier cedo demais (logo após login), o init do
        firmware sobrescreve nosso pin=0 de volta para pin=1.

        Chamar APÓS push_data garante que:
        a) O init do firmware já completou (pin=1 já restaurado)
        b) access_rules type≥1 já estão no DB da catraca
        c) Nosso set_configuration(pin=0) realmente muda o valor (1→0)
        d) configure_device_settings(pin=1) logo depois cria transição
           0→1 que FORÇA firmware a recarregar access_rules do DB
        """
        try:
            resp = self._make_request(
                "set_configuration.fcgi",
                json_data={
                    "identifier": {
                        "pin_identification_enabled": "0",
                        "card_identification_enabled": "0",
                    }
                },
            )
            ok = resp.status_code == 200
            if ok:
                logger.info(
                    f"[EASY_SETUP] [{self.device.name}] "
                    "identifier desabilitado (pin=0, card=0)"
                )
            return {"ok": ok}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── 3. Acertar data/hora ────────────────────────────────────────────────
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

    # ── 4. Configurar monitor ───────────────────────────────────────────────
    def configure_monitor(self):
        """Envia configuração de monitor (push) para a catraca."""
        try:
            monitor = self._get_device_scoped_config(
                MonitorConfig,
                predicate=lambda cfg: cfg.is_configured,
            )
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
                "source_device_id": monitor.device_id,
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def configure_network_interlock(self):
        """Configura o intertravamento via rede na catraca."""
        try:
            hw_cfg = self._get_device_scoped_config(HardwareConfig)
            if not hw_cfg:
                return {
                    "ok": True,
                    "skipped": True,
                    "message": "Nenhuma HardwareConfig encontrada",
                }

            payload = {
                "interlock_enabled": 1
                if getattr(hw_cfg, "network_interlock_enabled", False)
                else 0,
                "api_bypass_enabled": 1
                if getattr(hw_cfg, "network_interlock_api_bypass_enabled", False)
                else 0,
                "rex_bypass_enabled": 1
                if getattr(hw_cfg, "network_interlock_rex_bypass_enabled", False)
                else 0,
            }
            resp = self._make_request("set_network_interlock.fcgi", json_data=payload)
            return {
                "ok": resp.status_code == 200,
                "payload": payload,
                "source_device_id": hw_cfg.device_id,
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def sync_network_devices(self):
        """Faz a catraca conhecer os devices ativos do backend."""
        try:
            desired_values = [
                {"id": device.id, "name": device.name, "ip": device.ip}
                for device in Device.objects.filter(is_active=True).order_by("id")
            ]

            if not desired_values:
                return {"ok": True, "count": 0, "skipped": True}

            existing_ids = self._load_existing_ids("devices")
            desired_ids = {int(item["id"]) for item in desired_values}

            to_create = [
                item for item in desired_values if int(item["id"]) not in existing_ids
            ]
            to_update = [
                item for item in desired_values if int(item["id"]) in existing_ids
            ]
            to_delete = [
                device_id
                for device_id in existing_ids
                if int(device_id) not in desired_ids
            ]

            create_ok = True
            update_ok = True
            delete_ok = True

            if to_create:
                create_ok = self._create_objects_safe("devices", to_create).get(
                    "ok", False
                )

            if to_update:
                update_ok = self._modify_objects("devices", to_update)

            for device_id in to_delete:
                delete_ok = (
                    self._destroy_table("devices", {"devices": {"id": int(device_id)}})
                    and delete_ok
                )

            return {
                "ok": create_ok and update_ok and delete_ok,
                "count": len(desired_values),
                "created": len(to_create),
                "updated": len(to_update),
                "deleted": len(to_delete),
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── 5. Enviar configurações do device ───────────────────────────────────
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
        result = {"sections": {}}

        def bool_to_str(value):
            return "1" if value else "0"

        def is_missing_online_client(detail):
            text = str(detail or "").lower()
            return "online_client" in text and "not found" in text

        payload = {}

        # ── general (SystemConfig + HardwareConfig + UIConfig) ──
        general = {}

        sys_cfg = self._get_device_scoped_config(SystemConfig)
        if sys_cfg:
            general["catra_timeout"] = str(sys_cfg.catra_timeout or 5000)
            general["online"] = bool_to_str(sys_cfg.online)
            general["local_identification"] = bool_to_str(sys_cfg.local_identification)
            general["language"] = str(sys_cfg.language or "pt_BR")
            result["sections"]["system"] = {"source_device_id": sys_cfg.device_id}
        else:
            # Defaults seguros — local_identification DEVE ser 1
            general["local_identification"] = "1"
            general["online"] = "1"
            general["language"] = "pt_BR"
            result["sections"]["system"] = "defaults"

        hw_cfg = self._get_device_scoped_config(HardwareConfig)
        if hw_cfg:
            general["beep_enabled"] = bool_to_str(hw_cfg.beep_enabled)
            general["ssh_enabled"] = bool_to_str(hw_cfg.ssh_enabled)
            general["bell_enabled"] = bool_to_str(hw_cfg.bell_enabled)
            general["bell_relay"] = str(hw_cfg.bell_relay)
            general["exception_mode"] = str(hw_cfg.exception_mode or "none")
            result["sections"]["hardware"] = {"source_device_id": hw_cfg.device_id}

        # NOTA: screen_always_on não é suportado pelo firmware IDBLOCK
        # (causa "Node or attribute not found"), então não é enviado aqui.

        if general:
            payload["general"] = general

        # ── catra (CatraConfig) ──
        catra_cfg = self._get_device_scoped_config(CatraConfig)
        if catra_cfg:
            payload["catra"] = {
                "anti_passback": bool_to_str(catra_cfg.anti_passback),
                "daily_reset": bool_to_str(catra_cfg.daily_reset),
                "gateway": catra_cfg.gateway,
                "operation_mode": catra_cfg.operation_mode,
            }
            result["sections"]["catra"] = {"source_device_id": catra_cfg.device_id}
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
        sec_cfg = self._get_device_scoped_config(SecurityConfig)
        if sec_cfg:
            identifier_cfg["multi_factor_authentication"] = bool_to_str(
                getattr(sec_cfg, "multi_factor_authentication_enabled", False)
            )
            identifier_cfg["verbose_logging"] = bool_to_str(
                getattr(sec_cfg, "verbose_logging_enabled", True)
            )
            identifier_cfg["log_type"] = bool_to_str(
                getattr(sec_cfg, "log_type", False)
            )
            result["sections"]["security"] = {"source_device_id": sec_cfg.device_id}

        # Métodos de identificação habilitados.
        # PIN e ID+Senha são mutuamente exclusivos:
        #   pin_identification_enabled=1 → modo PIN
        #   pin_identification_enabled=0 → modo ID+Senha
        identifier_cfg.setdefault("card_identification_enabled", "1")
        identifier_cfg.setdefault("pin_identification_enabled", "1")

        payload["identifier"] = identifier_cfg
        result["sections"]["identifier_methods"] = True

        # ── push_server (PushServerConfig) ──
        ps_cfg = self._get_device_scoped_config(
            PushServerConfig,
            predicate=lambda cfg: bool(cfg.push_remote_address),
        )
        if ps_cfg and ps_cfg.push_remote_address:
            payload["push_server"] = {
                "push_request_timeout": str(ps_cfg.push_request_timeout),
                "push_request_period": str(ps_cfg.push_request_period),
                "push_remote_address": ps_cfg.push_remote_address,
            }
            result["sections"]["push_server"] = {"source_device_id": ps_cfg.device_id}
        else:
            # Sem PushServerConfig → desabilitar online_client para evitar
            # "cURL error: <url> malformed" a cada 5s após factory reset.
            payload["online_client"] = {
                "enabled": "0",
            }
            result["sections"]["push_server"] = "disabled (no config)"

        # ── Envia tudo de uma vez ──
        try:
            resp = self._make_request("set_configuration.fcgi", json_data=payload)
            result["ok"] = resp.status_code == 200
            result["payload_sections"] = list(payload.keys())
            if resp.status_code != 200:
                result["detail"] = resp.text[:300]
                if "online_client" in payload and is_missing_online_client(resp.text):
                    result["online_client_skipped"] = True
                    result["optional_warnings"] = [
                        "online_client nao suportado por este firmware"
                    ]
                    result["initial_detail"] = resp.text[:300]

                    retry_payload = dict(payload)
                    retry_payload.pop("online_client", None)
                    retry_resp = self._make_request(
                        "set_configuration.fcgi",
                        json_data=retry_payload,
                    )
                    result["ok"] = retry_resp.status_code == 200
                    result["payload_sections"] = list(retry_payload.keys())
                    result["retry_without_online_client_status"] = (
                        retry_resp.status_code
                    )
                    if retry_resp.status_code != 200:
                        result["detail"] = retry_resp.text[:300]
                    else:
                        result.pop("detail", None)
        except Exception as e:
            result["ok"] = False
            result["error"] = str(e)

        return result

    # ── 6. Verificar access_rules na catraca (polling) ──────────────────────
    def verify_access_rules(self, db_data, max_duration_s=180, interval_s=30):
        """
        Polling de access_rules na catraca após o setup completo.

        O firmware V5.18.3 tem init atrasada em MÚLTIPLAS ondas:
          - Onda 1 (~30-40s após boot): cria defaults, habilita biometry/card
          - Onda 2 (~2-3min após boot): recria access_rules com type=0

        Este método faz polling periódico, corrigindo type=0 sempre que
        aparecer, e forçando reload do identifier após cada correção.
        Para após 2 checks limpos consecutivos ou ao expirar max_duration_s.
        """
        result = {
            "checked": True,
            "polls": 0,
            "fixes_applied": 0,
            "consecutive_clean": 0,
        }
        deadline = _time.monotonic() + max_duration_s
        expected_rules = db_data.get("access_rules", [])

        while _time.monotonic() < deadline:
            result["polls"] += 1
            poll_num = result["polls"]

            try:
                # Carregar access_rules atuais da catraca
                sess = self.login()
                resp = requests.post(
                    self.get_url(f"load_objects.fcgi?session={sess}"),
                    json={
                        "object": "access_rules",
                        "fields": ["id", "name", "type", "priority"],
                    },
                    timeout=30,
                )
                if resp.status_code != 200:
                    logger.warning(
                        f"[EASY_SETUP] [{self.device.name}] "
                        f"Poll #{poll_num}: load_objects falhou HTTP {resp.status_code}"
                    )
                    _time.sleep(interval_s)
                    continue

                rules = resp.json().get("access_rules", [])
                bad_rules = [r for r in rules if r.get("type", 0) == 0]

                if not bad_rules:
                    result["consecutive_clean"] += 1
                    logger.info(
                        f"[EASY_SETUP] [{self.device.name}] "
                        f"Poll #{poll_num}: OK — {len(rules)} rules, "
                        f"todas type≥1 (clean {result['consecutive_clean']}/2)"
                    )
                    if result["consecutive_clean"] >= 2:
                        result["ok"] = True
                        logger.info(
                            f"[EASY_SETUP] [{self.device.name}] "
                            "Verificação estável — 2 checks limpos consecutivos ✓"
                        )
                        return result
                else:
                    # Encontrou type=0 — corrigir
                    result["consecutive_clean"] = 0
                    result["fixes_applied"] += 1
                    logger.warning(
                        f"[EASY_SETUP] [{self.device.name}] "
                        f"Poll #{poll_num}: {len(bad_rules)} rules type=0! "
                        f"Fix #{result['fixes_applied']}..."
                    )
                    self._fix_access_rules(db_data, expected_rules)

            except Exception as e:
                logger.error(
                    f"[EASY_SETUP] [{self.device.name}] Poll #{poll_num} erro: {e}"
                )

            _time.sleep(interval_s)

        # Expirou — reportar resultado
        result["ok"] = result["consecutive_clean"] >= 1
        if not result["ok"]:
            logger.error(
                f"[EASY_SETUP] [{self.device.name}] "
                f"Verificação expirou após {max_duration_s}s sem estabilizar!"
            )
        return result

    def _fix_access_rules(self, db_data, expected_rules):
        """
        Destrói access_rules type=0 e recria todos os dados dependentes.
        Depois força reload do identifier via disable→configure.
        """
        # 1. Destruir access_rules e todas as relações dependentes
        for tbl in [
            "access_rule_time_zones",
            "portal_access_rules",
            "group_access_rules",
            "user_access_rules",
            "access_rules",
        ]:
            self._destroy_table(tbl)

        # 2. Recriar access_rules com type≥1
        if expected_rules:
            safe_rules = [
                {**r, "type": max(r.get("type", 1), 1)} for r in expected_rules
            ]
            sess = self.login()
            requests.post(
                self.get_url(f"create_objects.fcgi?session={sess}"),
                json={"object": "access_rules", "values": safe_rules},
                timeout=60,
            )

        # 3. Recriar relações dependentes
        for tbl in [
            "user_access_rules",
            "group_access_rules",
            "portal_access_rules",
            "access_rule_time_zones",
        ]:
            values = db_data.get(tbl, [])
            if values:
                sess = self.login()
                requests.post(
                    self.get_url(f"create_objects.fcgi?session={sess}"),
                    json={"object": tbl, "values": values},
                    timeout=60,
                )

        # 4. Forçar identifier a recarregar do DB limpo
        self.disable_identifier()
        _time.sleep(2)
        self.configure_device_settings()

        logger.info(
            f"[EASY_SETUP] [{self.device.name}] "
            "Fix aplicado: rules recriadas + identifier recarregado"
        )

    # ── 7. Coletar dados do banco ───────────────────────────────────────────
    @staticmethod
    def _find_duplicate_pin_payloads(
        pins: Sequence[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for pin in pins:
            value = str(pin.get("value") or "").strip()
            if not value:
                continue
            grouped.setdefault(value, []).append(
                {
                    "user_id": pin.get("user_id"),
                    "name": pin.get("name"),
                }
            )

        return [
            {"value": value, "count": len(users), "users": users}
            for value, users in sorted(grouped.items())
            if len(users) > 1
        ]

    @staticmethod
    def _format_duplicate_pin_error(duplicates: Sequence[Mapping[str, Any]]) -> str:
        examples = []
        for duplicate in duplicates[:5]:
            users = duplicate.get("users") or []
            user_labels = []
            for user in users[:4]:
                if not isinstance(user, Mapping):
                    continue
                label = str(user.get("user_id") or "?")
                if user.get("name"):
                    label = f"{label} - {user.get('name')}"
                user_labels.append(label)
            examples.append(
                f"PIN {duplicate.get('value')} usado por {', '.join(user_labels)}"
            )
        suffix = " | ".join(examples)
        return (
            "Existem PINs duplicados no banco local. Corrija antes do Easy Setup. "
            f"{suffix}"
        ).strip()

    def _load_active_pin_payloads(self) -> list[dict[str, Any]]:
        return [
            {"user_id": user_id, "name": name, "value": pin}
            for user_id, name, pin in User.objects.exclude(pin__isnull=True)
            .exclude(pin="")
            .values_list("id", "name", "pin")
        ]

    def validate_data_integrity(self) -> dict[str, Any]:
        pins = self._load_active_pin_payloads()
        duplicates = self._find_duplicate_pin_payloads(pins)
        if duplicates:
            return {
                "ok": False,
                "error": self._format_duplicate_pin_error(duplicates),
                "duplicate_pins": duplicates[:20],
                "duplicate_pins_truncated": len(duplicates) > 20,
            }

        return {"ok": True, "pins_checked": len(pins)}

    def collect_db_data(self):
        """
        Coleta todos os dados do Django DB que precisam ser enviados
        para esta catraca.
        """
        # O backend Django é a fonte de verdade. As catracas recebem um
        # espelho do estado global salvo no banco.
        users_qs = User.objects.all().order_by("id")

        data = {}

        # Users
        users_list = []
        user_roles_list = []
        pins_list = []
        eligible_user_ids = set()
        skipped_users = []
        for u in users_qs:
            name = (u.name or "").strip()
            if not name:
                skipped_users.append({"user_id": u.id, "reason": "empty_name"})
                continue

            payload = {"id": u.id, "name": name}

            registration = (u.registration or "").strip()
            is_admin_user = bool(u.is_staff or u.is_superuser)
            if not registration and not is_admin_user:
                skipped_users.append(
                    {"user_id": u.id, "reason": "missing_registration"}
                )
                continue
            if registration:
                payload["registration"] = registration

            users_list.append(payload)
            eligible_user_ids.add(u.id)

            if is_admin_user:
                user_roles_list.append({"user_id": u.id, "role": 1})

            if u.pin:
                pins_list.append({"user_id": u.id, "name": u.name, "value": u.pin})

        duplicate_pins = self._find_duplicate_pin_payloads(pins_list)
        if duplicate_pins:
            raise ValueError(self._format_duplicate_pin_error(duplicate_pins))

        for pin in pins_list:
            pin.pop("name", None)

        data["users"] = users_list
        data["user_roles"] = user_roles_list
        data["pins"] = pins_list
        data["_user_push_warnings"] = skipped_users

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
            UserGroup.objects.filter(user_id__in=eligible_user_ids).values(
                "user_id", "group_id"
            )
        )

        data["user_access_rules"] = list(
            UserAccessRule.objects.filter(user_id__in=eligible_user_ids).values(
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
        data["cards"] = []
        for card in Card.objects.filter(user_id__in=eligible_user_ids).values(
            "user_id", "value"
        ):
            # A API da Control iD espera int64 em cards.value. O campo local e
            # texto para acomodar importacoes, entao normalizamos quando seguro.
            normalized = dict(card)
            try:
                normalized["value"] = int(str(normalized["value"]).strip())
            except (TypeError, ValueError):
                pass
            data["cards"].append(normalized)

        # Templates (biometria)
        data["templates"] = list(
            Template.objects.filter(user_id__in=eligible_user_ids).values(
                "user_id", "template"
            )
        )

        return data

    # ── 7. Enviar dados para catraca ────────────────────────────────────────
    def _destroy_table(self, table, where=None):
        """Limpa uma tabela da catraca antes de inserir novos dados."""
        if where is None:
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
            logger.warning(f"[EASY_SETUP] destroy_objects({table}) exception: {exc}")
            return False

    def _load_existing_ids(self, table):
        """Lê IDs existentes de uma tabela na catraca."""
        col = _TABLE_WHERE_COL.get(table, "id")
        try:
            sess = self.login()
            resp = requests.post(
                self.get_url(f"load_objects.fcgi?session={sess}"),
                json={"object": table, "fields": [col]},
                timeout=30,
            )
            if resp.status_code == 200:
                rows = resp.json().get(table, [])
                return {r[col] for r in rows}
        except Exception:
            pass
        return set()

    def _modify_objects(self, table, values):
        """Atualiza objetos existentes numa tabela da catraca (modify_objects)."""
        try:
            sess = self.login()
            resp = requests.post(
                self.get_url(f"modify_objects.fcgi?session={sess}"),
                json={"object": table, "values": values},
                timeout=60,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def _fix_default_access_rules(self):
        """
        Lê access_rules da catraca e corrige qualquer uma com type=0
        para type=1, evitando o erro "Invalid op type: 0".
        Retorna quantas regras foram corrigidas.
        """
        fixed = 0
        try:
            sess = self.login()
            resp = requests.post(
                self.get_url(f"load_objects.fcgi?session={sess}"),
                json={"object": "access_rules", "fields": ["id", "type"]},
                timeout=30,
            )
            if resp.status_code != 200:
                return fixed

            rules = resp.json().get("access_rules", [])
            bad_rules = [r for r in rules if r.get("type", 0) == 0]

            for rule in bad_rules:
                sess = self.login()
                resp = requests.post(
                    self.get_url(f"modify_objects.fcgi?session={sess}"),
                    json={
                        "object": "access_rules",
                        "values": [{"id": rule["id"], "type": 1}],
                    },
                    timeout=30,
                )
                if resp.status_code == 200:
                    fixed += 1
                    logger.info(
                        f"[EASY_SETUP] [{self.device.name}] "
                        f"access_rule id={rule['id']} type 0→1 corrigido"
                    )
        except Exception as e:
            logger.warning(
                f"[EASY_SETUP] [{self.device.name}] Erro ao corrigir access_rules: {e}"
            )
        return fixed

    def _legacy_create_objects_safe(self, table, values):
        """
        Cria objetos numa tabela da catraca com estratégia UPSERT.

        ⚠️ NUNCA usar destroy_objects em tabelas-pai!

        Estratégia:
        1. Tenta criar BATCH completo (mais rápido).
        2. Se falhar com UNIQUE/FOREIGN KEY:
           a) Entity tables (com 'id'): carrega IDs existentes,
              usa modify_objects para ATUALIZAR existentes e
              create_objects para os novos. Garante que defaults
              do firmware sejam sobrescritos com dados corretos.
           b) Junction tables (sem 'id'): cria um a um, pula UNIQUE
              (a relação já está estabelecida).
        """
        if not values:
            return {"ok": True, "count": 0, "skipped": True}

        try:
            # Tenta o batch completo primeiro
            sess = self.login()
            resp = requests.post(
                self.get_url(f"create_objects.fcgi?session={sess}"),
                json={"object": table, "values": values},
                timeout=60,
            )
            if resp.status_code == 200:
                return {"ok": True, "count": len(values), "status": 200}

            body = resp.text[:500]

            # Se batch falhou por constraint, estratégia depende do tipo
            if self._looks_like_duplicate_error(body) or "FOREIGN KEY" in body:
                if table in _UPSERTABLE_TABLES:
                    # Entity table → upsert (modify existing + create new)
                    return self._upsert_entity_objects(table, values)
                else:
                    # Junction table → um a um, pula UNIQUE
                    return self._create_junction_one_by_one(table, values)

            # Falha diferente de constraint
            logger.warning(
                f"[EASY_SETUP] create_objects({table}) falhou: "
                f"HTTP {resp.status_code} — {body}"
            )
            if table in _UPSERTABLE_TABLES:
                logger.info(
                    f"[EASY_SETUP] create_objects({table}) "
                    "falhou em batch; tentando upsert item a item..."
                )
                fallback = self._upsert_entity_objects(table, values)
                fallback["note"] = "fallback_upsert_after_batch_failure"
                fallback["batch_detail"] = body
                return fallback

            return {
                "ok": False,
                "count": len(values),
                "status": resp.status_code,
                "detail": body,
            }
        except Exception as e:
            return {"ok": False, "count": len(values), "error": str(e)}

    def _legacy_upsert_entity_objects(self, table, values):
        """
        Upsert para entity tables (com coluna 'id').
        Atualiza registros que já existem na catraca (ex: defaults do
        firmware) e cria os novos.
        """
        existing_ids = self._load_existing_ids(table)
        to_create = [v for v in values if v.get("id") not in existing_ids]
        to_modify = [v for v in values if v.get("id") in existing_ids]

        modified = 0
        created = 0
        errors = 0

        # Atualizar registros existentes com dados corretos do Django DB
        if to_modify:
            ok = self._modify_objects(table, to_modify)
            if ok:
                modified = len(to_modify)
            else:
                # Fallback: um a um
                for item in to_modify:
                    if self._modify_objects(table, [item]):
                        modified += 1
                    else:
                        errors += 1
                        logger.debug(
                            f"[EASY_SETUP] modify_objects({table}) "
                            f"falhou para id={item.get('id')}"
                        )

        # Criar novos registros
        for item in to_create:
            try:
                sess = self.login()
                r = requests.post(
                    self.get_url(f"create_objects.fcgi?session={sess}"),
                    json={"object": table, "values": [item]},
                    timeout=30,
                )
                if r.status_code == 200:
                    created += 1
                elif self._looks_like_duplicate_error(r.text):
                    # Race condition: apareceu entre load e create → modify
                    if self._modify_objects(table, [item]):
                        modified += 1
                    else:
                        errors += 1
                else:
                    errors += 1
                    logger.debug(
                        f"[EASY_SETUP] create_objects({table}) "
                        f"item falhou: {r.text[:200]}"
                    )
            except Exception:
                errors += 1

        logger.info(
            f"[EASY_SETUP] upsert({table}): "
            f"{modified} atualizados, {created} criados, {errors} erros"
        )
        return {
            "ok": errors == 0,
            "count": len(values),
            "modified": modified,
            "created": created,
            "errors": errors,
            "note": "upsert",
        }

    def _legacy_create_junction_one_by_one(self, table, values):
        """
        Cria registros de junção um a um, pulando UNIQUE.
        Para tabelas como group_access_rules, portal_access_rules, etc.
        Se o registro já existe, a relação já está estabelecida.
        """
        created = 0
        skipped = 0
        errors = 0

        for item in values:
            try:
                sess = self.login()
                r = requests.post(
                    self.get_url(f"create_objects.fcgi?session={sess}"),
                    json={"object": table, "values": [item]},
                    timeout=30,
                )
                if r.status_code == 200:
                    created += 1
                elif self._looks_like_duplicate_error(r.text):
                    skipped += 1
                else:
                    errors += 1
                    logger.debug(
                        f"[EASY_SETUP] create_objects({table}) "
                        f"item falhou: {r.text[:200]}"
                    )
            except Exception:
                errors += 1

        logger.info(
            f"[EASY_SETUP] create_one_by_one({table}): "
            f"{created} criados, {skipped} já existiam, {errors} erros"
        )
        return {
            "ok": errors == 0,
            "count": len(values),
            "created": created,
            "skipped_unique": skipped,
            "errors": errors,
            "note": "one-by-one",
        }

    def _chunk_values(
        self, values: Sequence[DevicePayload], chunk_size: int
    ) -> Iterable[list[DevicePayload]]:
        """Divide uma lista em lotes pequenos sem esconder a ordem original."""
        for index in range(0, len(values), chunk_size):
            yield list(values[index : index + chunk_size])

    def _response_detail(self, response: requests.Response) -> str:
        """Extrai uma mensagem curta e segura para logs/relatorio do frontend."""
        try:
            return (response.text or "")[:500]
        except Exception:
            return str(response)[:500]

    def _post_create_objects(
        self, table: str, values: Sequence[DevicePayload], *, timeout: int = 60
    ) -> requests.Response:
        sess = self.login()
        return requests.post(
            self.get_url(f"create_objects.fcgi?session={sess}"),
            json={"object": table, "values": values},
            timeout=timeout,
        )

    def _post_create_or_modify_objects(
        self, table: str, values: Sequence[DevicePayload], *, timeout: int = 60
    ) -> requests.Response:
        sess = self.login()
        return requests.post(
            self.get_url(f"create_or_modify_objects.fcgi?session={sess}"),
            json={"object": table, "values": values},
            timeout=timeout,
        )

    def _post_modify_objects(
        self, table: str, values: Sequence[DevicePayload], *, timeout: int = 60
    ) -> requests.Response:
        sess = self.login()
        return requests.post(
            self.get_url(f"modify_objects.fcgi?session={sess}"),
            json={"object": table, "values": values},
            timeout=timeout,
        )

    def _item_identity(self, item: Any) -> DevicePayload:
        """
        Mostra apenas os campos que ajudam a achar o registro problematico.

        O payload completo pode ter biometria/base64 ou campos grandes demais
        para a tela; por isso o relatorio usa uma identidade compacta.
        """
        if not isinstance(item, dict):
            return {"value": str(item)[:120]}

        useful_keys = (
            "id",
            "user_id",
            "group_id",
            "access_rule_id",
            "portal_id",
            "time_zone_id",
            "area_id",
            "value",
            "registration",
            "name",
        )
        identity = {key: item.get(key) for key in useful_keys if key in item}
        if identity:
            return identity

        return {key: item[key] for key in list(item.keys())[:4]}

    def _new_push_report(
        self,
        table: str,
        values: Sequence[DevicePayload],
        *,
        note: str,
        strategy: PushStrategy | str,
        initial_status: int | None = None,
        initial_detail: str | None = None,
    ) -> PushReport:
        report: PushReport = {
            "ok": True,
            "count": len(values),
            "created": 0,
            "modified": 0,
            "skipped_unique": 0,
            "errors": 0,
            "note": note,
            "strategy": strategy,
            "chunk_plan": list(_CREATE_CHUNK_LADDER),
            "stages": [],
            "failed_items": [],
            "failed_items_truncated": False,
        }
        if initial_status is not None:
            report["initial_status"] = initial_status
        if initial_detail:
            report["initial_detail"] = initial_detail
        return report

    def _new_skipped_push_report(self) -> PushReport:
        report = self._new_push_report("", [], note="skipped", strategy="skipped")
        report["skipped"] = True
        report["chunk_plan"] = []
        return report

    def _new_success_push_report(
        self,
        table: str,
        values: Sequence[DevicePayload],
        *,
        note: str,
        strategy: PushStrategy,
        applied: int = 0,
        created: int = 0,
        modified: int = 0,
        skipped_unique: int = 0,
    ) -> PushReport:
        report = self._new_push_report(table, values, note=note, strategy=strategy)
        report["status"] = 200
        if applied:
            report["applied"] = applied
        report["created"] = created
        report["modified"] = modified
        report["skipped_unique"] = skipped_unique
        report["chunk_plan"] = []
        return report

    def _new_stage_report(
        self, operation: PushOperation, chunk_size: int
    ) -> ChunkStageReport:
        return {
            "operation": operation,
            "chunk_size": chunk_size,
            "chunks": 0,
            "ok_chunks": 0,
            "failed_chunks": 0,
            "records_ok": 0,
            "records_pending": 0,
        }

    def _append_failed_item(
        self,
        report: PushReport,
        table: str,
        item: DevicePayload,
        *,
        status: int | None,
        detail: str,
    ) -> None:
        if len(report["failed_items"]) >= _MAX_FAILED_ITEM_REPORTS:
            report["failed_items_truncated"] = True
            return

        report["failed_items"].append(
            {
                "table": table,
                "item": self._item_identity(item),
                "status": status,
                "detail": (detail or "")[:500],
            }
        )

    def _mark_single_item_failed(
        self,
        report: PushReport,
        stage: ChunkStageReport,
        table: str,
        item: DevicePayload,
        status: int | None,
        detail: str,
    ) -> None:
        report["errors"] += 1
        stage["failed_chunks"] += 1
        stage["records_pending"] += 1
        self._append_failed_item(report, table, item, status=status, detail=detail)
        logger.debug(
            "[EASY_SETUP] [%s] %s falhou para %s: HTTP %s - %s",
            self.device.name,
            table,
            self._item_identity(item),
            status,
            detail,
        )

    def _resolve_duplicate_create(
        self,
        report: PushReport,
        stage: ChunkStageReport,
        table: str,
        item: DevicePayload,
        duplicate_mode: DuplicateMode,
    ) -> bool:
        """
        Trata duplicidade quando o lote ja caiu para 1 registro.

        - skip: relacoes/cartoes/pins ja existem, entao consideramos resolvido.
        - modify: entidade com id ja existente deve ser atualizada.
        - error: duplicidade inesperada vira falha explicita.
        """
        if duplicate_mode == "skip":
            report["skipped_unique"] += 1
            stage["ok_chunks"] += 1
            stage["records_ok"] += 1
            return True

        if duplicate_mode != "modify":
            return False

        try:
            response = self._post_modify_objects(table, [item], timeout=30)
            detail = self._response_detail(response)
            if response.status_code == 200:
                report["modified"] += 1
                stage["ok_chunks"] += 1
                stage["records_ok"] += 1
                return True

            self._mark_single_item_failed(
                report,
                stage,
                table,
                item,
                response.status_code,
                f"create duplicado; modify falhou: {detail}",
            )
            return True
        except Exception as exc:
            self._mark_single_item_failed(
                report,
                stage,
                table,
                item,
                None,
                f"create duplicado; modify gerou excecao: {exc}",
            )
            return True

    def _run_dynamic_chunks(
        self,
        table: str,
        values: Sequence[DevicePayload],
        *,
        operation: PushOperation,
        report: PushReport,
        duplicate_mode: DuplicateMode = "error",
        include_full_attempt: bool = False,
    ) -> None:
        """
        Envia somente os lotes que ainda falharam para o proximo tamanho.

        Fluxo:
        1. tenta o conjunto inteiro quando include_full_attempt=True;
        2. tenta 100, 50, 10, 5;
        3. cai para 1 por 1 e registra o item exato que quebrou.
        """
        pending = list(values)
        if not pending:
            return

        sizes = list(_CREATE_CHUNK_LADDER)
        if include_full_attempt:
            sizes = [len(pending)] + [size for size in sizes if size < len(pending)]
        else:
            sizes = [size for size in sizes if size < len(pending) or size == 1]
        if 1 not in sizes:
            sizes.append(1)

        for chunk_size in sizes:
            if not pending:
                break

            stage = self._new_stage_report(operation, chunk_size)
            next_pending = []

            for chunk in self._chunk_values(pending, chunk_size):
                stage["chunks"] += 1
                timeout = 30 if chunk_size == 1 else 60

                try:
                    if operation == "create_or_modify":
                        response = self._post_create_or_modify_objects(
                            table, chunk, timeout=timeout
                        )
                    elif operation == "modify":
                        response = self._post_modify_objects(
                            table, chunk, timeout=timeout
                        )
                    else:
                        response = self._post_create_objects(
                            table, chunk, timeout=timeout
                        )
                    status = response.status_code
                    detail = self._response_detail(response)
                except Exception as exc:
                    status = None
                    detail = str(exc)[:500]

                if status == 200:
                    if operation == "create_or_modify":
                        report["applied"] = int(report.get("applied", 0)) + len(
                            chunk
                        )
                    elif operation == "modify":
                        report["modified"] += len(chunk)
                    else:
                        report["created"] += len(chunk)
                    stage["ok_chunks"] += 1
                    stage["records_ok"] += len(chunk)
                    continue

                if chunk_size == 1:
                    item = chunk[0]
                    is_duplicate = (
                        operation == "create"
                        and self._looks_like_duplicate_error(detail)
                    )
                    if is_duplicate and self._resolve_duplicate_create(
                        report, stage, table, item, duplicate_mode
                    ):
                        continue

                    self._mark_single_item_failed(
                        report, stage, table, item, status, detail
                    )
                    continue

                stage["failed_chunks"] += 1
                stage["records_pending"] += len(chunk)
                next_pending.extend(chunk)

            if stage["chunks"]:
                report["stages"].append(stage)
            pending = next_pending

    def _finalize_push_report(self, report: PushReport) -> PushReport:
        report["ok"] = report["errors"] == 0
        report["status"] = 200 if report["ok"] else report.get("initial_status")
        return report

    def _count_push_result_records(self, result: Mapping[str, Any]) -> int:
        if result.get("skipped"):
            return 0

        counters = (
            result.get("applied"),
            result.get("created"),
            result.get("modified"),
            result.get("skipped_unique"),
        )
        if any(isinstance(value, int) for value in counters):
            return sum(value for value in counters if isinstance(value, int))

        count = result.get("count", 0)
        return count if result.get("ok") and isinstance(count, int) else 0

    def _create_junction_dynamic_chunks(
        self,
        table: str,
        values: Sequence[DevicePayload],
        *,
        initial_status: int | None = None,
        initial_detail: str | None = None,
    ) -> PushReport:
        report = self._new_push_report(
            table,
            values,
            note="dynamic_chunks",
            strategy="dynamic_chunks",
            initial_status=initial_status,
            initial_detail=initial_detail,
        )
        self._run_dynamic_chunks(
            table,
            values,
            operation="create",
            report=report,
            duplicate_mode="skip",
            include_full_attempt=False,
        )
        return self._finalize_push_report(report)

    def _create_or_modify_entity_objects(
        self, table: str, values: Sequence[DevicePayload]
    ) -> PushReport:
        """
        Caminho rapido para entidades que possuem id estavel.

        Depois do factory reset a Control iD recria alguns defaults
        (areas, portals, access_rules etc.). Nesses casos create_objects gera
        erro de constraint mesmo quando queremos apenas deixar o registro igual
        ao banco. create_or_modify_objects trata criacao e atualizacao no mesmo
        endpoint e evita cair no fallback por duplicidade esperada.
        """
        try:
            response = self._post_create_or_modify_objects(table, values, timeout=60)
            detail = self._response_detail(response)
            if response.status_code == 200:
                return self._new_success_push_report(
                    table,
                    values,
                    note="create_or_modify_batch",
                    strategy="create_or_modify",
                    applied=len(values),
                )

            initial_status = response.status_code
            initial_detail = detail
        except Exception as exc:
            initial_status = None
            initial_detail = str(exc)[:500]

        logger.warning(
            "[EASY_SETUP] [%s] create_or_modify_objects(%s) batch falhou "
            "(HTTP %s). Iniciando fallback dinamico: 100, 50, 10, 5, 1.",
            self.device.name,
            table,
            initial_status,
        )

        report = self._new_push_report(
            table,
            values,
            note="create_or_modify_dynamic_chunks",
            strategy="dynamic_chunks",
            initial_status=initial_status,
            initial_detail=initial_detail,
        )
        report["applied"] = 0
        self._run_dynamic_chunks(
            table,
            values,
            operation="create_or_modify",
            report=report,
            include_full_attempt=False,
        )
        return self._finalize_push_report(report)

    def _upsert_entity_objects(
        self,
        table: str,
        values: Sequence[DevicePayload],
        *,
        initial_status: int | None = None,
        initial_detail: str | None = None,
    ) -> PushReport:
        report = self._new_push_report(
            table,
            values,
            note="upsert_dynamic_chunks",
            strategy="dynamic_chunks",
            initial_status=initial_status,
            initial_detail=initial_detail,
        )

        existing_ids = self._load_existing_ids(table)
        to_modify = [value for value in values if value.get("id") in existing_ids]
        to_create = [value for value in values if value.get("id") not in existing_ids]

        logger.info(
            "[EASY_SETUP] [%s] %s: upsert dinamico (%s criar, %s atualizar)",
            self.device.name,
            table,
            len(to_create),
            len(to_modify),
        )

        self._run_dynamic_chunks(
            table,
            to_modify,
            operation="modify",
            report=report,
            include_full_attempt=True,
        )
        self._run_dynamic_chunks(
            table,
            to_create,
            operation="create",
            report=report,
            duplicate_mode="modify",
            include_full_attempt=True,
        )

        return self._finalize_push_report(report)

    def _create_objects_safe(
        self, table: str, values: Sequence[DevicePayload]
    ) -> PushReport:
        """
        Cria dados na catraca com fallback progressivo e diagnostico claro.

        Primeiro tentamos o batch completo, que e o caminho rapido. Se a
        catraca rejeitar o conjunto, nao desistimos do pacote inteiro: quebramos
        em 100, 50, 10, 5 e finalmente 1 por 1. Assim um registro ruim nao
        derruba 1444 usuarios, grupos, biometrias ou relacoes.
        """
        if not values:
            return self._new_skipped_push_report()

        if table in _UPSERTABLE_TABLES:
            return self._create_or_modify_entity_objects(table, values)

        try:
            response = self._post_create_objects(table, values, timeout=60)
            detail = self._response_detail(response)
            if response.status_code == 200:
                return self._new_success_push_report(
                    table,
                    values,
                    note="batch",
                    strategy="batch",
                    created=len(values),
                )

            initial_status = response.status_code
            initial_detail = detail
        except Exception as exc:
            initial_status = None
            initial_detail = str(exc)[:500]

        logger.warning(
            "[EASY_SETUP] [%s] create_objects(%s) batch completo falhou "
            "(HTTP %s). Iniciando fallback dinamico: 100, 50, 10, 5, 1.",
            self.device.name,
            table,
            initial_status,
        )

        return self._create_junction_dynamic_chunks(
            table,
            values,
            initial_status=initial_status,
            initial_detail=initial_detail,
        )

    def push_data(self, data):
        """
        Envia os dados coletados para a catraca SEM DESTRUIR NADA.

        ⚠️ REGRA CRÍTICA: NUNCA usar destroy_objects em tabelas-pai
        (users, groups, access_rules, portals, areas, time_zones,
        time_spans) nem em suas junções (group_access_rules,
        portal_access_rules, access_rule_time_zones).

        Destruir e recriar tabelas corrompe permanentemente o cache
        interno do firmware V5.18.3, causando crash ao avaliar acesso.
        Mesmo reboot ou disable→enable identifier não corrige.

        Estratégia COMPROVADA:
          1. Corrigir access_rules type=0 → type=1 (modify_objects)
          2. Criar TUDO com create_objects (UNIQUE → skip, dado já existe)
          3. Nenhum destroy em nenhuma tabela

        Após factory reset, a catraca preserva dados estruturais
        (groups, rules, portals, etc.) e limpa apenas users/pins.
        Criamos users/pins por cima e ignoramos UNIQUE no resto.
        """
        results = {}

        # ── Fase 1: Corrigir access_rules type=0 ─────────────────────
        logger.info(
            f"[EASY_SETUP] [{self.device.name}] "
            "Fase 1 — corrigir access_rules type=0..."
        )
        fixed = self._fix_default_access_rules()
        results["_fix_type0"] = {"ok": True, "fixed": fixed}

        # ── Fase 2: Criar TUDO por cima (UNIQUE → skip) ──────────────
        # Ordem respeita FK: entidades-pai primeiro, junções depois.
        # access_rule_time_zones ANTES de portal_access_rules (firmware
        # crasha se portal é vinculado a regra sem time_zone).
        logger.info(
            f"[EASY_SETUP] [{self.device.name}] "
            "Fase 2 — create por cima (sem destroy)..."
        )
        for table in PUSH_ORDER:
            values = data.get(table, [])
            results[table] = self._create_objects_safe(table, values)

        return results

    # ── Orquestrador completo ───────────────────────────────────────────────
    def run_full_setup(self):
        """
        Executa o setup completo num único device.

        ⚠️ REGRA CRÍTICA: Após factory reset, o firmware preserva dados
        estruturais (groups, rules, portals, etc.) e limpa users/pins.
        NUNCA destruir tabelas — apenas criar por cima (UNIQUE → skip).

        Retorna dict com resultado de cada etapa.
        """
        report = {"device": self.device.name, "steps": {}}
        t0 = _time.monotonic()

        report["steps"]["pause_offline_detection"] = (
            self._pause_monitor_offline_detection()
        )

        # Etapa 1 — Login
        try:
            self.login(force_new=True)
            report["steps"]["login"] = {"ok": True}
        except Exception as e:
            report["steps"]["login"] = {"ok": False, "error": str(e)}
            report["elapsed_s"] = round(_time.monotonic() - t0, 2)
            return report

        # Etapa 2 — Factory reset (mantém rede)
        # Limpa users/pins/cards/templates e reseta configs.
        # Preserva: groups, access_rules, portals, areas, time_zones,
        # time_spans, e todas as junções estruturais.
        # Etapa 1.5: validar dados locais antes de resetar a catraca.
        report["steps"]["preflight"] = self.validate_data_integrity()
        if not report["steps"]["preflight"].get("ok"):
            logger.error(
                "[EASY_SETUP] [%s] Preflight FALHOU: %s",
                self.device.name,
                report["steps"]["preflight"].get("error"),
            )
            report["elapsed_s"] = round(_time.monotonic() - t0, 2)
            return report

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

        # Etapa 5 — Aguardar firmware init completa (~35s)
        # O firmware V5.18.3 tem init atrasada que pode criar
        # access_rules type=0 e alterar configs. Esperamos antes de
        # corrigir/criar dados para não ter race condition.
        logger.info(
            f"[EASY_SETUP] [{self.device.name}] "
            "Aguardando firmware completar init (~35s)..."
        )
        _time.sleep(35)

        # Etapa 6 — Corrigir access_rules type=0 e enviar dados
        # Primeiro corrige type=0 (modify_objects), depois cria
        # TUDO por cima (create_objects). UNIQUE → skip.
        # ⚠️ NENHUM destroy_objects é usado!
        logger.info(f"[EASY_SETUP] [{self.device.name}] Coletando dados do DB...")
        db_data = self.collect_db_data()

        logger.info(
            f"[EASY_SETUP] [{self.device.name}] "
            "Enviando dados (create por cima, sem destroy)..."
        )
        report["steps"]["push"] = self.push_data(db_data)

        logger.info(
            f"[EASY_SETUP] [{self.device.name}] "
            "Sincronizando tabela devices para intertravamento/rede..."
        )
        report["steps"]["network_devices"] = self.sync_network_devices()

        # Etapa 7 — Configurações do device
        # Envia todas as configs (identifier, catra, general, push_server).
        logger.info(f"[EASY_SETUP] [{self.device.name}] Enviando configurações...")
        report["steps"]["device_settings"] = self.configure_device_settings()

        logger.info(
            f"[EASY_SETUP] [{self.device.name}] "
            "Configurando intertravamento via rede..."
        )
        report["steps"]["network_interlock"] = self.configure_network_interlock()

        report["steps"]["persist_applied_configs"] = (
            self._persist_applied_configs_to_database(
                persist_monitor=report["steps"]["monitor"].get("ok", False),
                persist_device_settings=(
                    report["steps"]["device_settings"].get("ok", False)
                    and report["steps"]["network_interlock"].get("ok", False)
                ),
            )
        )

        report["elapsed_s"] = round(_time.monotonic() - t0, 2)

        # Resumo rápido
        push = report["steps"]["push"]
        total_pushed = sum(self._count_push_result_records(v) for v in push.values())
        total_errors = sum(
            1 for v in push.values() if not v.get("ok") and not v.get("skipped")
        )
        report["summary"] = {
            "records_pushed": total_pushed,
            "tables_with_errors": total_errors,
        }

        return report

    def _legacy_factory_reset_v1(self):
        """
        Reseta a catraca para configuracao de fabrica mantendo config de rede.
        Usa polling ativo para detectar quando a API volta a responder.
        """
        result = {}

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

        self.session = None
        logger.info(
            f"[EASY_SETUP] [{self.device.name}] "
            "Factory reset enviado, aguardando catraca voltar online..."
        )

        online_result = self._wait_for_device_online()
        result.update(online_result)
        if result.get("ok") and result.get("used_default_credentials"):
            result["warning"] = (
                "Factory reset resetou credenciais para admin/admin. "
                "Atualize username/password do device no Django."
            )

        if result.get("ok"):
            logger.info(
                f"[EASY_SETUP] [{self.device.name}] "
                f"Online apos reboot (tentativa {result.get('attempts')})"
            )
        return result

    def _legacy_fix_access_rules_v1(self, db_data, expected_rules):
        """
        Corrige access_rules problemáticas sem destruir tabelas.
        Depois força reload do identifier via disable -> configure.
        """
        safe_rules = [{**r, "type": max(r.get("type", 1), 1)} for r in expected_rules]
        if safe_rules:
            self._create_objects_safe("access_rules", safe_rules)

        for table in [
            "user_access_rules",
            "group_access_rules",
            "portal_access_rules",
            "access_rule_time_zones",
        ]:
            values = db_data.get(table, [])
            if values:
                self._create_objects_safe(table, values)

        self.disable_identifier()
        _time.sleep(2)
        self.configure_device_settings()

        logger.info(
            f"[EASY_SETUP] [{self.device.name}] "
            "Fix aplicado: rules corrigidas e identifier recarregado"
        )

    def _legacy_run_full_setup_v1(self):
        """
        Executa o setup completo num unico device.
        """
        report = {"device": self.device.name, "steps": {}}
        t0 = _time.monotonic()

        report["steps"]["pause_offline_detection"] = (
            self._pause_monitor_offline_detection()
        )

        try:
            self.login(force_new=True)
            report["steps"]["login"] = {"ok": True}
        except Exception as e:
            report["steps"]["login"] = {"ok": False, "error": str(e)}
            report["elapsed_s"] = round(_time.monotonic() - t0, 2)
            return report

        logger.info(
            f"[EASY_SETUP] [{self.device.name}] Factory reset (keep_network)..."
        )
        report["steps"]["factory_reset"] = self.factory_reset()
        if not report["steps"]["factory_reset"].get("ok"):
            logger.error(
                f"[EASY_SETUP] [{self.device.name}] Factory reset FALHOU - abortando"
            )
            report["elapsed_s"] = round(_time.monotonic() - t0, 2)
            return report

        logger.info(f"[EASY_SETUP] [{self.device.name}] Acertando relogio...")
        report["steps"]["datetime"] = self.set_datetime()

        logger.info(f"[EASY_SETUP] [{self.device.name}] Configurando monitor...")
        report["steps"]["monitor"] = self.configure_monitor()

        logger.info(f"[EASY_SETUP] [{self.device.name}] Coletando dados do DB...")
        db_data = self.collect_db_data()

        logger.info(
            f"[EASY_SETUP] [{self.device.name}] "
            "Enviando dados (create por cima, sem destroy)..."
        )
        report["steps"]["push"] = self.push_data(db_data)

        logger.info(
            f"[EASY_SETUP] [{self.device.name}] "
            "Sincronizando tabela devices para intertravamento/rede..."
        )
        report["steps"]["network_devices"] = self.sync_network_devices()

        logger.info(
            f"[EASY_SETUP] [{self.device.name}] "
            "Forcando reload do identifier (disable -> enable)..."
        )
        report["steps"]["disable_identifier"] = self.disable_identifier()

        logger.info(f"[EASY_SETUP] [{self.device.name}] Enviando configuracoes...")
        report["steps"]["device_settings"] = self.configure_device_settings()

        logger.info(
            f"[EASY_SETUP] [{self.device.name}] "
            "Configurando intertravamento via rede..."
        )
        report["steps"]["network_interlock"] = self.configure_network_interlock()

        report["steps"]["persist_applied_configs"] = (
            self._persist_applied_configs_to_database(
                persist_monitor=report["steps"]["monitor"].get("ok", False),
                persist_device_settings=(
                    report["steps"]["device_settings"].get("ok", False)
                    and report["steps"]["network_interlock"].get("ok", False)
                ),
            )
        )

        logger.info(
            f"[EASY_SETUP] [{self.device.name}] "
            "Verificando access_rules apos estabilizacao do firmware..."
        )
        report["steps"]["verify_access_rules"] = self.verify_access_rules(db_data)

        report["elapsed_s"] = round(_time.monotonic() - t0, 2)

        push = report["steps"]["push"]
        total_pushed = sum(self._count_push_result_records(v) for v in push.values())
        total_errors = sum(
            1 for v in push.values() if not v.get("ok") and not v.get("skipped")
        )
        report["summary"] = {
            "records_pushed": total_pushed,
            "tables_with_errors": total_errors,
            "device_settings_ok": report["steps"]["device_settings"].get("ok", False),
            "verify_access_rules_ok": report["steps"]["verify_access_rules"].get(
                "ok", False
            ),
        }

        return report
