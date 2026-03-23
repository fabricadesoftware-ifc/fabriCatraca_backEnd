from typing import TypedDict
from enum import IntEnum


class HolidaysGrops(IntEnum):
    GROUP1 = 1
    GROUP2 = 2
    GROUP3 = 3


class HolidaysData(TypedDict):
    id: int
    name: str
    start: int
    end: int
    hol1: HolidaysGrops
    hol2: HolidaysGrops
    hol3: HolidaysGrops
    repeats: int