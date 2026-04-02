from rest_framework import status
from rest_framework.response import Response

from src.core.__seedwork__.infra import ControlIDSyncMixin
from src.core.__seedwork__.infra.mixins._typing import UserGroupLike
from src.core.__seedwork__.infra.types.user_groups import UserGroupsData


class UserGroupsSyncMixin(ControlIDSyncMixin):
    def _target_devices(self, instance: UserGroupLike):
        return list(instance.user.get_target_devices(include_inactive=False))

    def _sync_to_target_devices(self, instance: UserGroupLike, *, method: str) -> Response:
        payload: UserGroupsData = {
            "user_id": instance.user.id,
            "group_id": instance.group.id,
        }
        devices = self._target_devices(instance)
        if not devices:
            return Response({"success": True, "skipped": True}, status=status.HTTP_201_CREATED)

        for device in devices:
            self.set_device(device)
            if method == "create":
                response = self.create_objects("user_groups", [payload])
                expected_status = status.HTTP_201_CREATED
            elif method == "update":
                response = self.update_objects("user_groups", payload, {"user_groups": payload})
                expected_status = status.HTTP_200_OK
            else:
                response = self.destroy_objects(
                    "user_groups",
                    {"user_groups": {"user_id": instance.user.id, "group_id": instance.group.id}},
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
