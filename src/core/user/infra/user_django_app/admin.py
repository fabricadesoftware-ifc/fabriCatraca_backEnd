from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django import forms
from src.core.user.infra.user_django_app.models import User


class UserAdminForm(forms.ModelForm):
    """Formulário para administrar usuários com suporte a trocar senha."""

    new_password = forms.CharField(
        label=_("Nova senha"),
        required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "off"}),
        help_text=_(
            "Deixe em branco para manter a senha atual. Digite uma nova senha para alterá-la."
        ),
    )

    class Meta:
        model = User
        fields = [
            "name",
            "email",
            "registration",
            "user_type_id",
            "app_role",
            "panel_access_only",
            "pin",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
            "last_login",
            "date_joined",
        ]

    def clean_new_password(self):
        """Valida o campo de senha."""
        password = self.cleaned_data.get("new_password")
        return password or None

    def save(self, commit=True):
        """Salva o usuário e altera a senha se fornecida."""
        user = super().save(commit=False)
        password = self.cleaned_data.get("new_password")
        if password:  # Só altera se senha foi preenchida
            user.set_password(password)
        if commit:
            user.save()
            # Salva as relações Many-to-Many (groups, permissions)
            self.save_m2m()
        return user


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    form = UserAdminForm
    list_display = (
        "id",
        "name",
        "email",
        "app_role",
        "panel_access_only",
        "registration",
        "user_type_id",
        "is_active",
        "is_staff",
    )
    list_display_links = ("id", "name")
    search_fields = ("name", "email", "registration")
    list_filter = (
        "is_active",
        "is_staff",
        "user_type_id",
        "app_role",
        "panel_access_only",
    )
    ordering = ("id",)
    readonly_fields = ("last_login", "date_joined")
    save_on_top = True

    fieldsets = (
        (
            _("Identificação"),
            {
                "classes": ("module",),
                "fields": ("name", "email", "registration"),
            },
        ),
        (
            _("Acesso"),
            {
                "classes": ("module",),
                "fields": ("user_type_id", "app_role", "panel_access_only", "pin"),
            },
        ),
        (
            _("Senha"),
            {
                "classes": ("wide",),
                "fields": ("new_password",),
            },
        ),
        (
            _("Permissões"),
            {
                "classes": (
                    "collapse",
                    "module",
                ),
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            _("Metadados"),
            {
                "classes": ("collapse", "module"),
                "fields": ("last_login", "date_joined"),
            },
        ),
    )

    filter_horizontal = ("groups", "user_permissions")

    class Media:
        css = {
            "all": ("admin/custom.css",),
        }
        js = ("admin/custom.js",)
