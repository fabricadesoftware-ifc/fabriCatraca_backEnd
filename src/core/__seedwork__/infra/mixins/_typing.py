from typing import Protocol


class HasId(Protocol):
    id: int


class AccessRuleLike(Protocol):
    id: int
    name: str
    type: int
    priority: int


class AreaLike(Protocol):
    id: int
    name: str


class UserCardLike(Protocol):
    id: int
    value: str


class GroupLike(Protocol):
    id: int
    name: str


class PortalLike(Protocol):
    id: int
    name: str
    area_from: HasId
    area_to: HasId


class AccessRuleTimeZoneLike(Protocol):
    access_rule: HasId
    time_zone: HasId


class GroupAccessRuleLike(Protocol):
    group: HasId
    access_rule: HasId


class PortalAccessRuleLike(Protocol):
    portal_id: int
    access_rule: HasId


class TemplateLike(Protocol):
    id: int
    user: HasId
    template: str


class TimeSpanLike(Protocol):
    id: int
    time_zone: HasId
    start: int
    end: int
    sun: bool
    mon: bool
    tue: bool
    wed: bool
    thu: bool
    fri: bool
    sat: bool
    hol1: bool
    hol2: bool
    hol3: bool


class TimeZoneLike(Protocol):
    id: int
    name: str


class UserAccessRuleLike(Protocol):
    user: HasId
    access_rule: HasId


class UserGroupLike(Protocol):
    user: HasId
    group: HasId


class GeneralConfigLike(Protocol):
    auto_reboot_hour: int
    auto_reboot_minute: int
    clear_expired_users: bool
    url_reboot_enabled: bool
    keep_user_image: bool
    beep_enabled: bool
    ssh_enabled: bool
    relayN_enabled: bool
    relayN_timeout: int
    relayN_auto_close: bool
    door_sensorN_enabled: bool
    door_sensorN_idle: bool
    doorN_interlock: bool
    bell_enabled: bool
    bell_relay: int
    catra_timeout: int
    online: bool
    local_identification: bool
    exception_mode: int
    doorN_exception_mode: int
    language: str
    daylight_savings_time_start: int
    daylight_savings_time_end: int
    password_only: bool
    hide_password_only: bool
    password_only_tip: str
    hide_name_on_identification: bool
    denied_transaction_code: int
    send_code_when_not_identified: bool
    send_code_when_not_authorized: bool
    web_server_enabled: bool
