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
from typing import Optional, Tuple, List
from django.utils import timezone
import logging

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
    ) -> str:
        """
        Analisa um evento de acesso e retorna uma string com o diagnóstico
        PRECISO, logando no console.

        Returns:
            str: Diagnóstico completo do acesso
        """
        from src.core.user.infra.user_django_app.models import User
        from src.core.control_Id.infra.control_id_django_app.models import (
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
        from src.core.control_Id.infra.control_id_django_app.models.portal_access_rule import (
            PortalAccessRule,
        )
        from src.core.control_Id.infra.control_id_django_app.models.user_access_rule import (
            UserAccessRule,
        )
        from src.core.control_Id.infra.control_id_django_app.models.group_access_rules import (
            GroupAccessRule,
        )
        from src.core.control_Id.infra.control_id_django_app.models.user_groups import (
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
        from src.core.control_Id.infra.control_id_django_app.models.access_rule_timezone import (
            AccessRuleTimeZone,
        )
        from src.core.control_Id.infra.control_id_django_app.models.timespan import (
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

    def _log_diagnosis(self, diagnosis: str, is_granted: bool):
        """Loga o diagnóstico no nível apropriado"""
        if is_granted:
            logger.info(diagnosis)
        else:
            logger.warning(diagnosis)


# Instância global
access_verifier = AccessVerificationService()
