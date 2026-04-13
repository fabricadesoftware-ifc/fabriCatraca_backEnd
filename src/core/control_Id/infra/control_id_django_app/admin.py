from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from datetime import timezone as dt_timezone
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
    ReleaseAudit,
    TemporaryUserRelease,
    TemporaryGroupRelease
)
from src.core.control_Id.infra.control_id_django_app.models.device import Device


def format_datetime_utc(value):
    if not value:
        return "—"
    return timezone.localtime(value, dt_timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")


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
    @admin.display(description="Time (UTC)")
    def time_utc(self, obj):
        return format_datetime_utc(obj.time)

    list_display = (
        "id",
        "time_utc",
        "user",
        "device",
        "portal",
        "event_type",
        "access_rule",
    )
    list_filter = ("event_type", "device", "portal")
    search_fields = ("user__name", "device__name", "portal__name")


@admin.register(TemporaryUserRelease)
class TemporaryUserReleaseAdmin(admin.ModelAdmin):
    @admin.display(description="Valid until (UTC)")
    def valid_until_utc(self, obj):
        return format_datetime_utc(obj.valid_until)

    @admin.display(description="Activated at (UTC)")
    def activated_at_utc(self, obj):
        return format_datetime_utc(obj.activated_at)

    @admin.display(description="Closed at (UTC)")
    def closed_at_utc(self, obj):
        return format_datetime_utc(obj.closed_at)

    list_display = (
        "id",
        "user",
        "requested_by",
        "access_rule",
        "status",
        "valid_until_utc",
        "activated_at_utc",
        "closed_at_utc",
    )
    list_filter = ("status", "access_rule")
    search_fields = ("user__name", "requested_by__name", "notes", "result_message")

@admin.register(TemporaryGroupRelease)
class TemporaryGroupReleaseAdmin(admin.ModelAdmin):
    @admin.display(description="Valid until (UTC)")
    def valid_until_utc(self, obj):
        return format_datetime_utc(obj.valid_until)

    @admin.display(description="Activated at (UTC)")
    def activated_at_utc(self, obj):
        return format_datetime_utc(obj.activated_at)

    @admin.display(description="Closed at (UTC)")
    def closed_at_utc(self, obj):
        return format_datetime_utc(obj.closed_at)

    list_display = (
        "id",
        "group",
        "requested_by",
        "access_rule",
        "status",
        "valid_until_utc",
        "activated_at_utc",
        "closed_at_utc",
    )
    list_filter = ("status", "access_rule")
    search_fields = ("group__name", "requested_by__name", "notes", "result_message")


@admin.register(ReleaseAudit)
class ReleaseAuditAdmin(admin.ModelAdmin):
    @admin.display(description="Requested at (UTC)")
    def requested_at_utc(self, obj):
        return format_datetime_utc(obj.requested_at)

    @admin.display(description="Scheduled for (UTC)")
    def scheduled_for_utc(self, obj):
        return format_datetime_utc(obj.scheduled_for)

    list_display = (
        "id",
        "release_type",
        "status",
        "requested_by_name",
        "target_user_name",
        "device",
        "portal",
        "requested_at_utc",
        "scheduled_for_utc",
    )
    list_filter = ("release_type", "status", "requested_by_role")
    search_fields = (
        "requested_by_name",
        "requested_by_email",
        "target_user_name",
        "target_user_registration",
        "notes",
        "error_message",
    )
    readonly_fields = ("created_at", "updated_at", "request_payload", "response_payload")


# Register your models here.
