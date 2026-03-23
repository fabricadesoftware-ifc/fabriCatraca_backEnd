from src.core.__seedwork__.infra import ControlIDSyncMixin
from rest_framework.response import Response
from src.core.__seedwork__.infra.mixins._typing import UserCardLike
from src.core.__seedwork__.infra.types import CardsData

class CardSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance: UserCardLike) -> Response:
        payload: CardsData = {
            "id": instance.id,
            "value": instance.value,
        }
        response = self.create_objects("cards", [payload])
        return response
    
    def update_in_catraca(self, instance: UserCardLike) -> Response:
        payload: CardsData = {
            "id": instance.id,
            "value": instance.value,
        }
        response = self.update_objects(
            "cards",
            payload,
            {"cards": {"id": instance.id}},
        )
        return response
    
    def delete_in_catraca(self, instance: UserCardLike) -> Response:
        response = self.destroy_objects(
            "cards",
            {"cards": {"id": instance.id}},
        )
        return response
    