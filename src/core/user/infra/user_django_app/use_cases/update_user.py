from __future__ import annotations

from django.db import transaction

from src.core.user.infra.user_django_app.models import User
from src.core.user.infra.user_django_app.services import UserDeviceSyncService
from src.core.user.infra.user_django_app.use_cases.shared import normalize_user_type


class UpdateUserUseCase:
    def __init__(self, sync_service: UserDeviceSyncService | None = None) -> None:
        self.sync_service = sync_service or UserDeviceSyncService()

    def execute(self, user: User, serializer) -> User:
        previous = self.sync_service.snapshot(user)

        with transaction.atomic():
            user = serializer.save()
            normalize_user_type(user)
            current = self.sync_service.snapshot(user)
            self.sync_service.apply_update(user, previous, current)
            return user
