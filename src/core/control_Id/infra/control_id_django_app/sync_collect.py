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

    for device in devices:
        try:
            sync.set_device(device)

            for user in sync.sync_users(device):
                uid = user['id']
                if uid not in all_users:
                    all_users[uid] = user
                    all_users[uid]['devices'] = []
                all_users[uid]['devices'].append(device)

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
            all_group_access_rules.extend(sync.sync_group_access_rules(device))
            all_user_groups.extend(sync.sync_user_groups(device))
            all_groups.extend(sync.sync_groups(device))
            all_access_logs.extend(sync.sync_access_logs(device))
        except Exception:
            continue

    return (
        all_users, all_time_zones, all_time_spans, all_access_rules,
        all_portals, all_areas, all_templates, all_cards,
        all_user_access_rules, all_portal_access_rules,
        all_access_rule_time_zones, all_group_access_rules, all_user_groups, all_groups, all_access_logs,
    )


