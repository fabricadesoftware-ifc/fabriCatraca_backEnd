from rest_framework import status
from rest_framework.response import Response
from django.utils import timezone

from src.core.__seedwork__.infra import ControlIDSyncMixin
from src.core.__seedwork__.infra.mixins._typing import UserGroupLike
from src.core.__seedwork__.infra.types.user_groups import UserGroupsData


class UserGroupsSyncMixin(ControlIDSyncMixin):
    @staticmethod
    def _datetime_to_device_timestamp(value):
        if not value:
            return 0

        aware_value = value
        if timezone.is_naive(aware_value):
            aware_value = timezone.make_aware(
                aware_value,
                timezone.get_current_timezone(),
            )
        return int(aware_value.timestamp())

    def _build_user_payload(self, instance: UserGroupLike):
        return {
            "id": instance.user.id,
            "name": instance.user.name,
            "registration": instance.user.registration or "",
            "begin_time": self._datetime_to_device_timestamp(instance.user.start_date),
            "end_time": self._datetime_to_device_timestamp(instance.user.end_date),
        }

    def _build_group_payload(self, instance: UserGroupLike):
        return {
            "id": instance.group.id,
            "name": instance.group.name,
        }

    def _ensure_parent_objects_on_device(self, instance: UserGroupLike) -> Response:
        group_response = self.create_or_update_objects(
            "groups",
            [self._build_group_payload(instance)],
        )
        if group_response.status_code != status.HTTP_200_OK:
            return group_response

        user_response = self.create_or_update_objects(
            "users",
            [self._build_user_payload(instance)],
        )
        if user_response.status_code != status.HTTP_200_OK:
            return user_response

        return Response({"success": True}, status=status.HTTP_200_OK)

    def _target_devices(self, instance: UserGroupLike):
        return list(instance.user.get_target_devices(include_inactive=False))

    def _sync_to_target_devices(
        self, instance: UserGroupLike, *, method: str
    ) -> Response:
        payload: UserGroupsData = {
            "user_id": instance.user.id,
            "group_id": instance.group.id,
        }
        devices = self._target_devices(instance)
        if not devices:
            return Response(
                {"success": True, "skipped": True}, status=status.HTTP_201_CREATED
            )

        for device in devices:
            self.set_device(device)
            if method == "create":
                parent_response = self._ensure_parent_objects_on_device(instance)
                if parent_response.status_code != status.HTTP_200_OK:
                    return parent_response

                response = self.create_or_update_objects("user_groups", [payload])
                if response.status_code == status.HTTP_200_OK:
                    response.status_code = status.HTTP_201_CREATED
                expected_status = status.HTTP_201_CREATED
            elif method == "update":
                parent_response = self._ensure_parent_objects_on_device(instance)
                if parent_response.status_code != status.HTTP_200_OK:
                    return parent_response

                response = self.update_objects(
                    "user_groups", payload, {"user_groups": payload}
                )
                expected_status = status.HTTP_200_OK
            else:
                response = self.destroy_objects(
                    "user_groups",
                    {
                        "user_groups": {
                            "user_id": instance.user.id,
                            "group_id": instance.group.id,
                        }
                    },
                )
                expected_status = status.HTTP_204_NO_CONTENT

            if response.status_code != expected_status:
                return response

        return Response({"success": True}, status=expected_status)

    def create_in_catraca(self, instance: UserGroupLike) -> Response:
        return self._sync_to_target_devices(instance, method="create")

    def update_in_catraca(self, instance: UserGroupLike) -> Response:
        return self._sync_to_target_devices(instance, method="update")

    def delete_in_catraca(self, instance: UserGroupLike) -> Response:
        return self._sync_to_target_devices(instance, method="delete")
