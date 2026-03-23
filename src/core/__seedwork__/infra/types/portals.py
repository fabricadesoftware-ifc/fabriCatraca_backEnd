from typing import TypedDict


class PortalData(TypedDict):
    id: int
    name: str
    area_from_id: int
    area_to_id: int