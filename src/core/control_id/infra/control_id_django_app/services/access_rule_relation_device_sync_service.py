from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from rest_framework import status

from src.core.__seedwork__.infra.catraca_sync import CatracaSyncError
from src.core.control_id.infra.control_id_django_app.gateways import ControlIDGateway
from src.core.control_id.infra.control_id_django_app.models import (
    AccessRuleTimeZone,
    Device,
    GroupAccessRule,
    PortalGroup,
    PortalAccessRule,
    UserAccessRule,
)


class AccessRuleRelationSyncError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details


class AccessRuleRelationDeviceSyncService:
    def __init__(self, gateway: ControlIDGateway | None = None) -> None:
        self.gateway = gateway or ControlIDGateway()

    @staticmethod
    def get_device_ids(portal_group: PortalGroup | None) -> list[int] | None:
        if portal_group:
            return list(portal_group.active_devices().values_list("id", flat=True))
        return None

    @staticmethod
    def get_all_active_device_ids() -> set[int]:
        return set(
            Device.objects.filter(is_active=True).values_list("id", flat=True)
        )

    def expand_device_ids(self, device_ids: list[int] | None) -> set[int]:
        if device_ids is None:
            return self.get_all_active_device_ids()
        return set(device_ids)

    @staticmethod
    def user_payload(instance: UserAccessRule) -> dict[str, int]:
        return {
            "user_id": instance.user_id,
            "access_rule_id": instance.access_rule_id,
        }

    @staticmethod
    def group_payload(instance: GroupAccessRule) -> dict[str, int]:
        return {
            "group_id": instance.group_id,
            "access_rule_id": instance.access_rule_id,
        }

    @staticmethod
    def portal_payload(instance: PortalAccessRule) -> dict[str, int]:
        return {
            "portal_id": instance.portal_id,
            "access_rule_id": instance.access_rule_id,
        }

    @staticmethod
    def time_zone_payload(instance: AccessRuleTimeZone) -> dict[str, int]:
        return {
            "access_rule_id": instance.access_rule_id,
            "time_zone_id": instance.time_zone_id,
        }

    def _raise_sync_error(
        self,
        message: str,
        *,
        response=None,
        exc: CatracaSyncError | None = None,
    ) -> None:
        if exc is not None:
            raise AccessRuleRelationSyncError(
                message,
                status_code=exc.status_code or status.HTTP_400_BAD_REQUEST,
                details=str(exc),
            ) from exc

        raise AccessRuleRelationSyncError(
            message,
            status_code=getattr(response, "status_code", status.HTTP_400_BAD_REQUEST),
            details=getattr(response, "data", None),
        )

    def _create_relation(
        self,
        *,
        object_name: str,
        payload: dict[str, int],
        device_ids: list[int] | None,
    ) -> None:
        try:
            response = self.gateway.create_or_update_objects(
                object_name,
                [payload],
                device_ids=device_ids,
            )
        except CatracaSyncError as exc:
            self._raise_sync_error(
                f"Erro ao criar vinculo de regra em {object_name}.",
                exc=exc,
            )

        if response.status_code != status.HTTP_200_OK:
            self._raise_sync_error(
                f"Erro ao criar vinculo de regra em {object_name}.",
                response=response,
            )

    def _update_relation(
        self,
        *,
        object_name: str,
        payload: dict[str, int],
        where_payload: dict[str, int],
        device_ids: list[int] | None,
    ) -> None:
        try:
            response = self.gateway.update_objects(
                object_name,
                payload,
                {object_name: where_payload},
                device_ids=device_ids,
            )
        except CatracaSyncError as exc:
            self._raise_sync_error(
                f"Erro ao atualizar vinculo de regra em {object_name}.",
                exc=exc,
            )

        if response.status_code != status.HTTP_200_OK:
            self._raise_sync_error(
                f"Erro ao atualizar vinculo de regra em {object_name}.",
                response=response,
            )

    def _delete_relation(
        self,
        *,
        object_name: str,
        payload: dict[str, int],
        device_ids: list[int] | None,
    ) -> None:
        try:
            response = self.gateway.destroy_objects(
                object_name,
                {object_name: payload},
                device_ids=device_ids,
            )
        except CatracaSyncError as exc:
            self._raise_sync_error(
                f"Erro ao remover vinculo de regra em {object_name}.",
                exc=exc,
            )

        if response.status_code != status.HTTP_204_NO_CONTENT:
            self._raise_sync_error(
                f"Erro ao remover vinculo de regra em {object_name}.",
                response=response,
            )

    @staticmethod
    def _as_device_id_list(device_ids: Iterable[int]) -> list[int]:
        return sorted(set(device_ids))

    def _sync_update_relation(
        self,
        *,
        object_name: str,
        payload: dict[str, int],
        previous_payload: dict[str, int],
        old_device_ids: list[int] | None,
        new_device_ids: list[int] | None,
    ) -> None:
        if old_device_ids == new_device_ids:
            self._update_relation(
                object_name=object_name,
                payload=payload,
                where_payload=previous_payload,
                device_ids=new_device_ids,
            )
            return

        old_set = self.expand_device_ids(old_device_ids)
        new_set = self.expand_device_ids(new_device_ids)

        removed = old_set - new_set
        added = new_set - old_set
        common = old_set & new_set

        if removed:
            self._delete_relation(
                object_name=object_name,
                payload=previous_payload,
                device_ids=self._as_device_id_list(removed),
            )
        if added:
            self._create_relation(
                object_name=object_name,
                payload=payload,
                device_ids=self._as_device_id_list(added),
            )
        if common:
            self._update_relation(
                object_name=object_name,
                payload=payload,
                where_payload=previous_payload,
                device_ids=self._as_device_id_list(common),
            )

    def create_user_rule(self, instance: UserAccessRule) -> None:
        self._create_relation(
            object_name="user_access_rules",
            payload=self.user_payload(instance),
            device_ids=self.get_device_ids(instance.portal_group),
        )

    def update_user_rule(
        self,
        instance: UserAccessRule,
        *,
        previous_payload: dict[str, int],
        old_device_ids: list[int] | None,
    ) -> None:
        self._sync_update_relation(
            object_name="user_access_rules",
            payload=self.user_payload(instance),
            previous_payload=previous_payload,
            old_device_ids=old_device_ids,
            new_device_ids=self.get_device_ids(instance.portal_group),
        )

    def delete_user_rule(self, instance: UserAccessRule) -> None:
        self._delete_relation(
            object_name="user_access_rules",
            payload=self.user_payload(instance),
            device_ids=self.get_device_ids(instance.portal_group),
        )

    def create_group_rule(self, instance: GroupAccessRule) -> None:
        self._create_relation(
            object_name="group_access_rules",
            payload=self.group_payload(instance),
            device_ids=self.get_device_ids(instance.portal_group),
        )

    def update_group_rule(
        self,
        instance: GroupAccessRule,
        *,
        previous_payload: dict[str, int],
        old_device_ids: list[int] | None,
    ) -> None:
        self._sync_update_relation(
            object_name="group_access_rules",
            payload=self.group_payload(instance),
            previous_payload=previous_payload,
            old_device_ids=old_device_ids,
            new_device_ids=self.get_device_ids(instance.portal_group),
        )

    def delete_group_rule(self, instance: GroupAccessRule) -> None:
        self._delete_relation(
            object_name="group_access_rules",
            payload=self.group_payload(instance),
            device_ids=self.get_device_ids(instance.portal_group),
        )

    def create_portal_rule(self, instance: PortalAccessRule) -> None:
        self._create_relation(
            object_name="portal_access_rules",
            payload=self.portal_payload(instance),
            device_ids=None,
        )

    def update_portal_rule(
        self,
        instance: PortalAccessRule,
        *,
        previous_payload: dict[str, int],
    ) -> None:
        self._update_relation(
            object_name="portal_access_rules",
            payload=self.portal_payload(instance),
            where_payload=previous_payload,
            device_ids=None,
        )

    def delete_portal_rule(self, instance: PortalAccessRule) -> None:
        self._delete_relation(
            object_name="portal_access_rules",
            payload=self.portal_payload(instance),
            device_ids=None,
        )

    def create_time_zone_rule(self, instance: AccessRuleTimeZone) -> None:
        self._create_relation(
            object_name="access_rule_time_zones",
            payload=self.time_zone_payload(instance),
            device_ids=None,
        )

    def update_time_zone_rule(
        self,
        instance: AccessRuleTimeZone,
        *,
        previous_payload: dict[str, int],
    ) -> None:
        self._update_relation(
            object_name="access_rule_time_zones",
            payload=self.time_zone_payload(instance),
            where_payload=previous_payload,
            device_ids=None,
        )

    def delete_time_zone_rule(self, instance: AccessRuleTimeZone) -> None:
        self._delete_relation(
            object_name="access_rule_time_zones",
            payload=self.time_zone_payload(instance),
            device_ids=None,
        )
