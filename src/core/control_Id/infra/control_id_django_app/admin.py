from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from src.core.control_Id.infra.control_id_django_app.models import (
    Template,
    TimeZone,
    TimeSpan,
    AccessRule,
    UserAccessRule,
    AccessRuleTimeZone,
    PortalAccessRule,
    Card,
    CustomGroup,
    UserGroup,
    GroupAccessRule,
    Portal,
    Area,
    AccessLogs,
)
from src.core.control_Id.infra.control_id_django_app.models.device import Device


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "finger_type", "finger_position")
    search_fields = ("user__name", "id")


@admin.register(TimeZone)
class TimeZoneAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(TimeSpan)
class TimeSpanAdmin(admin.ModelAdmin):
    list_display = ("id", "time_zone", "start", "end")
    list_filter = ("time_zone",)


@admin.register(AccessRule)
class AccessRuleAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "type", "priority")
    search_fields = ("name",)
    list_filter = ("type",)


@admin.register(UserAccessRule)
class UserAccessRuleAdmin(admin.ModelAdmin):
    list_display = ("id", "user_id", "access_rule_id")
    search_fields = ("user_id__name", "access_rule_id__name")


@admin.register(AccessRuleTimeZone)
class AccessRuleTimeZoneAdmin(admin.ModelAdmin):
    list_display = ("id", "access_rule_id", "time_zone_id")
    list_filter = ("access_rule_id", "time_zone_id")


@admin.register(PortalAccessRule)
class PortalAccessRuleAdmin(admin.ModelAdmin):
    list_display = ("id", "portal_id", "access_rule_id")
    list_filter = ("portal_id",)


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ("id", "value", "user")
    search_fields = ("value", "user__name")


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "ip", "is_active", "is_default")
    list_filter = ("is_active", "is_default")
    search_fields = ("name", "ip")
    ordering = ("name",)


@admin.register(Portal)
class PortalAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "area_from_id", "area_to_id")
    search_fields = ("name",)


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(CustomGroup)
class CustomGroupAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(UserGroup)
class UserGroupAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "group")
    search_fields = ("user__name", "group__name")


@admin.register(GroupAccessRule)
class GroupAccessRuleAdmin(admin.ModelAdmin):
    list_display = ("id", "group", "access_rule")
    search_fields = ("group__name", "access_rule__name")


@admin.register(AccessLogs)
class AccessLogsAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "time",
        "user",
        "device",
        "portal",
        "event_type",
        "access_rule",
    )
    list_filter = ("event_type", "device", "portal")
    search_fields = ("user__name", "device__name", "portal__name")


# Register your models here.
