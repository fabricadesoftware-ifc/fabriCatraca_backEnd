"""
Serviço de Verificação de Acesso — integrado ao sistema de Monitor

Quando a catraca envia um log de acesso via push (Monitor),
este serviço analisa as regras de acesso configuradas no banco
e loga no console o MOTIVO EXATO da decisão (acesso concedido ou negado).

Baseado na lógica do script 'verificação catraca.py', agora usando
os models Django e o ORM.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
from django.utils import timezone
import logging
import requests

logger = logging.getLogger(__name__)

# Mapeamento de event_type para descrição legível
EVENT_DESCRIPTIONS = {
    1: "Equipamento inválido",
    2: "Parâmetro de identificação inválido",
    3: "Não identificado",
    4: "Identificação pendente",
    5: "Tempo de identificação esgotado",
    6: "Acesso NEGADO",
    7: "Acesso CONCEDIDO",
    8: "Acesso pendente",
    9: "Usuário não é administrador",
    10: "Acesso não identificado",
    11: "Acesso por botoeira",
    12: "Acesso pela interface web",
    13: "Desistência de entrada",
    14: "Sem resposta",
    15: "Acesso pela interfonia",
}

# Eventos que representam acesso concedido
GRANTED_EVENTS = {7, 11, 12, 15}

# Eventos que representam acesso negado
DENIED_EVENTS = {1, 2, 3, 5, 6, 9, 10}


@dataclass
class RuleVerdict:
    """Resultado estruturado da análise de UMA regra para o usuário."""

    rule_name: str
    rule_type: int  # 1=liberação, 0=bloqueio
    priority: int
    user_has_rule: bool
    time_ok: bool
    via_group: bool = False  # se vem via grupo ou direto
    time_detail: str = ""  # detalhe do horário (ex: "00:00-23:59 Seg-Dom")


@dataclass
class AccessVerdict:
    """Veredito final estruturado da análise de todas as regras."""

    # Listas de regras analisadas
    active_liberations: List[RuleVerdict] = field(default_factory=list)
    active_blocks: List[RuleVerdict] = field(default_factory=list)
    inactive_liberations: List[RuleVerdict] = field(
        default_factory=list
    )  # fora do horário
    unlinked_rules: List[RuleVerdict] = field(default_factory=list)  # usuário não tem

    # Estado geral
    user_found: bool = False
    portal_found: bool = False
    portal_has_rules: bool = False
    user_has_any_rule: bool = False
    user_has_any_matching_rule: bool = False

    # Diagnóstico preciso
    precise_reason: str = ""

    def compute_precise_reason(self, event_type: int) -> str:
        """Calcula o motivo EXATO baseado nas regras e no resultado da catraca."""
        is_denied = event_type in DENIED_EVENTS
        is_granted = event_type in GRANTED_EVENTS

        # ── Eventos específicos têm diagnóstico direto ──
        if event_type == 3:
            self.precise_reason = (
                "NEGADO: Biometria ou cartão não reconhecido pelo dispositivo"
            )
            return self.precise_reason
        if event_type == 5:
            self.precise_reason = "NEGADO: Tempo de leitura biométrica/cartão esgotado (pessoa não aproximou a tempo)"
            return self.precise_reason
        if event_type == 1:
            self.precise_reason = (
                "NEGADO: Equipamento/dispositivo reportou erro interno"
            )
            return self.precise_reason
        if event_type == 2:
            self.precise_reason = (
                "NEGADO: Credencial apresentada é inválida ou corrompida"
            )
            return self.precise_reason
        if event_type == 9:
            self.precise_reason = "NEGADO: Tentativa de acesso administrativo por usuário sem permissão de admin"
            return self.precise_reason
        if event_type == 10:
            self.precise_reason = (
                "NEGADO: Acesso sem identificação (nenhuma credencial apresentada)"
            )
            return self.precise_reason

        # ── Problemas de configuração ──
        if not self.user_found:
            self.precise_reason = (
                "NEGADO: Usuário não existe no sistema (user_id inválido ou zero)"
            )
            return self.precise_reason

        if not self.portal_found:
            self.precise_reason = "NEGADO: Portal não encontrado no banco de dados (possível dessincronização com a catraca)"
            return self.precise_reason

        if not self.portal_has_rules:
            self.precise_reason = "NEGADO: O portal não possui NENHUMA regra de acesso vinculada — ninguém consegue passar por ele"
            return self.precise_reason

        if not self.user_has_any_rule:
            self.precise_reason = "NEGADO: Usuário não possui NENHUMA regra de acesso (nem direta, nem via grupo)"
            return self.precise_reason

        if not self.user_has_any_matching_rule:
            self.precise_reason = (
                "NEGADO: Usuário possui regras, mas NENHUMA delas está vinculada a este portal. "
                "As regras do usuário não coincidem com as regras exigidas pelo portal"
            )
            return self.precise_reason

        # ── Análise de bloqueio vs liberação (prioridade) ──
        if self.active_blocks and self.active_liberations:
            best_block = max(self.active_blocks, key=lambda r: r.priority)
            best_lib = max(self.active_liberations, key=lambda r: r.priority)
            if best_block.priority >= best_lib.priority:
                self.precise_reason = (
                    f'NEGADO: Regra de BLOQUEIO "{best_block.rule_name}" (prioridade {best_block.priority}) '
                    f'sobrepõe a regra de liberação "{best_lib.rule_name}" (prioridade {best_lib.priority}). '
                    f"Remova a regra de bloqueio ou aumente a prioridade da liberação"
                )
                return self.precise_reason

        if self.active_blocks and not self.active_liberations:
            best_block = max(self.active_blocks, key=lambda r: r.priority)
            self.precise_reason = (
                f'NEGADO: Regra de BLOQUEIO "{best_block.rule_name}" ativa no horário atual, '
                f"e o usuário não possui nenhuma regra de liberação ativa neste momento"
            )
            return self.precise_reason

        # ── Liberação ativa mas catraca negou = inconsistência ──
        if self.active_liberations and is_denied:
            best_lib = max(self.active_liberations, key=lambda r: r.priority)
            self.precise_reason = (
                f'INCONSISTÊNCIA: A regra de liberação "{best_lib.rule_name}" está ATIVA '
                f"(horário OK, usuário vinculado), mas a catraca NEGOU o acesso. "
                f"Causas prováveis: (1) dados desincronizados — execute uma sincronização completa, "
                f"(2) biometria/cartão expirado ou não cadastrado na catraca, "
                f"(3) anti-passback ativo (tentativa de entrar 2x seguidas sem sair), "
                f"(4) regra modificada na catraca diretamente sem sincronizar com o sistema"
            )
            return self.precise_reason

        # ── Sem liberação ativa (fora do horário) ──
        if self.inactive_liberations and not self.active_liberations:
            rules_detail = []
            for r in self.inactive_liberations:
                rules_detail.append(f'"{r.rule_name}" ({r.time_detail})')
            rules_str = ", ".join(rules_detail)
            self.precise_reason = (
                f"NEGADO: Usuário está FORA DO HORÁRIO permitido. "
                f"Regras de liberação existem mas estão inativas agora: {rules_str}"
            )
            return self.precise_reason

        # ── Acesso concedido ──
        if is_granted and self.active_liberations:
            best_lib = max(self.active_liberations, key=lambda r: r.priority)
            self.precise_reason = (
                f'PERMITIDO: Regra "{best_lib.rule_name}" (liberação, prioridade {best_lib.priority}) '
                f"está ativa no horário atual"
            )
            return self.precise_reason

        if is_granted:
            self.precise_reason = "PERMITIDO: Acesso concedido pela catraca"
            return self.precise_reason

        # ── Fallback (não deveria chegar aqui) ──
        self.precise_reason = (
            "NEGADO: Motivo não determinado — verifique as configurações manualmente"
        )
        return self.precise_reason


class AccessVerificationService:
    """
    Analisa um log de acesso recebido da catraca e determina
    o motivo EXATO do resultado (concessão ou negação).

    Utiliza os models Django:
    - User, Portal, AccessRule, AccessRuleTimeZone, TimeZone, TimeSpan
    - PortalAccessRule, UserAccessRule, GroupAccessRule, UserGroup
    """

    def analyze_access(
        self,
        user_id: Optional[int],
        portal_id: Optional[int],
        event_type: int,
        access_rule_id: Optional[int] = None,
        device_name: str = "",
        access_time: Optional[datetime] = None,
        device=None,
    ) -> str:
        """
        Analisa um evento de acesso e retorna uma string com o diagnóstico
        PRECISO, logando no console.

        Args:
            device: Instância de Device (model Django) para consultar a catraca
                    quando houver inconsistência. Se None, não consulta.

        Returns:
            str: Diagnóstico completo do acesso
        """
        from src.core.user.infra.user_django_app.models import User
        from src.core.control_id.infra.control_id_django_app.models import (
            Portal,
            AccessRule,
        )

        if access_time is None:
            access_time = timezone.now()

        event_desc = EVENT_DESCRIPTIONS.get(
            event_type, f"Evento desconhecido ({event_type})"
        )
        is_granted = event_type in GRANTED_EVENTS
        is_denied = event_type in DENIED_EVENTS

        verdict = AccessVerdict()

        lines: List[str] = []
        lines.append("")
        lines.append("=" * 70)
        lines.append(f"🚪 VERIFICAÇÃO DE ACESSO — {device_name}")
        lines.append(f"   Horário: {access_time.strftime('%d/%m/%Y %H:%M:%S')}")
        lines.append("=" * 70)

        # ── 1. Resultado da catraca ──
        if is_granted:
            lines.append(f"   ✅ Resultado: {event_desc}")
        elif is_denied:
            lines.append(f"   ❌ Resultado: {event_desc}")
        else:
            lines.append(f"   ⚠️  Resultado: {event_desc}")

        # ── 2. Identificação do usuário ──
        user = None
        if user_id and int(user_id) > 0:
            user = User.objects.filter(id=user_id).first()

        if user:
            verdict.user_found = True
            lines.append(f"   👤 Usuário: {user.name} (ID: {user.id})")  # type: ignore[attr-defined]
            if hasattr(user, "registration") and user.registration:
                lines.append(f"      Matrícula: {user.registration}")
            # Verifica se está marcado como visitante
            if hasattr(user, "user_type_id") and user.user_type_id == 1:
                lines.append(
                    "   ⚠️  VISITANTE (user_type_id=1) — firmware pode restringir acesso!"
                )
        else:
            verdict.user_found = False
            lines.append(f"   👤 Usuário: NÃO IDENTIFICADO (user_id={user_id})")
            verdict.compute_precise_reason(event_type)
            lines.append("")
            lines.append(f"   🔍 MOTIVO: {verdict.precise_reason}")
            lines.append("=" * 70)
            diagnosis = "\n".join(lines)
            self._log_diagnosis(diagnosis, is_granted)
            return diagnosis

        # ── 3. Informações do portal ──
        portal = None
        if portal_id:
            portal = Portal.objects.filter(id=portal_id).first()

        if portal:
            verdict.portal_found = True
            lines.append(f"   🚪 Portal: {portal.name} (ID: {portal.id})")  # type: ignore[attr-defined]
            if hasattr(portal, "area_from") and portal.area_from:
                lines.append(
                    f"      De: {portal.area_from.name} → Para: {portal.area_to.name}"
                )
        else:
            verdict.portal_found = False
            lines.append(f"   🚪 Portal: não encontrado (portal_id={portal_id})")

        # ── 4. Regra de acesso informada pela catraca ──
        if access_rule_id:
            rule_used = AccessRule.objects.filter(id=access_rule_id).first()
            if rule_used:
                rule_type = "LIBERAÇÃO" if rule_used.type == 1 else "BLOQUEIO"
                lines.append(
                    f"   📋 Regra usada pela catraca: {rule_used.name} (Tipo: {rule_type}, Prioridade: {rule_used.priority})"
                )

        # ── 5. Análise COMPLETA das regras com veredito ──
        lines.append("")
        lines.append("   📊 ANÁLISE DAS REGRAS DE ACESSO:")
        lines.append("   " + "-" * 50)

        rule_lines = self._analyze_rules_with_verdict(
            user=user,
            portal=portal,
            access_time=access_time,
            verdict=verdict,
        )

        for line in rule_lines:
            lines.append(f"   {line}")

        # ── 6. DIAGNÓSTICO FINAL PRECISO ──
        verdict.compute_precise_reason(event_type)

        lines.append("")
        lines.append("   " + "-" * 50)
        lines.append(f"   🔍 MOTIVO: {verdict.precise_reason}")

        # ── 7. Se INCONSISTÊNCIA, consultar catraca para descobrir o que está diferente ──
        if "INCONSISTÊNCIA" in verdict.precise_reason and device and user:
            lines.append("")
            lines.append("   🔎 VERIFICAÇÃO CRUZADA COM A CATRACA:")
            lines.append("   " + "-" * 50)
            try:
                catraca_lines = self._cross_check_with_catraca(
                    device=device,
                    user_id=user.id,  # type: ignore[attr-defined]
                    user_name=user.name,  # type: ignore[attr-defined]
                    portal_id=portal.id if portal else None,  # type: ignore[attr-defined]
                    portal_name=portal.name if portal else None,  # type: ignore[attr-defined]
                )
                for cl in catraca_lines:
                    lines.append(f"   {cl}")
            except Exception as e:
                lines.append(f"   ⚠️  Erro ao consultar catraca: {e}")

        lines.append("=" * 70)
        lines.append("")

        diagnosis = "\n".join(lines)
        self._log_diagnosis(diagnosis, is_granted)
        return diagnosis

    def _analyze_rules_with_verdict(
        self,
        user,
        portal,
        access_time: datetime,
        verdict: AccessVerdict,
    ) -> List[str]:
        """
        Analisa todas as regras de acesso e preenche o AccessVerdict
        com dados estruturados para diagnóstico preciso.
        """
        from src.core.control_id.infra.control_id_django_app.models.portal_access_rule import (
            PortalAccessRule,
        )
        from src.core.control_id.infra.control_id_django_app.models.user_access_rule import (
            UserAccessRule,
        )
        from src.core.control_id.infra.control_id_django_app.models.group_access_rules import (
            GroupAccessRule,
        )
        from src.core.control_id.infra.control_id_django_app.models.user_groups import (
            UserGroup,
        )

        lines: List[str] = []

        if not portal:
            verdict.portal_found = False
            verdict.portal_has_rules = False
            lines.append("⚠️  Sem portal — não é possível verificar regras")
            return lines

        # Regras vinculadas ao portal
        portal_rules = PortalAccessRule.objects.filter(portal=portal).select_related(
            "access_rule"
        )

        if not portal_rules.exists():
            verdict.portal_has_rules = False
            lines.append("⚠️  Portal sem regras de acesso vinculadas")
            return lines

        verdict.portal_has_rules = True

        # Regras do usuário (diretas)
        user_rule_ids = set(
            UserAccessRule.objects.filter(user=user).values_list(
                "access_rule_id", flat=True
            )
        )

        # Regras do usuário (via grupos)
        user_group_ids = list(
            UserGroup.objects.filter(user=user).values_list("group_id", flat=True)
        )
        group_rule_ids = set(
            GroupAccessRule.objects.filter(group_id__in=user_group_ids).values_list(
                "access_rule_id", flat=True
            )
        )

        all_user_rule_ids = user_rule_ids | group_rule_ids
        verdict.user_has_any_rule = len(all_user_rule_ids) > 0

        lines.append(f"Regras do usuário (diretas): {len(user_rule_ids)}")
        lines.append(f"Regras via grupo:            {len(group_rule_ids)}")
        lines.append("")

        # Calcular segundos do dia e dia da semana
        segundos_dia = (
            access_time.hour * 3600 + access_time.minute * 60 + access_time.second
        )
        dia_semana = access_time.weekday()  # 0=segunda
        dias_nome = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        dia_atual_nome = dias_nome[dia_semana]

        # Verificar cada regra do portal
        for pr in portal_rules:
            rule = pr.access_rule
            rule_type_str = "LIBERAÇÃO" if rule.type == 1 else "BLOQUEIO"
            icon = "🟢" if rule.type == 1 else "🔴"

            # Verifica se o usuário tem essa regra
            user_has_rule = rule.id in all_user_rule_ids  # type: ignore[attr-defined]
            via_group = rule.id in group_rule_ids and rule.id not in user_rule_ids  # type: ignore[attr-defined]

            if user_has_rule:
                verdict.user_has_any_matching_rule = True

            has_rule_text = (
                "✔ Usuário possui esta regra"
                + (" (via grupo)" if via_group else " (direta)")
                if user_has_rule
                else "✖ Usuário NÃO possui esta regra"
            )

            lines.append(
                f"{icon} Regra: {rule.name} (Tipo: {rule_type_str}, Prioridade: {rule.priority})"
            )
            lines.append(f"   {has_rule_text}")

            if not user_has_rule:
                rv = RuleVerdict(
                    rule_name=rule.name,
                    rule_type=rule.type,
                    priority=rule.priority,
                    user_has_rule=False,
                    time_ok=False,
                    via_group=False,
                )
                verdict.unlinked_rules.append(rv)
                lines.append("   → Regra não se aplica a este usuário")
                lines.append("")
                continue

            # Verificar horários
            horario_ok, horario_detail, time_summary = self._check_time_zones(
                rule, segundos_dia, dia_semana
            )

            for detail in horario_detail:
                lines.append(f"   {detail}")

            rv = RuleVerdict(
                rule_name=rule.name,
                rule_type=rule.type,
                priority=rule.priority,
                user_has_rule=True,
                time_ok=horario_ok,
                via_group=via_group,
                time_detail=time_summary,
            )

            if rule.type == 0 and horario_ok:
                verdict.active_blocks.append(rv)
                lines.append(
                    "   🔴 BLOQUEIO ATIVO — regra de bloqueio dentro do horário"
                )
            elif rule.type == 1 and horario_ok:
                verdict.active_liberations.append(rv)
                lines.append(
                    "   🟢 LIBERAÇÃO ATIVA — regra de liberação dentro do horário"
                )
            elif rule.type == 1 and not horario_ok:
                verdict.inactive_liberations.append(rv)
                lines.append(
                    f"   ⏰ FORA DO HORÁRIO — regra de liberação inativa agora ({dia_atual_nome} {access_time.strftime('%H:%M')})"
                )
            elif rule.type == 0 and not horario_ok:
                lines.append("   ⏰ Regra de bloqueio inativa (fora do horário)")

            lines.append("")

        return lines

    def _check_time_zones(
        self, access_rule, segundos_dia: int, dia_semana: int
    ) -> Tuple[bool, List[str], str]:
        """
        Verifica se o horário atual está dentro das TimeZones da regra.

        Returns:
            (dentro_horario, lista_de_detalhes, resumo_horario)
        """
        from src.core.control_id.infra.control_id_django_app.models.access_rule_timezone import (
            AccessRuleTimeZone,
        )
        from src.core.control_id.infra.control_id_django_app.models.timespan import (
            TimeSpan,
        )

        details: List[str] = []
        summary_parts: List[str] = []

        artz_qs = AccessRuleTimeZone.objects.filter(
            access_rule=access_rule
        ).select_related("time_zone")

        if not artz_qs.exists():
            details.append("⏰ Sem restrição de horário (acesso livre)")
            return True, details, "sem restrição (livre)"

        dias_nome = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        dia_atual_nome = dias_nome[dia_semana]

        for artz in artz_qs:
            tz = artz.time_zone
            details.append(f"⏰ Zona horária: {tz.name}")

            spans = TimeSpan.objects.filter(time_zone=tz)

            if not spans.exists():
                details.append("   (sem intervalos configurados)")
                summary_parts.append(f"{tz.name}: sem intervalos")
                continue

            for span in spans:
                dias_flags = [
                    span.mon,
                    span.tue,
                    span.wed,
                    span.thu,
                    span.fri,
                    span.sat,
                    span.sun,
                ]
                dias_ativos = [
                    dias_nome[i] for i, flag in enumerate(dias_flags) if flag
                ]

                start_h = span.start // 3600
                start_m = (span.start % 3600) // 60
                end_h = span.end // 3600
                end_m = (span.end % 3600) // 60

                horario_str = f"{start_h:02d}:{start_m:02d} - {end_h:02d}:{end_m:02d}"
                dias_str = ", ".join(dias_ativos) if dias_ativos else "Nenhum dia"

                span_summary = f"{horario_str} [{dias_str}]"
                summary_parts.append(span_summary)

                dia_ok = dias_flags[dia_semana]
                horario_ok = span.start <= segundos_dia <= span.end

                if dia_ok and horario_ok:
                    details.append(
                        f"   ✔ {horario_str} [{dias_str}] ← DENTRO deste intervalo ({dia_atual_nome})"
                    )
                    return True, details, span_summary
                elif dia_ok and not horario_ok:
                    details.append(
                        f"   ✖ {horario_str} [{dias_str}] ← Dia correto ({dia_atual_nome}) mas FORA do horário"
                    )
                else:
                    details.append(
                        f"   ✖ {horario_str} [{dias_str}] ← Hoje ({dia_atual_nome}) não está nos dias permitidos"
                    )

        full_summary = "; ".join(summary_parts) if summary_parts else "nenhum intervalo"
        details.append("   → Resultado: FORA do horário permitido")
        return False, details, full_summary

    def _cross_check_with_catraca(
        self,
        device,
        user_id: int,
        user_name: str,
        portal_id: Optional[int],
        portal_name: Optional[str],
    ) -> List[str]:
        """
        Consulta a catraca diretamente para descobrir diferenças entre
        o banco Django e o que está de fato configurado no equipamento.

        Verifica:
        1. Se o usuário existe na catraca
        2. Se o usuário tem regras de acesso na catraca
        3. Se o usuário pertence a grupos na catraca
        4. Se os grupos têm regras na catraca
        5. Se o portal tem regras de acesso na catraca
        6. Se o usuário tem templates biométricos/cartões na catraca
        """
        lines: List[str] = []
        base_url = (
            f"http://{device.ip}"
            if not device.ip.startswith(("http://", "https://"))
            else device.ip
        )

        # Login na catraca
        try:
            resp = requests.post(
                f"{base_url}/login.fcgi",
                json={"login": device.username, "password": device.password},
                timeout=5,
            )
            resp.raise_for_status()
            session = resp.json().get("session")
            if not session:
                lines.append("❌ Não foi possível logar na catraca")
                return lines
        except Exception as e:
            lines.append(f"❌ Catraca inacessível: {e}")
            return lines

        def _load(
            obj: str, where: Optional[Dict] = None, fields: Optional[List[str]] = None
        ) -> List[Dict]:
            payload: Dict[str, Any] = {"object": obj}
            if where:
                payload["where"] = where
            if fields:
                payload["fields"] = fields
            try:
                r = requests.post(
                    f"{base_url}/load_objects.fcgi?session={session}",
                    json=payload,
                    timeout=8,
                )
                if r.status_code != 200:
                    return []
                return r.json().get(obj, [])
            except Exception:
                return []

        problems_found = 0

        # ── 1. Usuário existe na catraca? ──
        catraca_users = _load("users", where={"users": {"id": user_id}})
        if not catraca_users:
            lines.append(
                f"❌ Usuário '{user_name}' (ID {user_id}) NÃO EXISTE na catraca!"
            )
            lines.append("   → Solução: Execute uma sincronização de usuários")
            problems_found += 1
        else:
            cu = catraca_users[0]
            lines.append(
                f"✔ Usuário existe na catraca: {cu.get('name', '?')} (ID {cu.get('id')})"
            )

            # Verificar se o usuário está marcado como visitante na catraca
            catraca_user_type = cu.get("user_type_id")
            if catraca_user_type is not None and int(catraca_user_type) == 1:
                lines.append(
                    "⚠️  Usuário marcado como VISITANTE (user_type_id=1) na catraca!"
                )
                lines.append(
                    "   → Visitantes podem ter restrições adicionais de acesso no firmware."
                )
                lines.append(
                    '   → Se não é visitante, corrija via PATCH /api/users/<id>/ com {"user_type_id": 0}'
                )
                problems_found += 1

        # ── 2. Regras DIRETAS do usuário na catraca ──
        catraca_user_rules = _load(
            "user_access_rules",
            where={"user_access_rules": {"user_id": user_id}},
        )
        if catraca_user_rules:
            rule_ids = [str(r.get("access_rule_id")) for r in catraca_user_rules]
            lines.append(
                f"✔ Regras diretas na catraca: {len(catraca_user_rules)} (IDs: {', '.join(rule_ids)})"
            )
        else:
            lines.append("ℹ️  Sem regras diretas na catraca (pode ser via grupo)")

        # ── 3. Grupos do usuário na catraca ──
        catraca_user_groups = _load(
            "user_groups",
            where={"user_groups": {"user_id": user_id}},
        )
        if catraca_user_groups:
            group_ids = [int(g.get("group_id", 0)) for g in catraca_user_groups]
            lines.append(
                f"✔ Grupos na catraca: {len(catraca_user_groups)} (IDs: {', '.join(map(str, group_ids))})"
            )

            # ── 4. Regras dos grupos na catraca ──
            for gid in group_ids:
                catraca_group_rules = _load(
                    "group_access_rules",
                    where={"group_access_rules": {"group_id": gid}},
                )
                if catraca_group_rules:
                    grule_ids = [
                        str(r.get("access_rule_id")) for r in catraca_group_rules
                    ]
                    lines.append(
                        f"   ✔ Grupo {gid}: {len(catraca_group_rules)} regra(s) (IDs: {', '.join(grule_ids)})"
                    )
                else:
                    lines.append(f"   ❌ Grupo {gid}: SEM regras de acesso na catraca!")
                    lines.append("      → Solução: Sincronize group_access_rules")
                    problems_found += 1
        else:
            lines.append("❌ Usuário NÃO pertence a nenhum grupo na catraca!")
            lines.append("   → Solução: Sincronize user_groups")
            problems_found += 1

        # ── 5. Portal tem regras na catraca? ──
        if portal_id:
            catraca_portal_rules = _load(
                "portal_access_rules",
                where={"portal_access_rules": {"portal_id": portal_id}},
            )
            if catraca_portal_rules:
                prule_ids = [str(r.get("access_rule_id")) for r in catraca_portal_rules]
                lines.append(
                    f"✔ Portal '{portal_name}': {len(catraca_portal_rules)} regra(s) (IDs: {', '.join(prule_ids)})"
                )

                # Comparar: as regras do usuário/grupo coincidem com as do portal?
                user_all_rules = set()
                for r in catraca_user_rules:
                    user_all_rules.add(int(r.get("access_rule_id", 0)))
                for gid in [int(g.get("group_id", 0)) for g in catraca_user_groups]:
                    for gr in _load(
                        "group_access_rules",
                        where={"group_access_rules": {"group_id": gid}},
                    ):
                        user_all_rules.add(int(gr.get("access_rule_id", 0)))

                portal_rule_set = {
                    int(r.get("access_rule_id", 0)) for r in catraca_portal_rules
                }
                matching = user_all_rules & portal_rule_set

                if matching:
                    lines.append(
                        f"✔ Regras em comum (usuário ∩ portal) na catraca: {matching}"
                    )
                else:
                    lines.append(
                        "❌ NENHUMA regra em comum entre usuário e portal NA CATRACA!"
                    )
                    lines.append(
                        f"   Regras do usuário/grupos: {user_all_rules or 'nenhuma'}"
                    )
                    lines.append(f"   Regras do portal: {portal_rule_set}")
                    lines.append(
                        "   → Solução: Sincronize portal_access_rules e group_access_rules"
                    )
                    problems_found += 1
            else:
                lines.append(f"❌ Portal '{portal_name}' SEM regras na catraca!")
                lines.append("   → Solução: Sincronize portal_access_rules")
                problems_found += 1

        # ── 6. Time zones das regras em comum ──
        # Verifica se as regras que casam (usuário ∩ portal) têm time_zones
        # e se os time_spans cobrem o horário atual
        if portal_id:
            # Coleta regras do usuário (diretas + via grupo)
            user_all_rules_set = set()
            for r in catraca_user_rules:
                user_all_rules_set.add(int(r.get("access_rule_id", 0)))
            for gid in [int(g.get("group_id", 0)) for g in catraca_user_groups]:
                for gr in _load(
                    "group_access_rules",
                    where={"group_access_rules": {"group_id": gid}},
                ):
                    user_all_rules_set.add(int(gr.get("access_rule_id", 0)))

            portal_rule_ids = set()
            for r in _load(
                "portal_access_rules",
                where={"portal_access_rules": {"portal_id": portal_id}},
            ):
                portal_rule_ids.add(int(r.get("access_rule_id", 0)))

            matching_rules = user_all_rules_set & portal_rule_ids

            now = timezone.localtime()
            now_seconds = now.hour * 3600 + now.minute * 60 + now.second
            day_map = {
                0: "mon",
                1: "tue",
                2: "wed",
                3: "thu",
                4: "fri",
                5: "sat",
                6: "sun",
            }
            today_field = day_map.get(now.weekday(), "mon")

            for rule_id in sorted(matching_rules):
                # Busca access_rule_time_zones na catraca
                art_zones = _load(
                    "access_rule_time_zones",
                    where={"access_rule_time_zones": {"access_rule_id": rule_id}},
                )
                if not art_zones:
                    lines.append(
                        f"❌ Regra {rule_id}: SEM time_zone vinculada na catraca!"
                    )
                    lines.append("   → Solução: Sincronize access_rule_time_zones")
                    problems_found += 1
                    continue

                tz_ids = [int(z.get("time_zone_id", 0)) for z in art_zones]
                lines.append(f"✔ Regra {rule_id}: time_zone(s) na catraca: {tz_ids}")

                # Para cada time_zone, verifica os time_spans
                rule_covers_now = False
                for tz_id in tz_ids:
                    spans = _load(
                        "time_spans",
                        where={"time_spans": {"time_zone_id": tz_id}},
                    )
                    if not spans:
                        lines.append(
                            f"   ❌ Time zone {tz_id}: SEM time_spans na catraca!"
                        )
                        lines.append("      → Solução: Sincronize time_spans")
                        problems_found += 1
                        continue

                    for span in spans:
                        start = int(span.get("start", 0))
                        end = int(span.get("end", 0))
                        day_active = int(span.get(today_field, 0))

                        start_h, start_m = divmod(start, 3600)
                        start_m //= 60
                        end_h, end_m = divmod(end, 3600)
                        end_m //= 60

                        if day_active and start <= now_seconds <= end:
                            rule_covers_now = True
                            lines.append(
                                f"   ✔ Time zone {tz_id}: {start_h:02d}:{start_m:02d}-{end_h:02d}:{end_m:02d} "
                                f"cobre horário atual ({now.strftime('%H:%M:%S')}, {today_field})"
                            )
                        elif not day_active:
                            lines.append(
                                f"   ⚠️  Time zone {tz_id}: {start_h:02d}:{start_m:02d}-{end_h:02d}:{end_m:02d} "
                                f"— dia '{today_field}' DESATIVADO na catraca"
                            )
                        else:
                            lines.append(
                                f"   ⚠️  Time zone {tz_id}: {start_h:02d}:{start_m:02d}-{end_h:02d}:{end_m:02d} "
                                f"— horário atual ({now.strftime('%H:%M:%S')}) FORA da faixa"
                            )

                if not rule_covers_now:
                    lines.append(
                        f"   ❌ Regra {rule_id}: NENHUM time_span cobre o horário atual na catraca!"
                    )
                    lines.append("      → Esta é provavelmente a causa da negação!")
                    problems_found += 1

        # ── 7. Templates/cartões do usuário ──
        catraca_templates = _load(
            "templates",
            where={"templates": {"user_id": user_id}},
            fields=["id", "user_id"],
        )
        catraca_cards = _load(
            "cards",
            where={"cards": {"user_id": user_id}},
            fields=["id", "user_id", "value"],
        )

        if catraca_templates:
            lines.append(
                f"✔ Templates biométricos na catraca: {len(catraca_templates)}"
            )
        else:
            lines.append(
                "⚠️  Sem templates biométricos na catraca (facial/digital não cadastrado)"
            )
            lines.append("   → Se o acesso é por biometria, este é o problema!")
            problems_found += 1

        if catraca_cards:
            card_values = [str(c.get("value", "?")) for c in catraca_cards]
            lines.append(
                f"✔ Cartões na catraca: {len(catraca_cards)} (valores: {', '.join(card_values)})"
            )
        else:
            lines.append("⚠️  Sem cartões RFID na catraca")
            lines.append("   → Se o acesso é por cartão, este é o problema!")

        # ── 8. PINs de identificação do usuário ──
        catraca_pins = _load(
            "pins",
            where={"pins": {"user_id": user_id}},
        )
        if catraca_pins:
            pin_values = [str(p.get("value", "?")) for p in catraca_pins]
            lines.append(f"✔ PIN de identificação na catraca: {', '.join(pin_values)}")
        else:
            lines.append(
                "❌ Sem PIN de identificação na catraca (tabela 'pins' vazia para este usuário)!"
            )
            lines.append("   → Se o acesso é por PIN, este é o problema!")
            lines.append(
                "   → Solução: Recrie ou atualize o usuário para sincronizar o PIN"
            )
            problems_found += 1

        # Verifica se o PIN do banco bate com o da catraca
        if catraca_pins:
            try:
                from src.core.user.infra.user_django_app.models import User as UserModel

                db_user = UserModel.objects.filter(id=user_id).first()
                if db_user and db_user.pin:
                    catraca_pin_value = str(catraca_pins[0].get("value", ""))
                    if catraca_pin_value != db_user.pin:
                        lines.append(
                            f"⚠️  PIN divergente! Banco: {db_user.pin} | Catraca: {catraca_pin_value}"
                        )
                        lines.append(
                            "   → Solução: Atualize o usuário para ressincronizar o PIN"
                        )
                        problems_found += 1
                    else:
                        lines.append(
                            f"✔ PIN banco ({db_user.pin}) = PIN catraca ({catraca_pin_value})"
                        )
            except Exception:
                pass

        # ── Resumo ──
        lines.append("")
        if problems_found == 0:
            lines.append(
                "✔ TUDO SINCRONIZADO — dados na catraca batem com o banco. "
                "Causa provável: anti-passback ou restrição de firmware."
            )
        else:
            lines.append(
                f"❌ {problems_found} PROBLEMA(S) DE SINCRONIZAÇÃO encontrado(s)!"
            )
            lines.append(
                "   → Execute uma sincronização completa via API: POST /api/config/sync/"
            )

        return lines

    def _log_diagnosis(self, diagnosis: str, is_granted: bool):
        """Loga o diagnóstico no nível apropriado"""
        if is_granted:
            logger.info(diagnosis)
        else:
            logger.warning(diagnosis)


# Instância global
access_verifier = AccessVerificationService()
