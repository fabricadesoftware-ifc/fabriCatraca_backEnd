from typing import TypedDict


class CatraInfosData(TypedDict):
    id: int
    left_turns: int
    right_turns: int
    entrance_turns: int
    exit_turns: int