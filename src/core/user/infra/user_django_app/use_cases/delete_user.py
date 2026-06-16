from __future__ import annotations

from django.db import transaction

from src.core.control_id.infra.control_id_django_app.models.access_logs import AccessLogs
from src.core.user.infra.user_django_app.models import User
from src.core.user.infra.user_django_app.services import UserDeviceSyncService


class DeleteUserUseCase:
    def __init__(self, sync_service: UserDeviceSyncService | None = None) -> None:
        self.sync_service = sync_service or UserDeviceSyncService()

    def execute(self, user: User) -> None:
        with transaction.atomic():
            user.useraccessrule_set.all().delete()
            user.usergroup_set.all().delete()
            user.templates.all().delete()
            user.cards.all().delete()
            user.groups.clear()
            user.user_permissions.clear()

            AccessLogs.objects.filter(user=user).update(user=None)

            if not user.panel_access_only:
                for device in self.sync_service.get_active_target_devices(user):
                    self.sync_service.delete_user_from_device(device, user)

            user.delete()
