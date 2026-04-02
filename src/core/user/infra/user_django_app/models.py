import random

from django.contrib.auth.models import AbstractUser
from django.db import models
from safedelete.config import SOFT_DELETE_CASCADE
from safedelete.models import SafeDeleteModel

from src.core.uploader.models import Archive

from .managers import CustomUserManager


def generate_pin():
    return str(random.randint(0, 9999)).zfill(4)


class User(SafeDeleteModel, AbstractUser):  # type: ignore
    _safedelete_policy = SOFT_DELETE_CASCADE

    class UserType(models.IntegerChoices):
        VISITOR = 1

    class AppRole(models.TextChoices):
        NONE = "", "Sem perfil"
        ADMIN = "admin", "Administrador"
        GUARITA = "guarita", "Guarita"
        SISAE = "sisae", "SISAE"

    class DeviceScope(models.TextChoices):
        ALL_ACTIVE = "all_active", "Todas as catracas ativas"
        SELECTED = "selected", "Catracas selecionadas"
        NONE = "none", "Nao sincronizar com catracas"

    username = None
    name = models.CharField(max_length=255)
    registration = models.CharField(max_length=50, blank=True, null=True, unique=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    password = models.CharField(max_length=255, null=True, blank=True)
    app_role = models.CharField(
        max_length=20,
        choices=AppRole.choices,
        blank=True,
        default=AppRole.NONE,
        help_text="Perfil de aplicacao para acesso ao painel.",
    )
    panel_access_only = models.BooleanField(
        default=False,
        help_text="Quando ativo, a conta e apenas do painel e nao deve ser sincronizada com as catracas.",
    )
    device_scope = models.CharField(
        max_length=20,
        choices=DeviceScope.choices,
        default=DeviceScope.ALL_ACTIVE,
        help_text="Define em quais catracas o usuario deve existir.",
    )
    selected_devices = models.ManyToManyField(
        "control_id_django_app.Device",
        blank=True,
        related_name="scoped_users",
        help_text="Catracas escolhidas quando o escopo for selecionado.",
    )
    user_type_id = models.IntegerField(
        choices=UserType.choices,
        null=True,
        blank=True,
        help_text="Visitantes terao id 1, usuarios cadastrados serao nulo",
    )
    pin = models.CharField(
        max_length=4,
        default=generate_pin,
        help_text="PIN de 4 digitos para acesso na catraca (campo password na API Control iD).",
    )
    cpf = models.CharField(max_length=14, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    picture = models.ForeignKey(Archive, on_delete=models.SET_NULL, null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    phone_landline = models.CharField(max_length=20, blank=True, null=True)
    phone_responsible = models.CharField(max_length=20, blank=True, null=True)
    responsible_name = models.CharField(max_length=255, blank=True, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]
    EMAIL_FIELD = "email"

    objects = CustomUserManager()

    @property
    def effective_app_role(self):
        if self.app_role:
            return self.app_role
        if self.is_superuser or self.is_staff:
            return self.AppRole.ADMIN
        return self.AppRole.NONE

    @property
    def is_admin_role(self):
        return self.effective_app_role == self.AppRole.ADMIN

    @property
    def is_guarita_role(self):
        return self.effective_app_role == self.AppRole.GUARITA

    @property
    def is_sisae_role(self):
        return self.effective_app_role == self.AppRole.SISAE

    def get_target_devices(self, include_inactive: bool = False):
        from src.core.control_Id.infra.control_id_django_app.models import Device

        if self.panel_access_only or self.device_scope == self.DeviceScope.NONE:
            return Device.objects.none()

        queryset = (
            self.selected_devices.all()
            if self.device_scope == self.DeviceScope.SELECTED
            else Device.objects.all()
        )

        if not include_inactive:
            queryset = queryset.filter(is_active=True)

        return queryset.order_by("id")

    def __str__(self):
        return f"{self.pk} - {self.name}"

    class Meta(SafeDeleteModel.Meta, AbstractUser.Meta):
        verbose_name = "User"
        verbose_name_plural = "Users"
