from __future__ import annotations

from dataclasses import dataclass

from django.db import IntegrityError, transaction

from src.core.control_id.infra.control_id_django_app.models import (
    AccessRuleTimeZone,
    GroupAccessRule,
    PortalAccessRule,
    UserAccessRule,
)
from src.core.control_id.infra.control_id_django_app.services import (
    AccessRuleRelationDeviceSyncService,
)


@dataclass(frozen=True)
class AccessRuleRelationUseCaseResult:
    instance: UserAccessRule | GroupAccessRule | PortalAccessRule | AccessRuleTimeZone
    created: bool = True


class CreateUserAccessRuleUseCase:
    def __init__(
        self,
        sync_service: AccessRuleRelationDeviceSyncService | None = None,
    ) -> None:
        self.sync_service = sync_service or AccessRuleRelationDeviceSyncService()

    def execute(self, serializer) -> AccessRuleRelationUseCaseResult:
        with transaction.atomic():
            instance = serializer.save()
            self.sync_service.create_user_rule(instance)
            return AccessRuleRelationUseCaseResult(instance=instance)


class UpdateUserAccessRuleUseCase:
    def __init__(
        self,
        sync_service: AccessRuleRelationDeviceSyncService | None = None,
    ) -> None:
        self.sync_service = sync_service or AccessRuleRelationDeviceSyncService()

    def execute(
        self,
        serializer,
        *,
        instance: UserAccessRule,
    ) -> AccessRuleRelationUseCaseResult:
        old_device_ids = self.sync_service.get_device_ids(instance.portal_group)
        previous_payload = self.sync_service.user_payload(instance)

        with transaction.atomic():
            instance = serializer.save()
            self.sync_service.update_user_rule(
                instance,
                previous_payload=previous_payload,
                old_device_ids=old_device_ids,
            )
            return AccessRuleRelationUseCaseResult(instance=instance)


class DeleteUserAccessRuleUseCase:
    def __init__(
        self,
        sync_service: AccessRuleRelationDeviceSyncService | None = None,
    ) -> None:
        self.sync_service = sync_service or AccessRuleRelationDeviceSyncService()

    def execute(self, instance: UserAccessRule) -> None:
        with transaction.atomic():
            self.sync_service.delete_user_rule(instance)
            instance.delete()


class CreateGroupAccessRuleUseCase:
    def __init__(
        self,
        sync_service: AccessRuleRelationDeviceSyncService | None = None,
    ) -> None:
        self.sync_service = sync_service or AccessRuleRelationDeviceSyncService()

    def execute(self, serializer) -> AccessRuleRelationUseCaseResult:
        group = serializer.validated_data["group"]
        access_rule = serializer.validated_data["access_rule"]
        portal_group = serializer.validated_data.get("portal_group")

        instance = GroupAccessRule.objects.filter(
            group=group,
            access_rule=access_rule,
            portal_group=portal_group,
        ).first()

        if instance:
            return AccessRuleRelationUseCaseResult(instance=instance, created=False)

        with transaction.atomic():
            soft_deleted_instance = GroupAccessRule._base_manager.filter(
                group=group,
                access_rule=access_rule,
                portal_group=portal_group,
            ).first()

            if soft_deleted_instance:
                soft_deleted_instance.undelete()
                instance = soft_deleted_instance
            else:
                try:
                    instance = serializer.save()
                except IntegrityError:
                    instance = GroupAccessRule._base_manager.filter(
                        group=group,
                        access_rule=access_rule,
                        portal_group=portal_group,
                    ).first()
                    if not instance:
                        raise
                    if getattr(instance, "deleted", None):
                        instance.undelete()

            self.sync_service.create_group_rule(instance)
            return AccessRuleRelationUseCaseResult(instance=instance)


class UpdateGroupAccessRuleUseCase:
    def __init__(
        self,
        sync_service: AccessRuleRelationDeviceSyncService | None = None,
    ) -> None:
        self.sync_service = sync_service or AccessRuleRelationDeviceSyncService()

    def execute(
        self,
        serializer,
        *,
        instance: GroupAccessRule,
    ) -> AccessRuleRelationUseCaseResult:
        old_device_ids = self.sync_service.get_device_ids(instance.portal_group)
        previous_payload = self.sync_service.group_payload(instance)

        with transaction.atomic():
            instance = serializer.save()
            self.sync_service.update_group_rule(
                instance,
                previous_payload=previous_payload,
                old_device_ids=old_device_ids,
            )
            return AccessRuleRelationUseCaseResult(instance=instance)


class DeleteGroupAccessRuleUseCase:
    def __init__(
        self,
        sync_service: AccessRuleRelationDeviceSyncService | None = None,
    ) -> None:
        self.sync_service = sync_service or AccessRuleRelationDeviceSyncService()

    def execute(self, instance: GroupAccessRule) -> None:
        with transaction.atomic():
            self.sync_service.delete_group_rule(instance)
            instance.delete()


