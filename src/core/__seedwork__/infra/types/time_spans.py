from typing import TypedDict
from enum import IntEnum


class TimeSpansData(TypedDict):
    id: int
    time_zoned_id: int
    start: int
    end: int
    sun: IntEnum
    mon: IntEnum
    tue: IntEnum
    wed: IntEnum
    thu: IntEnum
    fri: IntEnum
    sat: IntEnum
    hol1: IntEnum
    hol2: IntEnum
    hol3: IntEnum
    