from typing import TypedDict
from enum import IntEnum

class ActionRunAt(IntEnum):
    DEVICE = 1
    ALL_DEVICES = 2
    SERVER = 3

class ActionsData(TypedDict):
    group_id: int
    name: str
    actions: str
    parameters: str
    run_at: ActionRunAt