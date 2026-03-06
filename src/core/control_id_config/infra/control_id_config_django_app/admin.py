from django.contrib import admin
from .models import (
    SystemConfig,
    HardwareConfig,
    SecurityConfig,
    UIConfig,
    CatraConfig,
    PushServerConfig,
    EasySetupLog,
)


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
        "exception_mode",
    )
    list_filter = (
        "beep_enabled",
        "ssh_enabled",
        "bell_enabled",
        "exception_mode",
        "relayN_enabled",
    )
    search_fields = ("device__name",)
    ordering = ("device__name",)


@admin.register(SecurityConfig)
class SecurityConfigAdmin(admin.ModelAdmin):
    list_display = (
        "device",
        "password_only",
        "hide_password_only",
        "hide_name_on_identification",
    )
    list_filter = ("password_only", "hide_password_only", "hide_name_on_identification")
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
    list_display = (
        "device",
        "status",
        "task_id_short",
        "started_at",
        "finished_at",
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
        "started_at",
        "finished_at",
    )

    def task_id_short(self, obj):
        return obj.task_id[:8] if obj.task_id else ""

    task_id_short.short_description = "Task ID"

    def elapsed(self, obj):
        if obj.report and "elapsed_s" in obj.report:
            return f"{obj.report['elapsed_s']}s"
        return "-"

    elapsed.short_description = "Duração"
