from django.contrib import admin
from django.utils.html import format_html

from .models import MonitorAlert, MonitorAlertRead, MonitorConfig


@admin.register(MonitorConfig)
class MonitorConfigAdmin(admin.ModelAdmin):
    list_display = [
        "device",
        "is_configured_display",
        "is_offline",
        "last_seen_at",
        "hostname",
        "port",
        "notification_url_display",
        "request_timeout",
        "updated_at",
    ]
    list_filter = ["is_offline", "created_at", "updated_at"]
    search_fields = ["device__name", "hostname"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "full_url",
        "is_configured",
        "last_seen_at",
        "last_payload_at",
        "last_signal_source",
        "offline_since",
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
            {"fields": ("is_offline", "offline_since", "last_seen_at", "last_payload_at", "last_signal_source")},
        ),
        ("Status", {"fields": ("is_configured", "full_url", "created_at", "updated_at"), "classes": ("collapse",)}),
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
    list_display = ("title", "type", "severity", "device", "user", "is_active", "started_at", "resolved_at")
    list_filter = ("type", "severity", "is_active", "started_at", "resolved_at")
    search_fields = ("title", "message", "device__name", "user__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(MonitorAlertRead)
class MonitorAlertReadAdmin(admin.ModelAdmin):
    list_display = ("alert", "user", "read_at")
    search_fields = ("alert__title", "user__name", "user__email")
    readonly_fields = ("read_at",)
