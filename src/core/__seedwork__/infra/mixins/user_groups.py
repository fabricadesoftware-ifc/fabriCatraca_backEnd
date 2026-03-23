from src.core.__seedwork__.infra import ControlIDSyncMixin
from rest_framework.response import Response

from src.core.__seedwork__.infra.mixins._typing import UserGroupLike
from src.core.__seedwork__.infra.types.user_groups import UserGroupsData


class UserGroupsSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance: UserGroupLike) -> Response:
        payload: UserGroupsData = {
            "user_id": instance.user.id,
            "group_id": instance.group.id,
        }
        response = self.create_objects(
            "user_groups",
            [payload],
        )
        return response

    def update_in_catraca(self, instance: UserGroupLike) -> Response:
        payload: UserGroupsData = {
            "user_id": instance.user.id,
            "group_id": instance.group.id,
        }
        response = self.update_objects(
            "user_groups",
            payload,
            {"user_groups": payload},
        )
        return response

    def delete_in_catraca(self, instance: UserGroupLike) -> Response:
        response = self.destroy_objects(
            "user_groups",
            {
                "user_groups": {
                    "user_id": instance.user.id,
                    "group_id": instance.group.id,
                }
            },
        )
        return response
