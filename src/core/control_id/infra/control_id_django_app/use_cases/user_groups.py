from __future__ import annotations

from dataclasses import dataclass

from django.db import IntegrityError, transaction

from src.core.control_id.infra.control_id_django_app.models.user_groups import (
    UserGroup,
)
from src.core.control_id.infra.control_id_django_app.services import (
    UserGroupDeviceSyncService,
)


@dataclass(frozen=True)
class UserGroupUseCaseResult:
    instance: UserGroup
    status_code: int


class CreateUserGroupUseCase:
    def __init__(
        self,
        sync_service: UserGroupDeviceSyncService | None = None,
    ) -> None:
        self.sync_service = sync_service or UserGroupDeviceSyncService()

    def execute(self, serializer) -> UserGroupUseCaseResult:
        user = serializer.validated_data["user"]
        group = serializer.validated_data["group"]
        instance = UserGroup.objects.filter(user=user, group=group).first()

        if instance:
            return UserGroupUseCaseResult(instance=instance, status_code=200)

        with transaction.atomic():
            soft_deleted_instance = UserGroup._base_manager.filter(
                user=user,
                group=group,
            ).first()
            if soft_deleted_instance:
                soft_deleted_instance.undelete()
                self.sync_service.create(soft_deleted_instance)
                return UserGroupUseCaseResult(
                    instance=soft_deleted_instance,
                    status_code=200,
                )

            try:
                instance = serializer.save()
                self.sync_service.create(instance)
                return UserGroupUseCaseResult(instance=instance, status_code=201)
            except IntegrityError:
                existing = UserGroup._base_manager.filter(
                    user=user,
                    group=group,
                ).first()
                if not existing:
                    raise

                existing.undelete()
                self.sync_service.create(existing)
                return UserGroupUseCaseResult(instance=existing, status_code=200)


class UpdateUserGroupUseCase:
    def __init__(
        self,
        sync_service: UserGroupDeviceSyncService | None = None,
    ) -> None:
        self.sync_service = sync_service or UserGroupDeviceSyncService()

    def execute(self, instance: UserGroup, serializer) -> UserGroup:
        previous_payload = self.sync_service.to_relation_payload(instance)

        with transaction.atomic():
            instance = serializer.save()
            self.sync_service.update(instance, previous_payload=previous_payload)
            return instance


class DeleteUserGroupUseCase:
    def __init__(
        self,
        sync_service: UserGroupDeviceSyncService | None = None,
    ) -> None:
        self.sync_service = sync_service or UserGroupDeviceSyncService()

    def execute(self, instance: UserGroup) -> None:
        with transaction.atomic():
            self.sync_service.delete(instance)
            instance.delete()
