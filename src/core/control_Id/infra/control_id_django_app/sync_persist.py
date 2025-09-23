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
        print("[SYNC] Iniciando sincronização completa")
        
        # Sincronização de usuários
        print("[SYNC] Sincronizando usuários")
        remote_user_ids = {int(k) for k in all_users.keys()}
        User.objects.exclude(id__in=remote_user_ids).exclude(is_staff=True, is_superuser=True).delete()

        # Identifica usuários sem matrícula
        users_without_registration = []
        for user_id, user_data in all_users.items():
            if not user_data.get('registration'):
                users_without_registration.append({
                    'id': user_id,
                    'name': user_data['name'],
                    'devices': [d.name for d in user_data['devices']]
                })

        if users_without_registration:
            print("\n[SYNC] ⚠️ ATENÇÃO: Usuários sem matrícula encontrados:")
            for user in users_without_registration:
                print(f"""    ID: {user['id']}
    Nome: {user['name']}
    Dispositivos: {', '.join(user['devices'])}
    ----------------------------------------""")
            print("\nPor favor, atualize as matrículas desses usuários no sistema.\n")

        # Processa usuários com tratamento para matrícula vazia
        for user_data in all_users.values():
            devices = user_data.pop('devices')
            
            # Se não tem matrícula, usa um valor temporário baseado no ID
            if not user_data.get('registration'):
                temp_registration = f"TEMP_{user_data['id']}"
                print(f"[SYNC] Usuário {user_data['name']} (ID: {user_data['id']}) sem matrícula. Usando temporária: {temp_registration}")
                user_data['registration'] = temp_registration

            user, _ = User.objects.update_or_create(
                id=user_data['id'],
                defaults={
                    'name': user_data['name'],
                    'registration': user_data['registration'],
                    'user_type_id': user_data.get('user_type_id')
                }
            )
            user.devices.set(devices)

        # Sincronização de time zones
        print("[SYNC] Sincronizando time zones")
        for tz in all_time_zones.values():
            TimeZone.objects.update_or_create(id=tz['id'], defaults={"name": tz['name']})
        TimeZone.objects.exclude(id__in=list(all_time_zones.keys())).delete()

        # Sincronização de time spans
        print("[SYNC] Sincronizando time spans")
        for ts in all_time_spans.values():
            TimeSpan.objects.update_or_create(
                id=ts['id'],
                defaults=dict(
                    time_zone_id=ts['time_zone_id'], start=ts['start'], end=ts['end'],
                    sun=ts['sun'], mon=ts['mon'], tue=ts['tue'], wed=ts['wed'], thu=ts['thu'], fri=ts['fri'], sat=ts['sat'],
                    hol1=ts['hol1'], hol2=ts['hol2'], hol3=ts['hol3']
                )
            )
        TimeSpan.objects.exclude(id__in=list(all_time_spans.keys())).delete()

        # Sincronização de regras de acesso
        print("[SYNC] Sincronizando regras de acesso")
        for ar in all_access_rules.values():
            AccessRule.objects.update_or_create(
                id=ar['id'],
                defaults={"name": ar['name'], "type": ar['type'], "priority": ar['priority']}
            )
        AccessRule.objects.exclude(id__in=list(all_access_rules.keys())).delete()

        # Sincronização de grupos
        print("[SYNC] Sincronizando grupos")
        groups_by_name: Dict[str, List[int]] = {}
        for g in all_groups:
            name = g['name']
            gid = int(g['id'])
            groups_by_name.setdefault(name, []).append(gid)

        chosen_id_by_name: Dict[str, int] = {}
        group_id_map: Dict[int, int] = {}
        for name, ids in groups_by_name.items():
            preferred_id = min(ids)
            existing = CustomGroup.objects.filter(name=name).first()
            canonical_id = existing.id if existing else preferred_id
            if not existing:
                try:
                    CustomGroup.objects.create(id=canonical_id, name=name)
                except Exception:
                    existing = CustomGroup.objects.filter(name=name).first()
                    if existing:
                        canonical_id = existing.id
            chosen_id_by_name[name] = canonical_id
            for gid in ids:
                group_id_map[gid] = canonical_id

        # Sincronização de grupos de usuários
        print("[SYNC] Sincronizando grupos de usuários")
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

        # Sincronização de regras de acesso de grupo
        print(f"[SYNC] Sincronizando regras de acesso de grupo: recebidos={len(all_group_access_rules)}")
        try:
            seen_group_rules: set[Tuple[int, int]] = set()
            created_gar = 0
            for gar in all_group_access_rules:
                original_group_id = int(gar['group_id'])
                mapped_group_id = group_id_map.get(original_group_id, original_group_id)
                access_rule_id = int(gar['access_rule_id'])
                key = (mapped_group_id, access_rule_id)
                if key in seen_group_rules:
                    continue
                seen_group_rules.add(key)
                if not CustomGroup.objects.filter(id=mapped_group_id).exists():
                    continue
                if not AccessRule.objects.filter(id=access_rule_id).exists():
                    continue
                _, created = GroupAccessRule.objects.get_or_create(group_id=mapped_group_id, access_rule_id=access_rule_id)
                if created:
                    created_gar += 1
        except NameError:
            pass
        print(f"[SYNC] group_access_rules criados/confirmados: {created_gar}")

        # Sincronização de áreas
        print("[SYNC] Sincronizando áreas")
        for a in all_areas.values():
            Area.objects.update_or_create(id=a['id'], defaults={"name": a['name']})
        Area.objects.exclude(id__in=list(all_areas.keys())).delete()

        # Sincronização de portais
        print("[SYNC] Sincronizando portais")
        for p in all_portals.values():
            Portal.objects.update_or_create(
                id=p['id'],
                defaults={"name": p['name'], "area_from_id": p['area_from_id'], "area_to_id": p['area_to_id']}
            )
        Portal.objects.exclude(id__in=list(all_portals.keys())).delete()

        # Sincronização de templates
        print("[SYNC] Sincronizando templates")
        sp_templates = transaction.savepoint()
        try:
            Template.objects.all().delete()
            templates = []
            for t in all_templates:
                if User.objects.filter(id=t['user_id']).exists():
                    templates.append(Template(user_id=t['user_id'], template=t['template'], finger_type=t.get('finger_type', 0), finger_position=t.get('finger_position', 0)))
            templates = Template.objects.bulk_create(templates)
            for t, t_data in zip(templates, all_templates):
                if User.objects.filter(id=t_data['user_id']).exists():
                    t.devices.set(t_data['devices'])
            transaction.savepoint_commit(sp_templates)
        except Exception:
            transaction.savepoint_rollback(sp_templates)

        # Sincronização de cartões
        print("[SYNC] Sincronizando cartões")
        sp_cards = transaction.savepoint()
        try:
            Card.objects.all().delete()
            cards_models = []
            for c in all_cards:
                if User.objects.filter(id=c['user_id']).exists():
                    cards_models.append(Card(user_id=c['user_id'], value=c['value']))
            cards_models = Card.objects.bulk_create(cards_models)
            for c, c_data in zip(cards_models, all_cards):
                if User.objects.filter(id=c_data['user_id']).exists():
                    c.devices.set(c_data['devices'])
            transaction.savepoint_commit(sp_cards)
        except Exception:
            transaction.savepoint_rollback(sp_cards)

        # Sincronização de regras de acesso de usuário
        print("[SYNC] Sincronizando regras de acesso de usuário")
        for rule in all_user_access_rules:
            try:
                user = User.objects.get(id=rule['user_id'])
                access_rule = AccessRule.objects.get(id=rule['access_rule_id'])
                UserAccessRule.objects.create(user=user, access_rule=access_rule)
            except (User.DoesNotExist, AccessRule.DoesNotExist):
                pass

        # Sincronização de regras de acesso de portal
        print("[SYNC] Sincronizando regras de acesso de portal")
        for rule in all_portal_access_rules:
            try:
                portal = Portal.objects.get(id=rule['portal_id'])
                access_rule = AccessRule.objects.get(id=rule['access_rule_id'])
                PortalAccessRule.objects.create(portal=portal, access_rule=access_rule)
            except (Portal.DoesNotExist, AccessRule.DoesNotExist):
                pass

        # Sincronização de regras de acesso com timezone
        print("[SYNC] Sincronizando regras de acesso com timezone")
        seen_artz: set[tuple[int, int]] = set()
        for artz in all_access_rule_time_zones:
            try:
                ar_id = int(artz['access_rule_id'])
                tz_id = int(artz['time_zone_id'])
                key = (ar_id, tz_id)
                if key in seen_artz:
                    continue
                seen_artz.add(key)
                if not AccessRule.objects.filter(id=ar_id).exists():
                    continue
                if not TimeZone.objects.filter(id=tz_id).exists():
                    continue
                AccessRuleTimeZone.objects.get_or_create(access_rule_id=ar_id, time_zone_id=tz_id)
            except Exception:
                continue

        # Otimização: Pré-carrega dados necessários em memória
        print("[SYNC] Iniciando sincronização otimizada de logs de acesso")
        
        # Carrega IDs existentes em memória
        existing_devices = set(Device.objects.values_list('id', flat=True))
        existing_portals = set(Portal.objects.values_list('id', flat=True))
        existing_rules = set(AccessRule.objects.values_list('id', flat=True))
        existing_users = set(User.objects.values_list('id', flat=True))
        existing_logs = set(AccessLogs.objects.values_list('id', flat=True))

        # Obtém device padrão
        default_device = Device.objects.filter(is_default=True).first() or Device.objects.first()
        
        # Cria área padrão se necessário
        fallback_area = Area.objects.first()
        if fallback_area is None:
            fallback_area = Area.objects.create(id=999999, name='Default Area')

        # Prepara logs para inserção em lote
        valid_logs = []
        seen_log_ids = set()
        batch_size = 1000  # Ajuste conforme necessário
        
        # Contadores para relatório
        stats = {
            'total': len(all_access_logs),
            'device_fallback': 0,
            'skipped_no_device': 0,
            'created_portal': 0,
            'created_rule': 0,
            'user_null': 0,
            'duplicates': 0,
            'processed': 0,
            'errors': 0
        }

        print(f"[SYNC] Processando {stats['total']} logs de acesso")

        # Limpa logs antigos
        AccessLogs.objects.all().delete()

        # Processa logs em lotes
        for al in all_access_logs:
            try:
                # Verifica duplicatas
                log_id = al.get('id')
                if log_id in seen_log_ids or log_id in existing_logs:
                    stats['duplicates'] += 1
                    continue
                
                # Processa device
                device_id = al.get('device_id')
                if device_id not in existing_devices:
                    if default_device is None:
                        stats['skipped_no_device'] += 1
                        continue
                    device_id = default_device.id
                    stats['device_fallback'] += 1

                # Processa portal
                portal_id = al.get('portal_id') or al.get('door_id')
                if portal_id not in existing_portals:
                    try:
                        Portal.objects.create(
                            id=portal_id,
                            name=f'Portal {portal_id}',
                            area_from_id=fallback_area.id,
                            area_to_id=fallback_area.id
                        )
                        existing_portals.add(portal_id)
                        stats['created_portal'] += 1
                    except:
                        if portal_id not in existing_portals:
                            continue

                # Processa regra de acesso
                rule_id = al.get('identification_rule_id') or al.get('access_rule_id') or 999999
                if rule_id not in existing_rules:
                    try:
                        AccessRule.objects.create(
                            id=rule_id,
                            name=f'Rule {rule_id}',
                            type=1,
                            priority=0
                        )
                        existing_rules.add(rule_id)
                        stats['created_rule'] += 1
                    except:
                        if rule_id not in existing_rules:
                            continue

                # Processa usuário
                user_id = al.get('user_id')
                if user_id not in existing_users:
                    user_id = None
                    stats['user_null'] += 1

                # Normaliza dados
                try:
                    event_type = int(al.get('event', 10))
                except:
                    event_type = 10  # ACESSO_NAO_IDENTIFICADO

                try:
                    time_value = datetime.fromtimestamp(int(al.get('time')), tz=timezone.utc)
                except:
                    time_value = timezone.now()

                # Cria entrada de log
                entry = AccessLogs(
                    id=log_id,
                    time=time_value,
                    event_type=event_type,
                    device_id=device_id,
                    identifier_id=al.get('identifier_id', ''),
                    user_id=user_id,
                    portal_id=portal_id,
                    access_rule_id=rule_id,
                    qr_code=al.get('qrcode_value', ''),
                    uhf_value=al.get('uhf_tag', ''),
                    pin_value=al.get('pin_value', ''),
                    card_value=al.get('card_value', ''),
                    confidence=al.get('confidence', 0),
                    mask=al.get('mask', '')
                )
                
                valid_logs.append(entry)
                seen_log_ids.add(log_id)
                stats['processed'] += 1

                # Insere em lote quando atingir o tamanho do batch
                if len(valid_logs) >= batch_size:
                    AccessLogs.objects.bulk_create(valid_logs, ignore_conflicts=True)
                    valid_logs = []

            except Exception as e:
                stats['errors'] += 1
                if stats['errors'] <= 5:  # Limita o número de erros mostrados
                    print(f"[SYNC][ACCESS_LOGS] Erro ao processar log {al.get('id')}: {e}")

        # Insere logs restantes
        if valid_logs:
            AccessLogs.objects.bulk_create(valid_logs, ignore_conflicts=True)

        print(f"""[SYNC] Relatório de sincronização:
    Total de logs: {stats['total']}
    Processados com sucesso: {stats['processed']}
    Duplicados: {stats['duplicates']}
    Fallback de device: {stats['device_fallback']}
    Sem device (ignorados): {stats['skipped_no_device']}
    Portais criados: {stats['created_portal']}
    Regras criadas: {stats['created_rule']}
    Usuários não encontrados: {stats['user_null']}
    Erros de processamento: {stats['errors']}
""")
