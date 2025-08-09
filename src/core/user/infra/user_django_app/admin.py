from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from src.core.user.infra.user_django_app.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "registration", "user_type_id", "is_active", "is_staff")
    list_display_links = ("id", "name")
    search_fields = ("name", "email", "registration")
    list_filter = ("is_active", "is_staff", "user_type_id")
    ordering = ("id",)
    readonly_fields = ("last_login", "date_joined")
    save_on_top = True

    fieldsets = (
        (_("Identificação"), {
            "classes": ("module",),
            "fields": ("name", "email", "registration"),
        }),
        (_("Acesso"), {
            "classes": ("module",),
            "fields": ("user_type_id",),
        }),
        (_("Permissões"), {
            "classes": ("collapse", "module"),
            "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
        }),
        (_("Metadados"), {
            "classes": ("collapse", "module"),
            "fields": ("last_login", "date_joined"),
        }),
    )

    filter_horizontal = ("groups", "user_permissions")

    class Media:
        css = {
            "all": ("admin/custom.css",),
        }
        js = ("admin/custom.js",)
