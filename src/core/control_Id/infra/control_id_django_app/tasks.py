from celery import shared_task
from django.db import transaction
from rest_framework import status
from src.core.control_Id.infra.control_id_django_app.views.sync import GlobalSyncMixin
from src.core.control_Id.infra.control_id_django_app.models import (
    Device, Template, Card, TimeZone, TimeSpan, Portal, AccessRule,
    PortalAccessRule, UserAccessRule, AccessRuleTimeZone, Area,
    UserGroup, CustomGroup, GroupAccessRule, AccessLogs,
)
from src.core.user.infra.user_django_app.models import User


@shared_task(bind=True)
def run_global_sync(self) -> dict:
    sync = GlobalSyncMixin()
    device = Device.objects.filter(is_active=True).first()
    if not device:
        return {"success": False, "error": "Nenhuma catraca ativa encontrada"}

    # Ajuste do ID real (mantido conforme view atual)
    device.id = 4008342653506425
    device.save()

    all_users = {}
    all_time_zones = {}
    all_time_spans = {}
    all_access_rules = {}
    all_portals = {}
    all_areas = {}
    all_templates = []
    all_cards = []
    all_user_access_rules = []
    all_portal_access_rules = []
    all_access_rule_time_zones = []
    all_user_groups = []
    all_groups = []
    all_group_access_rules = []
    all_access_logs = []

    sync.set_device(device)

    # Coletas (espelha a view atual)
    for user in sync.sync_users(device):
        if user['id'] not in all_users:
            all_users[user['id']] = user
            all_users[user['id']]['devices'] = []
        all_users[user['id']]['devices'].append(device)

    for tz in sync.sync_time_zones(device):
        all_time_zones[tz['id']] = tz

    for ts in sync.sync_time_spans(device):
        all_time_spans[ts['id']] = ts

    for ar in sync.sync_access_rules(device):
        all_access_rules[ar['id']] = ar

    for a in sync.sync_areas(device):
        all_areas[a['id']] = a

    for p in sync.sync_portals(device):
        all_portals[p['id']] = p

    for t in sync.sync_templates(device):
        t['devices'] = [device]
        all_templates.append(t)

    for c in sync.sync_cards(device):
        c['devices'] = [device]
        all_cards.append(c)

    all_user_access_rules.extend(sync.sync_user_access_rules(device))
    all_portal_access_rules.extend(sync.sync_portal_access_rules(device))
    all_access_rule_time_zones.extend(sync.sync_access_rule_time_zones(device))
    all_user_groups.extend(sync.sync_user_groups(device))
    all_groups.extend(sync.sync_groups(device))
    all_group_access_rules.extend(sync.sync_group_access_rules(device))
    all_access_logs.extend(sync.sync_access_logs(device))

    # Persistência em transação (espelha a view atual)
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

        for group_data in all_groups:
            CustomGroup.objects.update_or_create(
                id=group_data['id'],
                defaults={'name': group_data['name']}
            )

        for user_group in all_user_groups:
            try:
                user = User.objects.get(id=user_group['user_id'])
                group = CustomGroup.objects.get(id=user_group['group_id'])
                UserGroup.objects.create(user=user, group=group)
            except (User.DoesNotExist, CustomGroup.DoesNotExist):
                continue

        TimeZone.objects.bulk_create([
            TimeZone(id=tz['id'], name=tz['name'])
            for tz in all_time_zones.values()
        ])

        TimeSpan.objects.bulk_create([
            TimeSpan(
                id=ts['id'],
                time_zone_id=ts['time_zone_id'],
                start=ts['start'],
                end=ts['end'],
                sun=ts['sun'],
                mon=ts['mon'],
                tue=ts['tue'],
                wed=ts['wed'],
                thu=ts['thu'],
                fri=ts['fri'],
                sat=ts['sat'],
                hol1=ts['hol1'],
                hol2=ts['hol2'],
                hol3=ts['hol3']
            )
            for ts in all_time_spans.values()
        ])

        AccessRule.objects.bulk_create([
            AccessRule(
                id=ar['id'],
                name=ar['name'],
                type=ar['type'],
                priority=ar['priority']
            )
            for ar in all_access_rules.values()
        ])

        GroupAccessRule.objects.bulk_create([
            GroupAccessRule(
                group_id=gar['group_id'],
                access_rule_id=gar['access_rule_id']
            )
            for gar in all_group_access_rules
        ])

        Area.objects.bulk_create([
            Area(id=a['id'], name=a['name'])
            for a in all_areas.values()
        ])

        Portal.objects.bulk_create([
            Portal(
                id=p['id'],
                name=p['name'],
                area_from_id=Area.objects.get(id=p['area_from_id']).id,
                area_to_id=Area.objects.get(id=p['area_to_id']).id,
            )
            for p in all_portals.values()
        ])

        templates = Template.objects.bulk_create([
            Template(
                user_id=t['user_id'],
                template=t['template'],
                finger_type=t.get('finger_type', 0),
                finger_position=t.get('finger_position', 0)
            )
            for t in all_templates
            if User.objects.filter(id=t['user_id']).exists()
        ])

        for t, t_data in zip(templates, all_templates):
            if User.objects.filter(id=t_data['user_id']).exists():
                t.devices.set(t_data['devices'])

        cards = Card.objects.bulk_create([
            Card(
                user_id=c['user_id'],
                value=c['value']
            )
            for c in all_cards
            if User.objects.filter(id=c['user_id']).exists()
        ])

        for c, c_data in zip(cards, all_cards):
            if User.objects.filter(id=c_data['user_id']).exists():
                c.devices.set(c_data['devices'])

        for rule in all_user_access_rules:
            try:
                user = User.objects.get(id=rule['user_id'])
                access_rule = AccessRule.objects.get(id=rule['access_rule_id']).id
                UserAccessRule.objects.create(
                    user_id=user,
                    access_rule_id=access_rule,
                )
            except (User.DoesNotExist, AccessRule.DoesNotExist):
                continue

        for rule in all_portal_access_rules:
            try:
                portal = Portal.objects.get(id=rule['portal_id'])
                access_rule = AccessRule.objects.get(id=rule['access_rule_id'])
                PortalAccessRule.objects.create(
                    portal_id=portal,
                    access_rule_id=access_rule,
                )
            except (Portal.DoesNotExist, AccessRule.DoesNotExist):
                continue

        for rule in all_access_rule_time_zones:
            try:
                access_rule = AccessRule.objects.get(id=rule['access_rule_id']).id
                time_zone = TimeZone.objects.get(id=rule['time_zone_id']).id
                AccessRuleTimeZone.objects.create(
                    access_rule_id=access_rule,
                    time_zone_id=time_zone,
                )
            except (AccessRule.DoesNotExist, TimeZone.DoesNotExist):
                continue

        # Logs
        AccessLogs.objects.all().delete()

        valid_logs = []
        from datetime import datetime
        for al in all_access_logs:
            try:
                if not all([
                    Device.objects.filter(id=al['device_id']).exists(),
                    User.objects.filter(id=al['user_id']).exists(),
                    Portal.objects.filter(id=al['portal_id']).exists(),
                    AccessRule.objects.filter(id=al['identification_rule_id']).exists(),
                ]):
                    continue

                valid_logs.append(
                    AccessLogs(
                        id=al['id'],
                        time=datetime.fromtimestamp(int(al['time'])),
                        event_type=al['event'],
                        device_id=al['device_id'],
                        identifier_id=al['identifier_id'],
                        user_id=al['user_id'],
                        portal_id=al['portal_id'],
                        access_rule_id=al['identification_rule_id'],
                        qr_code=al.get('qrcode_value', ''),
                        uhf_value=al.get('uhf_tag', ''),
                        pin_value=al.get('pin_value', ''),
                        card_value=al.get('card_value', ''),
                        confidence=al.get('confidence', 0),
                        mask=al.get('mask', ''),
                    )
                )
            except Exception:
                continue

        if valid_logs:
            AccessLogs.objects.bulk_create(valid_logs)

    return {
        "success": True,
        "message": "Sincronização global concluída com sucesso",
        "stats": {
            "users": len(all_users),
            "time_zones": len(all_time_zones),
            "time_spans": len(all_time_spans),
            "access_rules": len(all_access_rules),
            "areas": len(all_areas),
            "portals": len(all_portals),
            "templates": len(all_templates),
            "cards": len(all_cards),
            "user_access_rules": len(all_user_access_rules),
            "portal_access_rules": len(all_portal_access_rules),
            "access_rule_time_zones": len(all_access_rule_time_zones),
            "groups": len(all_groups),
            "user_groups": len(all_user_groups),
            "group_access_rules": len(all_group_access_rules),
            "devices": 1,
            "access_logs": len(all_access_logs),
        },
    }


