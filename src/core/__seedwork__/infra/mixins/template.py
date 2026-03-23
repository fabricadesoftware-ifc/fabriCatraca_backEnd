from src.core.__seedwork__.infra import ControlIDSyncMixin
from rest_framework.response import Response
from typing import TypedDict

from src.core.__seedwork__.infra.mixins._typing import TemplateLike


class TemplateData(TypedDict):
    id: int
    user_id: int
    template: str
    finger_type: int
    finger_position: int

class TemplateSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance: TemplateLike) -> Response:
        payload: TemplateData = {
            "id": instance.id,
            "user_id": instance.user.id,
            "template": instance.template,
            "finger_type": 0,  # dedo comum
            "finger_position": 0,  # campo reservado
        }
        response = self.create_objects("templates", [payload])
        return response

    def update_in_catraca(self, instance: TemplateLike) -> Response:
        payload: TemplateData = {
            "id": instance.id,
            "user_id": instance.user.id,
            "template": instance.template,
            "finger_type": 0,  # dedo comum
            "finger_position": 0,  # campo reservado
        }
        response = self.update_objects(
            "templates",
            payload,
            {"templates": {"id": instance.id}},
        )
        return response

    def delete_in_catraca(self, instance: TemplateLike) -> Response:
        response = self.destroy_objects(
            "templates",
            {"templates": {"id": instance.id}},
        )
        return response

