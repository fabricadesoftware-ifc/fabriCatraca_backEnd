from django.contrib import admin
from src.core.control_Id.infra.control_id_django_app.models import Template, TimeZone, TimeSpan, AccessRule, UserAccessRule, AccessRuleTimeZone, PortalAccessRule, Card

admin.site.register(Template)
admin.site.register(TimeZone)
admin.site.register(TimeSpan)
admin.site.register(AccessRule)
admin.site.register(UserAccessRule)
admin.site.register(AccessRuleTimeZone)
admin.site.register(PortalAccessRule)
admin.site.register(Card)
# Register your models here.
