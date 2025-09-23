from typing import Dict, Any, List, Tuple
from django.db import transaction
from django.utils import timezone
from datetime import datetime

from src.core.control_Id.infra.control_id_django_app.models import (
    Template, Card, TimeZone, TimeSpan, Portal, AccessRule,
    PortalAccessRule, UserAccessRule, AccessRuleTimeZone, Area,
    UserGroup, CustomGroup, GroupAccessRule, AccessLogs, Device,
)
from src.core.user.infra.user_django_app.models import User


def persist_all(
    all_users: Dict[int, Any],
    all_time_zones: Dict[int, Any],
    all_time_spans: Dict[int, Any],
    all_access_rules: Dict[int, Any],
    all_portals: Dict[int, Any],
    all_areas: Dict[int, Any],
    all_templates: List[Any],
    all_cards: List[Any],
    all_user_access_rules: List[Any],
    all_portal_access_rules: List[Any],
    all_access_rule_time_zones: List[Any],
    all_group_access_rules: List[Any],
    all_user_groups: List[Any],
    all_groups: List[Any],
    all_access_logs: List[Any],
):
    with transaction.atomic():
        TimeZone.objects.all().delete()
        TimeSpan.objects.all().delete()
        AccessRule.objects.all().delete()
        Portal.objects.all().delete()
        Area.objects.all().delete()
        Template.objects.all().delete()
        Card.objects.all().delete()
        UserAccessRule.objects.all().delete()
        PortalAccessRule.objects.all().delete()
        AccessRuleTimeZone.objects.all().delete()
        UserGroup.objects.all().delete()
        CustomGroup.objects.all().delete()
        GroupAccessRule.objects.all().delete()

        remote_user_ids = {int(k) for k in all_users.keys()}
        User.objects.exclude(id__in=remote_user_ids).exclude(is_staff=True, is_superuser=True).delete()

        for user_data in all_users.values():
            devices = user_data.pop('devices')
            user, _ = User.objects.update_or_create(
                id=user_data['id'],
                defaults={
                    'name': user_data['name'],
                    'registration': user_data.get('registration'),
                    'user_type_id': user_data.get('user_type_id')
                }
            )
            user.devices.set(devices)

        for tz in all_time_zones.values():
            TimeZone.objects.create(id=tz['id'], name=tz['name'])

        for ts in all_time_spans.values():
            TimeSpan.objects.create(
                id=ts['id'], time_zone_id=ts['time_zone_id'], start=ts['start'], end=ts['end'],
                sun=ts['sun'], mon=ts['mon'], tue=ts['tue'], wed=ts['wed'], thu=ts['thu'], fri=ts['fri'], sat=ts['sat'],
                hol1=ts['hol1'], hol2=ts['hol2'], hol3=ts['hol3']
            )

        for ar in all_access_rules.values():
            AccessRule.objects.create(id=ar['id'], name=ar['name'], type=ar['type'], priority=ar['priority'])

        # Deduplicação de grupos por nome: escolhe um ID canônico por nome e remapeia
        groups_by_name: Dict[str, List[int]] = {}
        for g in all_groups:
            name = g['name']
            gid = int(g['id'])
            groups_by_name.setdefault(name, []).append(gid)

        # Define ID canônico preferindo o menor ID, mas respeitando existência prévia por nome
        chosen_id_by_name: Dict[str, int] = {}
        group_id_map: Dict[int, int] = {}
        for name, ids in groups_by_name.items():
            preferred_id = min(ids)
            existing = CustomGroup.objects.filter(name=name).first()
            canonical_id = existing.id if existing else preferred_id
            # Tenta criar se não existir
            if not existing:
                try:
                    CustomGroup.objects.create(id=canonical_id, name=name)
                except Exception:
                    # Conflito concorrente: pega o existente por nome como canônico
                    existing = CustomGroup.objects.filter(name=name).first()
                    if existing:
                        canonical_id = existing.id
            chosen_id_by_name[name] = canonical_id
            for gid in ids:
                group_id_map[gid] = canonical_id

        # Cria vínculos usuário-grupo remapeando o group_id (evita duplicatas)
        seen_user_groups: set[Tuple[int, int]] = set()
        for ug in all_user_groups:
            try:
                user_id = int(ug['user_id'])
                original_group_id = int(ug['group_id'])
                mapped_group_id = group_id_map.get(original_group_id, original_group_id)
                key = (user_id, mapped_group_id)
                if key in seen_user_groups:
                    continue
                seen_user_groups.add(key)
                if not User.objects.filter(id=user_id).exists():
                    continue
                if not CustomGroup.objects.filter(id=mapped_group_id).exists():
                    continue
                UserGroup.objects.create(user_id=user_id, group_id=mapped_group_id)
            except Exception:
                continue

        # Regras de grupo (grupo -> regra) remapeadas
        try:
            seen_group_rules: set[Tuple[int, int]] = set()
            for gar in all_group_access_rules:  # type: ignore[name-defined]
                original_group_id = int(gar['group_id'])
                mapped_group_id = group_id_map.get(original_group_id, original_group_id)
                access_rule_id = int(gar['access_rule_id'])
                key = (mapped_group_id, access_rule_id)
                if key in seen_group_rules:
                    continue
                seen_group_rules.add(key)
                GroupAccessRule.objects.create(group_id=mapped_group_id, access_rule_id=access_rule_id)
        except NameError:
            pass

        for a in all_areas.values():
            Area.objects.create(id=a['id'], name=a['name'])

        for p in all_portals.values():
            Portal.objects.create(id=p['id'], name=p['name'], area_from_id=p['area_from_id'], area_to_id=p['area_to_id'])

        templates = []
        for t in all_templates:
            if User.objects.filter(id=t['user_id']).exists():
                templates.append(Template(user_id=t['user_id'], template=t['template'], finger_type=t.get('finger_type', 0), finger_position=t.get('finger_position', 0)))
        templates = Template.objects.bulk_create(templates)
        for t, t_data in zip(templates, all_templates):
            if User.objects.filter(id=t_data['user_id']).exists():
                t.devices.set(t_data['devices'])

        cards_models = []
        for c in all_cards:
            if User.objects.filter(id=c['user_id']).exists():
                cards_models.append(Card(user_id=c['user_id'], value=c['value']))
        cards_models = Card.objects.bulk_create(cards_models)
        for c, c_data in zip(cards_models, all_cards):
            if User.objects.filter(id=c_data['user_id']).exists():
                c.devices.set(c_data['devices'])

        for rule in all_user_access_rules:
            try:
                user = User.objects.get(id=rule['user_id'])
                access_rule = AccessRule.objects.get(id=rule['access_rule_id'])
                UserAccessRule.objects.create(user=user, access_rule=access_rule)
            except (User.DoesNotExist, AccessRule.DoesNotExist):
                pass

        for rule in all_portal_access_rules:
            try:
                portal = Portal.objects.get(id=rule['portal_id'])
                access_rule = AccessRule.objects.get(id=rule['access_rule_id'])
                PortalAccessRule.objects.create(portal=portal, access_rule=access_rule)
            except (Portal.DoesNotExist, AccessRule.DoesNotExist):
                pass

        for rule in all_access_rule_time_zones:
            try:
                access_rule = AccessRule.objects.get(id=rule['access_rule_id'])
                time_zone = TimeZone.objects.get(id=rule['time_zone_id'])
                AccessRuleTimeZone.objects.create(access_rule=access_rule, time_zone=time_zone)
            except (AccessRule.DoesNotExist, TimeZone.DoesNotExist):
                pass

        AccessLogs.objects.all().delete()
        valid_logs = []
        for al in all_access_logs:
            try:
                if not Device.objects.filter(id=al['device_id']).exists():
                    continue
                if not User.objects.filter(id=al['user_id']).exists():
                    continue
                if not Portal.objects.filter(id=al['portal_id']).exists():
                    continue
                if not AccessRule.objects.filter(id=al['identification_rule_id']).exists():
                    continue
                valid_logs.append(AccessLogs(
                    id=al['id'], time=datetime.fromtimestamp(int(al['time']), tz=timezone.utc),
                    event_type=al['event'], device_id=al['device_id'], identifier_id=al['identifier_id'],
                    user_id=al['user_id'], portal_id=al['portal_id'], access_rule_id=al['identification_rule_id'],
                    qr_code=al.get('qrcode_value', ''), uhf_value=al.get('uhf_tag', ''), pin_value=al.get('pin_value', ''),
                    card_value=al.get('card_value', ''), confidence=al.get('confidence', 0), mask=al.get('mask', ''),
                ))
            except Exception:
                continue
        if valid_logs:
            AccessLogs.objects.bulk_create(valid_logs)


