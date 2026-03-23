from typing import NotRequired, TypedDict


class CardsData(TypedDict):
    id: int
    value: str
    user_id: NotRequired[int]