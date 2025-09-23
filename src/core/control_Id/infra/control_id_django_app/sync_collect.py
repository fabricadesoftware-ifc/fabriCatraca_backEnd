from typing import Dict, List, Any, Tuple


def collect_all(sync, devices) -> Tuple[
    Dict[int, Any], Dict[int, Any], Dict[int, Any], Dict[int, Any], Dict[int, Any],
    List[Any], List[Any], List[Any], List[Any], List[Any], List[Any], List[Any], List[Any], List[Any], List[Any]
]:
    all_users: Dict[int, Any] = {}
    all_time_zones: Dict[int, Any] = {}
    all_time_spans: Dict[int, Any] = {}
    all_access_rules: Dict[int, Any] = {}
    all_portals: Dict[int, Any] = {}
    all_areas: Dict[int, Any] = {}
    all_templates: List[Any] = []
    all_cards: List[Any] = []
    all_user_access_rules: List[Any] = []
    all_portal_access_rules: List[Any] = []
    all_access_rule_time_zones: List[Any] = []
    all_group_access_rules: List[Any] = []
    all_user_groups: List[Any] = []
    all_groups: List[Any] = []
    all_access_logs: List[Any] = []

    print("[SYNC] Iniciando coleta completa de dados")

    for device in devices:
        try:
            sync.set_device(device)

            # Coleta usuários e seus dispositivos
            print(f"[SYNC] Coletando usuários do dispositivo {device.name}")
            for user in sync.sync_users(device):
                uid = user['id']
                if uid not in all_users:
                    all_users[uid] = user
                    all_users[uid]['devices'] = []
                all_users[uid]['devices'].append(device)

            # Coleta configurações de tempo
            print(f"[SYNC] Coletando configurações de tempo do dispositivo {device.name}")
            for tz in sync.sync_time_zones(device):
                all_time_zones[tz['id']] = tz
            for ts in sync.sync_time_spans(device):
                all_time_spans[ts['id']] = ts

            # Coleta regras de acesso e áreas
            print(f"[SYNC] Coletando regras e áreas do dispositivo {device.name}")
            for ar in sync.sync_access_rules(device):
                all_access_rules[ar['id']] = ar
            for a in sync.sync_areas(device):
                all_areas[a['id']] = a
            for p in sync.sync_portals(device):
                all_portals[p['id']] = p

            # Coleta templates e cartões
            print(f"[SYNC] Coletando templates e cartões do dispositivo {device.name}")
            for t in sync.sync_templates(device):
                t['devices'] = [device]
                all_templates.append(t)
            for c in sync.sync_cards(device):
                c['devices'] = [device]
                all_cards.append(c)

            # Coleta regras e grupos
            print(f"[SYNC] Coletando regras e grupos do dispositivo {device.name}")
            all_user_access_rules.extend(sync.sync_user_access_rules(device))
            all_portal_access_rules.extend(sync.sync_portal_access_rules(device))
            all_access_rule_time_zones.extend(sync.sync_access_rule_time_zones(device))
            all_group_access_rules.extend(sync.sync_group_access_rules(device))
            all_user_groups.extend(sync.sync_user_groups(device))
            all_groups.extend(sync.sync_groups(device))

            # Coleta logs de acesso
            print(f"[SYNC] Coletando logs de acesso do dispositivo {device.name}")
            device_logs = sync.sync_access_logs(device)
            print(f"[SYNC] Coletados {len(device_logs)} logs do dispositivo {device.name}")
            all_access_logs.extend(device_logs)

        except Exception as e:
            print(f"[SYNC] Erro ao coletar dados do dispositivo {device.name}: {str(e)}")
            continue

    # Imprime resumo da coleta
    print(f"""[SYNC] Resumo da coleta:
    Usuários: {len(all_users)}
    Time Zones: {len(all_time_zones)}
    Time Spans: {len(all_time_spans)}
    Regras de Acesso: {len(all_access_rules)}
    Áreas: {len(all_areas)}
    Portais: {len(all_portals)}
    Templates: {len(all_templates)}
    Cartões: {len(all_cards)}
    Regras de Acesso de Usuário: {len(all_user_access_rules)}
    Regras de Acesso de Portal: {len(all_portal_access_rules)}
    Regras de Acesso com TimeZone: {len(all_access_rule_time_zones)}
    Grupos: {len(all_groups)}
    Grupos de Usuário: {len(all_user_groups)}
    Regras de Acesso de Grupo: {len(all_group_access_rules)}
    Logs de Acesso: {len(all_access_logs)}
""")
    return (
        all_users, all_time_zones, all_time_spans, all_access_rules,
        all_portals, all_areas, all_templates, all_cards,
        all_user_access_rules, all_portal_access_rules,
        all_access_rule_time_zones, all_group_access_rules, all_user_groups, all_groups, all_access_logs,
    )


