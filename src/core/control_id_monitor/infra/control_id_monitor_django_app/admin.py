from django.contrib import admin
from django.utils.html import format_html
from .models import MonitorConfig


@admin.register(MonitorConfig)
class MonitorConfigAdmin(admin.ModelAdmin):
    """
    Admin para MonitorConfig - Sistema de Push de Logs em Tempo Real
    """
    list_display = [
        'device', 
        'is_configured_display',
        'hostname', 
        'port', 
        'notification_url_display',
        'request_timeout',
        'updated_at'
    ]
    list_filter = ['created_at', 'updated_at']
    search_fields = ['device__name', 'hostname']
    readonly_fields = ['created_at', 'updated_at', 'full_url', 'is_configured']
    
    fieldsets = (
        ('Dispositivo', {
            'fields': ('device',)
        }),
        ('Configurações do Servidor de Notificações', {
            'fields': ('hostname', 'port', 'path', 'request_timeout'),
            'description': 'Configure o servidor que receberá as notificações em tempo real'
        }),
        ('Status', {
            'fields': ('is_configured', 'full_url', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_configured_display(self, obj):
        """Mostra status de configuração com ícone"""
        if obj.is_configured:
            return format_html(
                '<span style="color: green;">✓ Ativo</span>'
            )
        return format_html(
            '<span style="color: gray;">○ Inativo</span>'
        )
    is_configured_display.short_description = 'Status'
    
    def notification_url_display(self, obj):
        """Mostra URL de notificação formatada"""
        if obj.is_configured:
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                obj.full_url,
                obj.full_url
            )
        return format_html(
            '<span style="color: gray;">(não configurado)</span>'
        )
    notification_url_display.short_description = 'URL de Notificação'
