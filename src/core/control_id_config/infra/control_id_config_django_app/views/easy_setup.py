"""
Easy Setup — Reset e reconfiguração completa de catracas selecionadas.

GET  /api/config/easy-setup/  → Lista devices disponíveis
POST /api/config/easy-setup/  → Executa setup nos devices selecionados

Fluxo por device:
  1. Login
  2. Limpar TODOS os dados da catraca (destroy_objects)
  3. Acertar data/hora
  4. Configurar monitor (push notifications)
  5. Enviar todos os dados do banco (users, groups, regras, etc.)
  6. Enviar PINs de identificação
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
from src.core.control_id_monitor.infra.control_id_monitor_django_app.models import (
    MonitorConfig,
)
from src.core.user.infra.user_django_app.models import User

logger = logging.getLogger(__name__)

# ── Ordem de limpeza (relações primeiro, entidades-pai por último) ──────────
CLEANUP_ORDER = [
    "access_logs",
    "templates",
    "cards",
    "pins",
    "user_access_rules",
    "user_groups",
    "group_access_rules",
    "portal_access_rules",
    "access_rule_time_zones",
    "groups",
    "access_rules",
    "time_spans",
    "time_zones",
    "portals",
    "areas",
    "users",
]

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

    # ── 1. Limpar dados ─────────────────────────────────────────────────────
    def clean_catraca(self):
        """Remove todas as tabelas da catraca na ordem segura de FK."""
        results = {}
        for table in CLEANUP_ORDER:
            try:
                sess = self.login()
                resp = requests.post(
                    self.get_url(f"destroy_objects.fcgi?session={sess}"),
                    json={
                        "object": table,
                        "where": {table: {"id": {">=": 0}}},
                    },
                    timeout=30,
                )
                results[table] = {
                    "status": resp.status_code,
                    "ok": resp.status_code == 200,
                }
            except Exception as e:
                results[table] = {"status": 0, "ok": False, "error": str(e)}
        return results

    # ── 2. Acertar data/hora ────────────────────────────────────────────────
    def set_datetime(self):
        """Sincroniza relógio da catraca com o servidor."""
        try:
            now = timezone.localtime()
            payload = {
                "general": {
                    "datetime": str(int(now.timestamp())),
                }
            }
            resp = self._make_request("set_configuration.fcgi", json_data=payload)
            return {"ok": resp.status_code == 200, "datetime": now.isoformat()}
        except Exception as e:
            return {"ok": False, "error": str(e)}

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

    # ── 4. Coletar dados do banco ───────────────────────────────────────────
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

        # TimeSpans
        data["time_spans"] = list(
            TimeSpan.objects.values(
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
        )

        # AccessRules
        data["access_rules"] = list(
            AccessRule.objects.values("id", "name", "type", "priority")
        )

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

    # ── 5. Enviar dados para catraca ────────────────────────────────────────
    def push_data(self, data):
        """
        Envia os dados coletados para a catraca na ordem correta de FK.
        Retorna dict com resultado por tabela.
        """
        results = {}
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
                    results[table]["detail"] = resp.text[:200]
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

        # Etapa 2 — Limpar dados
        logger.info(f"[EASY_SETUP] [{self.device.name}] Limpando dados...")
        report["steps"]["clean"] = self.clean_catraca()

        # Etapa 3 — Acertar data/hora
        logger.info(f"[EASY_SETUP] [{self.device.name}] Acertando relógio...")
        report["steps"]["datetime"] = self.set_datetime()

        # Etapa 4 — Configurar monitor
        logger.info(f"[EASY_SETUP] [{self.device.name}] Configurando monitor...")
        report["steps"]["monitor"] = self.configure_monitor()

        # Etapa 5 — Coletar e enviar dados
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
