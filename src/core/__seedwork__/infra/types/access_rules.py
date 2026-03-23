from typing import TypedDict
from enum import IntEnum


class AccessRuleType(IntEnum):
    BLOCK = 0  # Regra de bloqueio
    ALLOW = 1  # Regra de liberação

class AccessRuleData(TypedDict):
    id: int
    name: str
    type: AccessRuleType
    priority: int
    