class CreatePortalAccessRuleUseCase:
    def __init__(
        self,
        sync_service: AccessRuleRelationDeviceSyncService | None = None,
    ) -> None:
        self.sync_service = sync_service or AccessRuleRelationDeviceSyncService()

    def execute(self, serializer) -> AccessRuleRelationUseCaseResult:
        portal = serializer.validated_data["portal"]
        access_rule = serializer.validated_data["access_rule"]

        instance = PortalAccessRule.objects.filter(
            portal=portal,
            access_rule=access_rule,
        ).first()

        if instance:
            return AccessRuleRelationUseCaseResult(instance=instance, created=False)

        with transaction.atomic():
            soft_deleted_instance = PortalAccessRule._base_manager.filter(
                portal=portal,
                access_rule=access_rule,
            ).first()

            if soft_deleted_instance:
                soft_deleted_instance.undelete()
                instance = soft_deleted_instance
            else:
                try:
                    instance = serializer.save()
                except IntegrityError:
                    instance = PortalAccessRule._base_manager.filter(
                        portal=portal,
                        access_rule=access_rule,
                    ).first()
                    if not instance:
                        raise
                    if getattr(instance, "deleted", None):
                        instance.undelete()

            self.sync_service.create_portal_rule(instance)
            return AccessRuleRelationUseCaseResult(instance=instance)


class UpdatePortalAccessRuleUseCase:
    def __init__(
        self,
        sync_service: AccessRuleRelationDeviceSyncService | None = None,
    ) -> None:
        self.sync_service = sync_service or AccessRuleRelationDeviceSyncService()

    def execute(
        self,
        serializer,
        *,
        instance: PortalAccessRule,
    ) -> AccessRuleRelationUseCaseResult:
        previous_payload = self.sync_service.portal_payload(instance)

        with transaction.atomic():
            instance = serializer.save()
            self.sync_service.update_portal_rule(
                instance,
                previous_payload=previous_payload,
            )
            return AccessRuleRelationUseCaseResult(instance=instance)


class DeletePortalAccessRuleUseCase:
    def __init__(
        self,
        sync_service: AccessRuleRelationDeviceSyncService | None = None,
    ) -> None:
        self.sync_service = sync_service or AccessRuleRelationDeviceSyncService()

    def execute(self, instance: PortalAccessRule) -> None:
        with transaction.atomic():
            self.sync_service.delete_portal_rule(instance)
            instance.delete()


class CreateAccessRuleTimeZoneUseCase:
    def __init__(
        self,
        sync_service: AccessRuleRelationDeviceSyncService | None = None,
    ) -> None:
        self.sync_service = sync_service or AccessRuleRelationDeviceSyncService()

    def execute(self, serializer) -> AccessRuleRelationUseCaseResult:
        access_rule = serializer.validated_data["access_rule"]
        time_zone = serializer.validated_data["time_zone"]

        instance = AccessRuleTimeZone.objects.filter(
            access_rule=access_rule,
            time_zone=time_zone,
        ).first()

        if instance:
            return AccessRuleRelationUseCaseResult(instance=instance, created=False)

        with transaction.atomic():
            soft_deleted_instance = AccessRuleTimeZone._base_manager.filter(
                access_rule=access_rule,
                time_zone=time_zone,
            ).first()

            if soft_deleted_instance:
                soft_deleted_instance.undelete()
                instance = soft_deleted_instance
            else:
                try:
                    instance = serializer.save()
                except IntegrityError:
                    instance = AccessRuleTimeZone._base_manager.filter(
                        access_rule=access_rule,
                        time_zone=time_zone,
                    ).first()
                    if not instance:
                        raise
                    if getattr(instance, "deleted", None):
                        instance.undelete()

            self.sync_service.create_time_zone_rule(instance)
            return AccessRuleRelationUseCaseResult(instance=instance)


class UpdateAccessRuleTimeZoneUseCase:
    def __init__(
        self,
        sync_service: AccessRuleRelationDeviceSyncService | None = None,
    ) -> None:
        self.sync_service = sync_service or AccessRuleRelationDeviceSyncService()

    def execute(
        self,
        serializer,
        *,
        instance: AccessRuleTimeZone,
    ) -> AccessRuleRelationUseCaseResult:
        previous_payload = self.sync_service.time_zone_payload(instance)

        with transaction.atomic():
            instance = serializer.save()
            self.sync_service.update_time_zone_rule(
                instance,
                previous_payload=previous_payload,
            )
            return AccessRuleRelationUseCaseResult(instance=instance)


class DeleteAccessRuleTimeZoneUseCase:
    def __init__(
        self,
        sync_service: AccessRuleRelationDeviceSyncService | None = None,
    ) -> None:
        self.sync_service = sync_service or AccessRuleRelationDeviceSyncService()

    def execute(self, instance: AccessRuleTimeZone) -> None:
        with transaction.atomic():
            self.sync_service.delete_time_zone_rule(instance)
            instance.delete()
