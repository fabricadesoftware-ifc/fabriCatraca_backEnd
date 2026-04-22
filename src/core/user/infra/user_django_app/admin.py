from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django import forms
from django.utils import timezone
from datetime import timezone as dt_timezone
from src.core.user.infra.user_django_app.models import User, Visitas


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
            "picture",
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
    readonly_fields = (
        "last_login_utc",
        "date_joined_utc",
        "last_passage_at_utc",
    )
    save_on_top = True

    @admin.display(description=_("Last login (UTC)"))
    def last_login_utc(self, obj):
        return self._format_datetime_utc(getattr(obj, "last_login", None))

    @admin.display(description=_("Date joined (UTC)"))
    def date_joined_utc(self, obj):
        return self._format_datetime_utc(getattr(obj, "date_joined", None))

    @admin.display(description=_("Last passage at (UTC)"))
    def last_passage_at_utc(self, obj):
        return self._format_datetime_utc(getattr(obj, "last_passage_at", None))

    def _format_datetime_utc(self, value):
        if not value:
            return "—"
        return timezone.localtime(value, dt_timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")

    fieldsets = (
        (
            _("Identificação"),
            {
                "classes": ("module",),
                "fields": ("name", "email", "registration"),
            },
        ),
        (
            _("Perfil"),
            {
                "classes": ("module",),
                "fields": ("picture", "cpf", "phone", "birth_date", "start_date", "end_date"),
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
                "fields": ("last_login_utc", "date_joined_utc", "last_passage_at_utc"),
            },
        ),
    )

    filter_horizontal = ("groups", "user_permissions")

    class Media:
        css = {
            "all": ("admin/custom.css",),
        }
        js = ("admin/custom.js",)

@admin.register(Visitas)
class VisitasAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "visit_date")
    search_fields = ("user__name", "user__email", "user__cpf")
    list_filter = ("visit_date",)
    ordering = ("-visit_date",)
