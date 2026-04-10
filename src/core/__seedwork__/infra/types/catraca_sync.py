from typing import TypedDict, Literal


class RemoteEnrollBioResponse(TypedDict):
    type: Literal["biometry"]
    finger_type: int
    template: str
    template_size: int
    success: bool
    user_id: int
    device_id: int
    erro: str


class RemoteEnrollCardResponse(TypedDict):
    type: Literal["card"]
    card_value: int
    success: bool
    user_id: int
    device_id: int
    erro: str
