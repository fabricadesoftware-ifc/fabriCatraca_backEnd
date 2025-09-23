from celery import shared_task
from src.core.control_Id.infra.control_id_django_app.views.sync import GlobalSyncMixin
from src.core.control_Id.infra.control_id_django_app.models import Device
from .sync_collect import collect_all
from .sync_persist import persist_all


@shared_task(bind=True)
def run_global_sync(self) -> dict:
    sync = GlobalSyncMixin()
    devices = list(Device.objects.filter(is_active=True))
    if not devices:
        return {"success": False, "error": "Nenhuma catraca ativa encontrada"}

    (
        all_users,
        all_time_zones,
        all_time_spans,
        all_access_rules,
        all_portals,
        all_areas,
        all_templates,
        all_cards,
        all_user_access_rules,
        all_portal_access_rules,
        all_access_rule_time_zones,
        all_group_access_rules,
        all_user_groups,
        all_groups,
        all_access_logs,
    ) = collect_all(sync, devices)

    persist_all(
        all_users,
        all_time_zones,
        all_time_spans,
        all_access_rules,
        all_portals,
        all_areas,
        all_templates,
        all_cards,
        all_user_access_rules,
        all_portal_access_rules,
        all_access_rule_time_zones,
        all_group_access_rules,
        all_user_groups,
        all_groups,
        all_access_logs,
    )

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
            "devices": len(devices),
            "access_logs": len(all_access_logs),
        },
    }


