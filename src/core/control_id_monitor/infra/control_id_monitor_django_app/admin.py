from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from datetime import timezone as dt_timezone

from .models import MonitorAlert, MonitorAlertRead, MonitorConfig


def format_datetime_utc(value):
    if not value:
        return "—"
    return timezone.localtime(value, dt_timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")


@admin.register(MonitorConfig)
class MonitorConfigAdmin(admin.ModelAdmin):
    @admin.display(description="Last seen at (UTC)")
    def last_seen_at_utc(self, obj):
        return format_datetime_utc(obj.last_seen_at)

    @admin.display(description="Updated at (UTC)")
    def updated_at_utc(self, obj):
        return format_datetime_utc(obj.updated_at)

    @admin.display(description="Last payload at (UTC)")
    def last_payload_at_utc(self, obj):
        return format_datetime_utc(obj.last_payload_at)

    @admin.display(description="Offline since (UTC)")
    def offline_since_utc(self, obj):
        return format_datetime_utc(obj.offline_since)

    @admin.display(description="Created at (UTC)")
    def created_at_utc(self, obj):
        return format_datetime_utc(obj.created_at)

    list_display = [
        "device",
        "is_configured_display",
        "is_offline",
        "last_seen_at_utc",
        "hostname",
        "port",
        "notification_url_display",
        "request_timeout",
        "updated_at_utc",
    ]
    list_filter = ["is_offline", "created_at", "updated_at"]
    search_fields = ["device__name", "hostname"]
    readonly_fields = [
        "created_at_utc",
        "updated_at_utc",
        "full_url",
        "is_configured",
        "last_seen_at_utc",
        "last_payload_at_utc",
        "last_signal_source",
        "offline_since_utc",
        "offline_detection_paused_until",
        "is_offline",
    ]
    fieldsets = (
        ("Dispositivo", {"fields": ("device",)}),
        (
            "Configuracoes do Servidor de Notificacoes",
            {"fields": ("hostname", "port", "path", "request_timeout", "heartbeat_timeout_seconds")},
        ),
        (
            "Saude da Catraca",
            {"fields": ("is_offline", "offline_since_utc", "last_seen_at_utc", "last_payload_at_utc", "last_signal_source")},
        ),
        ("Status", {"fields": ("is_configured", "full_url", "created_at_utc", "updated_at_utc"), "classes": ("collapse",)}),
    )

    def is_configured_display(self, obj):
        if obj.is_configured:
            return format_html('<span style="color: green;">? Ativo</span>')
        return format_html('<span style="color: gray;">? Inativo</span>')

    is_configured_display.short_description = "Status"

    def notification_url_display(self, obj):
        if obj.is_configured:
            return format_html('<a href="{}" target="_blank">{}</a>', obj.full_url, obj.full_url)
        return format_html('<span style="color: gray;">(nao configurado)</span>')

    notification_url_display.short_description = "URL de Notificacao"


@admin.register(MonitorAlert)
class MonitorAlertAdmin(admin.ModelAdmin):
    @admin.display(description="Started at (UTC)")
    def started_at_utc(self, obj):
        return format_datetime_utc(obj.started_at)

    @admin.display(description="Resolved at (UTC)")
    def resolved_at_utc(self, obj):
        return format_datetime_utc(obj.resolved_at)

    list_display = ("title", "type", "severity", "device", "user", "is_active", "started_at_utc", "resolved_at_utc")
    list_filter = ("type", "severity", "is_active", "started_at", "resolved_at")
    search_fields = ("title", "message", "device__name", "user__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(MonitorAlertRead)
class MonitorAlertReadAdmin(admin.ModelAdmin):
    @admin.display(description="Read at (UTC)")
    def read_at_utc(self, obj):
        return format_datetime_utc(obj.read_at)

    list_display = ("alert", "user", "read_at_utc")
    search_fields = ("alert__title", "user__name", "user__email")
    readonly_fields = ("read_at_utc",)
