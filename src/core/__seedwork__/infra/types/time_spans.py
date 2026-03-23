from typing import TypedDict


class TimeSpansData(TypedDict):
    id: int
    time_zone_id: int
    start: int
    end: int
    sun: int
    mon: int
    tue: int
    wed: int
    thu: int
    fri: int
    sat: int
    hol1: int
    hol2: int
    hol3: int
    