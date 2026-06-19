from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from src.core.control_id.infra.control_id_django_app.models import AccessRule
from src.core.control_id.infra.control_id_django_app.services import (
    AccessRuleDeviceSyncService,
)


@dataclass(frozen=True)
class AccessRuleUseCaseResult:
    access_rule: AccessRule


class CreateAccessRuleUseCase:
    def __init__(
        self,
        sync_service: AccessRuleDeviceSyncService | None = None,
    ) -> None:
        self.sync_service = sync_service or AccessRuleDeviceSyncService()

    def execute(self, serializer) -> AccessRuleUseCaseResult:
        with transaction.atomic():
            access_rule = serializer.save()
            self.sync_service.create(access_rule)
            return AccessRuleUseCaseResult(access_rule=access_rule)


class UpdateAccessRuleUseCase:
    def __init__(
        self,
        sync_service: AccessRuleDeviceSyncService | None = None,
    ) -> None:
        self.sync_service = sync_service or AccessRuleDeviceSyncService()

    def execute(self, serializer) -> AccessRuleUseCaseResult:
        with transaction.atomic():
            access_rule = serializer.save()
            self.sync_service.update(access_rule)
            return AccessRuleUseCaseResult(access_rule=access_rule)


class DeleteAccessRuleUseCase:
    def __init__(
        self,
        sync_service: AccessRuleDeviceSyncService | None = None,
    ) -> None:
        self.sync_service = sync_service or AccessRuleDeviceSyncService()

    def execute(self, access_rule: AccessRule) -> None:
        with transaction.atomic():
            self.sync_service.delete(access_rule)
            access_rule.delete()
