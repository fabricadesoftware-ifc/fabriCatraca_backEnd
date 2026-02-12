"""
Serviço de Verificação de Acesso — integrado ao sistema de Monitor

Quando a catraca envia um log de acesso via push (Monitor),
este serviço analisa as regras de acesso configuradas no banco
e loga no console o MOTIVO da decisão (acesso concedido ou negado).

Baseado na lógica do script 'verificação catraca.py', agora usando
os models Django e o ORM.
"""

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


class AccessVerificationService:
    """
    Analisa um log de acesso recebido da catraca e determina
    o motivo detalhado do resultado (concessão ou negação).

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
        completo, logando no console com nível INFO.

        Args:
            user_id:        ID do usuário (pode ser None/0 se não identificado)
            portal_id:      ID do portal (lado da catraca)
            event_type:     Código numérico do evento (EventType)
            access_rule_id: ID da regra de acesso que a catraca usou (pode ser None)
            device_name:    Nome do dispositivo (para log)
            access_time:    Horário do evento (se None, usa agora)

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
            lines.append(f"   👤 Usuário: {user.name} (ID: {user.id})")  # type: ignore[attr-defined]
            if user.registration:
                lines.append(f"      Matrícula: {user.registration}")
        else:
            lines.append(f"   👤 Usuário: NÃO IDENTIFICADO (user_id={user_id})")
            if is_denied:
                lines.append(
                    "      ↳ Motivo provável: Pessoa não reconhecida pelo sistema"
                )
            lines.append("-" * 70)
            diagnosis = "\n".join(lines)
            self._log_diagnosis(diagnosis, is_granted)
            return diagnosis

        # ── 3. Informações do portal ──
        portal = None
        if portal_id:
            portal = Portal.objects.filter(id=portal_id).first()

        if portal:
            lines.append(f"   🚪 Portal: {portal.name} (ID: {portal.id})")  # type: ignore[attr-defined]
            if hasattr(portal, "area_from") and portal.area_from:
                lines.append(
                    f"      De: {portal.area_from.name} → Para: {portal.area_to.name}"
                )
        else:
            lines.append(f"   🚪 Portal: não encontrado (portal_id={portal_id})")

        # ── 4. Regra de acesso usada pela catraca ──
        if access_rule_id:
            rule_used = AccessRule.objects.filter(id=access_rule_id).first()
            if rule_used:
                rule_type = "LIBERAÇÃO" if rule_used.type == 1 else "BLOQUEIO"
                lines.append(
                    f"   📋 Regra usada: {rule_used.name} (Tipo: {rule_type}, Prioridade: {rule_used.priority})"
                )

        # ── 5. Análise das regras configuradas ──
        lines.append("")
        lines.append("   📊 ANÁLISE DAS REGRAS DE ACESSO:")
        lines.append("   " + "-" * 50)

        reasons = self._analyze_rules(
            user=user,
            portal=portal,
            access_time=access_time,
        )

        if reasons:
            for reason in reasons:
                lines.append(f"   {reason}")
        else:
            lines.append(
                "      Nenhuma regra de acesso encontrada para este usuário/portal"
            )
            if is_denied:
                lines.append(
                    "      ↳ Motivo provável: Sem regras de liberação configuradas"
                )

        # ── 6. Diagnóstico final ──
        lines.append("")
        lines.append("   " + "-" * 50)
        if is_granted:
            lines.append("   ✅ DIAGNÓSTICO: Acesso PERMITIDO pela catraca")
        elif is_denied:
            lines.append("   ❌ DIAGNÓSTICO: Acesso NEGADO pela catraca")
            # Motivos comuns de negação
            denial_reasons = self._infer_denial_reasons(
                user=user, portal=portal, event_type=event_type, access_time=access_time
            )
            for dr in denial_reasons:
                lines.append(f"      ↳ {dr}")
        else:
            lines.append(f"   ⚠️  DIAGNÓSTICO: Evento informativo ({event_desc})")

        lines.append("=" * 70)
        lines.append("")

        diagnosis = "\n".join(lines)
        self._log_diagnosis(diagnosis, is_granted)
        return diagnosis

    def _analyze_rules(
        self,
        user,
        portal,
        access_time: datetime,
    ) -> List[str]:
        """
        Analisa todas as regras de acesso aplicáveis ao usuário/portal
        e retorna linhas de diagnóstico.
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
            lines.append("   ⚠️  Sem portal — não é possível verificar regras")
            return lines

        # Regras vinculadas ao portal
        portal_rules = PortalAccessRule.objects.filter(portal=portal).select_related(
            "access_rule"
        )

        if not portal_rules.exists():
            lines.append("   ⚠️  Portal sem regras de acesso vinculadas")
            return lines

        # Regras do usuário (diretas)
        user_rule_ids = set(
            UserAccessRule.objects.filter(user=user).values_list(
                "access_rule_id", flat=True
            )
        )

        # Regras do usuário (via grupos)
        user_group_ids = UserGroup.objects.filter(user=user).values_list(
            "group_id", flat=True
        )
        group_rule_ids = set(
            GroupAccessRule.objects.filter(group_id__in=user_group_ids).values_list(
                "access_rule_id", flat=True
            )
        )

        all_user_rule_ids = user_rule_ids | group_rule_ids

        if all_user_rule_ids:
            lines.append(f"   Regras do usuário (diretas): {len(user_rule_ids)}")
            lines.append(f"   Regras via grupo:            {len(group_rule_ids)}")
        else:
            lines.append("   ⚠️  Usuário sem regras de acesso (direta ou via grupo)")

        lines.append("")

        # Verificar cada regra do portal
        segundos_dia = (
            access_time.hour * 3600 + access_time.minute * 60 + access_time.second
        )
        dia_semana = access_time.weekday()  # 0=segunda

        for pr in portal_rules:
            rule = pr.access_rule
            rule_type = "LIBERAÇÃO" if rule.type == 1 else "BLOQUEIO"
            icon = "🟢" if rule.type == 1 else "🔴"

            # Verifica se o usuário tem essa regra
            user_has_rule = rule.id in all_user_rule_ids  # type: ignore[attr-defined]
            has_rule_text = (
                "✔ Usuário possui" if user_has_rule else "✖ Usuário NÃO possui"
            )

            lines.append(
                f"   {icon} Regra: {rule.name} (Tipo: {rule_type}, Prioridade: {rule.priority})"
            )
            lines.append(f"      {has_rule_text} esta regra")

            if not user_has_rule:
                lines.append("      → Regra não se aplica a este usuário")
                lines.append("")
                continue

            # Verificar horários
            horario_ok, horario_detail = self._check_time_zones(
                rule, segundos_dia, dia_semana
            )

            for detail in horario_detail:
                lines.append(f"      {detail}")

            if rule.type == 0 and horario_ok and user_has_rule:
                lines.append(
                    "      🔴 BLOQUEIO ATIVO — regra de bloqueio dentro do horário"
                )
            elif rule.type == 1 and horario_ok and user_has_rule:
                lines.append(
                    "      🟢 LIBERAÇÃO ATIVA — regra de liberação dentro do horário"
                )
            elif rule.type == 1 and not horario_ok and user_has_rule:
                lines.append(
                    "      ⏰ FORA DO HORÁRIO — regra de liberação inativa neste momento"
                )

            lines.append("")

        return lines

    def _check_time_zones(
        self, access_rule, segundos_dia: int, dia_semana: int
    ) -> Tuple[bool, List[str]]:
        """
        Verifica se o horário atual está dentro das TimeZones da regra.

        Args:
            access_rule: Instância de AccessRule
            segundos_dia: Segundos desde meia-noite
            dia_semana: 0=segunda, 6=domingo

        Returns:
            (dentro_horario, lista_de_detalhes)
        """
        from src.core.control_Id.infra.control_id_django_app.models.access_rule_timezone import (
            AccessRuleTimeZone,
        )
        from src.core.control_Id.infra.control_id_django_app.models.timespan import (
            TimeSpan,
        )

        details: List[str] = []

        artz_qs = AccessRuleTimeZone.objects.filter(
            access_rule=access_rule
        ).select_related("time_zone")

        if not artz_qs.exists():
            details.append("⏰ Sem restrição de horário (acesso livre)")
            return True, details

        dias_nome = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        dia_atual_nome = dias_nome[dia_semana]

        for artz in artz_qs:
            tz = artz.time_zone
            details.append(f"⏰ Zona horária: {tz.name}")

            spans = TimeSpan.objects.filter(time_zone=tz)

            if not spans.exists():
                details.append("   (sem intervalos configurados)")
                continue

            for span in spans:
                # Dias da semana do span
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

                # Verifica se é dia e horário válido
                dia_ok = dias_flags[dia_semana]
                horario_ok = span.start <= segundos_dia <= span.end

                if dia_ok and horario_ok:
                    details.append(
                        f"   ✔ {horario_str} [{dias_str}] ← DENTRO deste intervalo ({dia_atual_nome})"
                    )
                    return True, details
                elif dia_ok and not horario_ok:
                    details.append(
                        f"   ✖ {horario_str} [{dias_str}] ← Dia correto ({dia_atual_nome}) mas FORA do horário"
                    )
                else:
                    details.append(
                        f"   ✖ {horario_str} [{dias_str}] ← Hoje ({dia_atual_nome}) não está nos dias permitidos"
                    )

        details.append("   → Resultado: FORA do horário permitido")
        return False, details

    def _infer_denial_reasons(
        self,
        user,
        portal,
        event_type: int,
        access_time: datetime,
    ) -> List[str]:
        """
        Infere os motivos mais prováveis de uma negação de acesso.
        """
        reasons: List[str] = []

        if event_type == 3:  # NÃO_IDENTIFICADO
            reasons.append("Biometria/cartão não reconhecido pelo dispositivo")
            return reasons

        if event_type == 5:  # TEMPO_ESGOTADO
            reasons.append("Tempo de leitura biométrica/cartão esgotado")
            return reasons

        if event_type == 1:  # EQUIPAMENTO_INVALIDO
            reasons.append("Problema no equipamento/dispositivo")
            return reasons

        if event_type == 2:  # PARAMETRO_INVALIDO
            reasons.append("Credencial apresentada é inválida ou corrompida")
            return reasons

        if event_type == 9:  # NAO_E_ADM
            reasons.append("Tentativa de acesso administrativo por usuário comum")
            return reasons

        # Para evento 6 (ACESSO_NEGADO genérico), investigar regras
        if event_type == 6:
            from src.core.control_Id.infra.control_id_django_app.models.user_access_rule import (
                UserAccessRule,
            )
            from src.core.control_Id.infra.control_id_django_app.models.portal_access_rule import (
                PortalAccessRule,
            )
            from src.core.control_Id.infra.control_id_django_app.models.user_groups import (
                UserGroup,
            )
            from src.core.control_Id.infra.control_id_django_app.models.group_access_rules import (
                GroupAccessRule,
            )

            if not user:
                reasons.append("Usuário não encontrado no sistema")
                return reasons

            if not portal:
                reasons.append(
                    "Portal não encontrado — possível configuração incorreta"
                )
                return reasons

            # Verifica se o usuário tem alguma regra
            user_rules = UserAccessRule.objects.filter(user=user).count()
            user_group_ids = UserGroup.objects.filter(user=user).values_list(
                "group_id", flat=True
            )
            group_rules = GroupAccessRule.objects.filter(
                group_id__in=user_group_ids
            ).count()

            if user_rules == 0 and group_rules == 0:
                reasons.append("Usuário não possui NENHUMA regra de acesso configurada")
                return reasons

            # Verifica se tem regras no portal
            portal_rule_ids = set(
                PortalAccessRule.objects.filter(portal=portal).values_list(
                    "access_rule_id", flat=True
                )
            )

            if not portal_rule_ids:
                reasons.append("Portal não possui regras de acesso vinculadas")
                return reasons

            # Verifica interseção
            user_rule_ids = set(
                UserAccessRule.objects.filter(user=user).values_list(
                    "access_rule_id", flat=True
                )
            )
            group_rule_ids = set(
                GroupAccessRule.objects.filter(group_id__in=user_group_ids).values_list(
                    "access_rule_id", flat=True
                )
            )
            all_user_rule_ids = user_rule_ids | group_rule_ids

            matching_rules = portal_rule_ids & all_user_rule_ids
            if not matching_rules:
                reasons.append(
                    "Usuário não compartilha nenhuma regra de acesso com este portal"
                )
                reasons.append(
                    "(as regras do usuário não incluem as regras exigidas pelo portal)"
                )
                return reasons

            # Se tem regras em comum, provavelmente é horário
            reasons.append(
                "Possível causa: fora do horário permitido pelas regras de acesso"
            )
            reasons.append(
                "Ou: uma regra de BLOQUEIO ativa sobrepôs a regra de liberação"
            )

        return reasons

    def _log_diagnosis(self, diagnosis: str, is_granted: bool):
        """Loga o diagnóstico no nível apropriado"""
        if is_granted:
            logger.info(diagnosis)
        else:
            logger.warning(diagnosis)


# Instância global
access_verifier = AccessVerificationService()
