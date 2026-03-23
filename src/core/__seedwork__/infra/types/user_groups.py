from typing import TypedDict


class UserGroupsData(TypedDict):
    user_id: int
    group_id: int


# Backward compatibility alias for previous typo name.
UsergGroupsData = UserGroupsData