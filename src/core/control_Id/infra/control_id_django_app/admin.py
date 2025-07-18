from django.contrib import admin
from src.core.control_Id.infra.control_id_django_app.models import Template, TimeZone, TimeSpan, AccessRule, UserAccessRule, AccessRuleTimeZone, PortalAccessRule, Card
from src.core.control_Id.infra.control_id_django_app.models.device import Device

admin.site.register(Template)
admin.site.register(TimeZone)
admin.site.register(TimeSpan)
admin.site.register(AccessRule)
admin.site.register(UserAccessRule)
admin.site.register(AccessRuleTimeZone)
admin.site.register(PortalAccessRule)
admin.site.register(Card)

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'ip', 'is_active', 'is_default')
    list_filter = ('is_active', 'is_default')
    search_fields = ('name', 'ip')
    ordering = ('name',)
# Register your models here.
