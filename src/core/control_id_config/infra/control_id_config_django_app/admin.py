from django.contrib import admin
from django.utils import timezone
from datetime import timezone as dt_timezone
from .models import (
    SystemConfig,
    HardwareConfig,
    SecurityConfig,
    UIConfig,
    CatraConfig,
    PushServerConfig,
    EasySetupLog,
)


def format_datetime_utc(value):
    if not value:
        return "—"
    return timezone.localtime(value, dt_timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")


@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = (
        "device",
        "auto_reboot_hour",
        "auto_reboot_minute",
        "online",
        "web_server_enabled",
    )
    list_filter = (
        "online",
        "web_server_enabled",
        "clear_expired_users",
        "url_reboot_enabled",
    )
    search_fields = ("device__name",)
    ordering = ("device__name",)


@admin.register(HardwareConfig)
class HardwareConfigAdmin(admin.ModelAdmin):
    list_display = (
        "device",
        "beep_enabled",
        "ssh_enabled",
        "bell_enabled",
        "network_interlock_enabled",
        "exception_mode",
    )
    list_filter = (
        "beep_enabled",
        "ssh_enabled",
        "bell_enabled",
        "network_interlock_enabled",
        "exception_mode",
        "relayN_enabled",
    )
    search_fields = ("device__name",)
    ordering = ("device__name",)


@admin.register(SecurityConfig)
class SecurityConfigAdmin(admin.ModelAdmin):
    list_display = (
        "device",
        "verbose_logging_enabled",
        "log_type",
        "multi_factor_authentication_enabled",
    )
    list_filter = ("verbose_logging_enabled", "log_type", "multi_factor_authentication_enabled")
    search_fields = ("device__name",)
    ordering = ("device__name",)


@admin.register(UIConfig)
class UIConfigAdmin(admin.ModelAdmin):
    list_display = ("device", "screen_always_on")
    list_filter = ("screen_always_on",)
    search_fields = ("device__name",)
    ordering = ("device__name",)


@admin.register(CatraConfig)
class CatraConfigAdmin(admin.ModelAdmin):
    list_display = (
        "device",
        "anti_passback",
        "daily_reset",
        "gateway",
        "operation_mode",
    )
    list_filter = ("anti_passback", "daily_reset", "gateway", "operation_mode")
    search_fields = ("device__name",)
    ordering = ("device__name",)
    fieldsets = (
        ("Informações do Dispositivo", {"fields": ("device",)}),
        ("Controle de Acesso", {"fields": ("anti_passback", "daily_reset")}),
        ("Operação da Catraca", {"fields": ("gateway", "operation_mode")}),
    )


@admin.register(PushServerConfig)
class PushServerConfigAdmin(admin.ModelAdmin):
    list_display = (
        "device",
        "push_request_timeout",
        "push_request_period",
        "push_remote_address_display",
    )
    list_filter = ("push_request_timeout", "push_request_period")
    search_fields = ("device__name", "push_remote_address")
    ordering = ("device__name",)
    fieldsets = (
        ("Informações do Dispositivo", {"fields": ("device",)}),
        (
            "Configurações de Timeout e Período",
            {"fields": ("push_request_timeout", "push_request_period")},
        ),
        ("Endereço do Servidor", {"fields": ("push_remote_address",)}),
    )

    def push_remote_address_display(self, obj):
        """Exibe endereço remoto de forma amigável"""
        return obj.push_remote_address or "(não configurado)"

    push_remote_address_display.short_description = "Endereço Remoto"


@admin.register(EasySetupLog)
class EasySetupLogAdmin(admin.ModelAdmin):
    @admin.display(description="Started at (UTC)")
    def started_at_utc(self, obj):
        return format_datetime_utc(obj.started_at)

    @admin.display(description="Finished at (UTC)")
    def finished_at_utc(self, obj):
        return format_datetime_utc(obj.finished_at)

    list_display = (
        "device",
        "status",
        "task_id_short",
        "started_at_utc",
        "finished_at_utc",
        "elapsed",
    )
    list_filter = ("status", "started_at")
    search_fields = ("device__name", "task_id")
    ordering = ("-started_at",)
    readonly_fields = (
        "task_id",
        "device",
        "status",
        "report",
        "started_at_utc",
        "finished_at_utc",
    )

    def task_id_short(self, obj):
        return obj.task_id[:8] if obj.task_id else ""

    task_id_short.short_description = "Task ID"

    def elapsed(self, obj):
        if obj.report and "elapsed_s" in obj.report:
            return f"{obj.report['elapsed_s']}s"
        return "-"

    elapsed.short_description = "Duração"
