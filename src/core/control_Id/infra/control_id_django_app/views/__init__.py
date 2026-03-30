from .template import TemplateViewSet
from .timezone import TimeZoneViewSet
from .timespan import TimeSpanViewSet
from .access_rule import AccessRuleViewSet
from .user_access_rule import UserAccessRuleViewSet
from .access_rule_timezone import AccessRuleTimeZoneViewSet
from .portal import PortalViewSet
from .portal_access_rule import PortalAccessRuleViewSet
from .cards import CardViewSet
from .areas import AreaViewSet
from .group import GroupViewSet
from .user_groups import UserGroupViewSet
from .group_access_rules import GroupAccessRulesViewSet
from .sync import sync_all, sync_status, sync_device_config
from .device import DeviceViewSet
from .access_logs import AccessLogsViewSet
from .device_actions import (
    buzzer_buzz,
    message_to_screen,
    remote_user_authorization,
)
from .temporary_user_release import TemporaryUserReleaseViewSet
from .temporary_group_release import TemporaryGroupReleaseViewSet
from .release_audit import ReleaseAuditViewSet



__all__ = [
    'TemplateViewSet',
    'TimeZoneViewSet',
    'TimeSpanViewSet',
    'AccessRuleViewSet',
    'UserAccessRuleViewSet',
    'AccessRuleTimeZoneViewSet',
    'PortalViewSet',
    'PortalAccessRuleViewSet',
    'CardViewSet',
    'AreaViewSet',
    'GroupViewSet',
    'UserGroupViewSet',
    'GroupAccessRulesViewSet',
    #'sync_all', TODO: Rever sync_all para não expor essa funcionalidade via API peraza 2k26
    'sync_status',
    'sync_device_config',
    'DeviceViewSet',
    'AccessLogsViewSet',
    'message_to_screen',
    'buzzer_buzz',
    'remote_user_authorization',
    'TemporaryUserReleaseViewSet',
    'TemporaryGroupReleaseViewSet',
    'ReleaseAuditViewSet',
]
