def admin_dashboard(request):
    """Fornece contadores para o dashboard do admin."""
    data = {
        "devices_active_count": 0,
        "users_count": 0,
        "access_rules_count": 0,
        "group_access_rules_count": 0,
    }
    try:
        # Evita custo em páginas fora do admin
        if request and request.path and request.path.startswith('/api/admin'):
            from src.core.control_Id.infra.control_id_django_app.models import Device, AccessRule, GroupAccessRule
            from src.core.user.infra.user_django_app.models import User
            data["devices_active_count"] = Device.objects.filter(is_active=True).count()
            data["users_count"] = User.objects.count()
            data["access_rules_count"] = AccessRule.objects.count()
            data["group_access_rules_count"] = GroupAccessRule.objects.count()
    except Exception:
        # Em migrações iniciais ou erros de import, mantém zero
        pass
    return data

