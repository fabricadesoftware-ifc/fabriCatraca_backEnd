import random

from django.contrib.auth.models import AbstractUser
from django.db import models
from safedelete.config import SOFT_DELETE_CASCADE
from safedelete.models import SafeDeleteModel

from src.core.uploader.models import Archive

from .managers import CustomUserManager
from src.core.__seedwork__.domain import BaseModel

PIN_LENGTH = 4
PIN_SPACE_SIZE = 10**PIN_LENGTH


def generate_pin():
    return str(random.randint(0, PIN_SPACE_SIZE - 1)).zfill(PIN_LENGTH)


def _is_valid_pin(value: str | None) -> bool:
    return bool(value and len(value) == PIN_LENGTH and value.isdigit())


def generate_unique_pin(
    *,
    exclude_user_id: int | None = None,
    extra_used_pins: set[str] | None = None,
) -> str:
    """
    Gera um PIN de 4 digitos ainda livre entre usuarios ativos.

    Mantemos o espaco em 0000-9999 por compatibilidade com a catraca. Quando
    todos estiverem ocupados, falhamos explicitamente para evitar duplicidade.
    """
    used_pins = set(extra_used_pins or set())
    queryset = User.objects.exclude(pin__isnull=True).exclude(pin="")
    if exclude_user_id is not None:
        queryset = queryset.exclude(pk=exclude_user_id)

    used_pins.update(str(pin).strip() for pin in queryset.values_list("pin", flat=True))
    if len({pin for pin in used_pins if _is_valid_pin(pin)}) >= PIN_SPACE_SIZE:
        raise ValueError("Nao ha PINs de 4 digitos disponiveis.")

    for _ in range(PIN_SPACE_SIZE):
        candidate = generate_pin()
        if candidate not in used_pins:
            return candidate

    for number in range(PIN_SPACE_SIZE):
        candidate = str(number).zfill(PIN_LENGTH)
        if candidate not in used_pins:
            return candidate

    raise ValueError("Nao ha PINs de 4 digitos disponiveis.")


class User(SafeDeleteModel, AbstractUser):  # type: ignore
    _safedelete_policy = SOFT_DELETE_CASCADE

    class UserType(models.IntegerChoices):
        VISITOR = 1

    class AppRole(models.TextChoices):
        NONE = "", "Sem perfil"
        ADMIN = "admin", "Administrador"
        GUARITA = "guarita", "Guarita"
        SISAE = "sisae", "SISAE"
        ALUNO = "aluno", "Aluno"
        SERVIDOR = "servidor", "Servidor"

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
        default=AppRole.ALUNO,
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
    cpf = models.CharField(max_length=14, blank=True, null=True, unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    picture = models.ForeignKey(
        Archive, on_delete=models.SET_NULL, null=True, blank=True
    )
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    phone_landline = models.CharField(max_length=20, blank=True, null=True)
    phone_responsible = models.CharField(max_length=20, blank=True, null=True)
    responsible_name = models.CharField(max_length=255, blank=True, null=True)
    created_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_users",
    )
    start_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Data e hora de inicio de vigencia do acesso.",
    )
    end_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Data e hora de fim de vigencia do acesso.",
    )
    last_passage_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Horario da ultima passagem registrada na catraca.",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]
    EMAIL_FIELD = "email"

    objects = CustomUserManager()

    def save(self, *args, **kwargs):
        normalized_pin = (self.pin or "").strip()
        pin_conflicts = False
        if _is_valid_pin(normalized_pin):
            pin_conflicts = (
                User.objects.filter(pin=normalized_pin)
                .exclude(pk=self.pk)
                .exists()
            )

        if not _is_valid_pin(normalized_pin) or pin_conflicts:
            self.pin = generate_unique_pin(exclude_user_id=self.pk)
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = set(update_fields) | {"pin"}
        else:
            self.pin = normalized_pin

        super().save(*args, **kwargs)

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
        from src.core.control_id.infra.control_id_django_app.models import Device

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
        constraints = [
            models.UniqueConstraint(
                fields=["pin"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_user_pin",
            )
        ]


class Visitas(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="visitas")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_visitas",
    )
    initial_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(blank=True, null=True)
    visit_date = models.DateTimeField()
    card = models.ForeignKey(
        "control_id_django_app.Card",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="visitas",
    )
    finished_at = models.DateTimeField(blank=True, null=True)
    card_removed_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Visita do usuário {self.user.name} em {self.visit_date.strftime('%Y-%m-%d %H:%M:%S')}"

    class Meta(BaseModel.Meta):
        verbose_name = "Visita"
        verbose_name_plural = "Visitas"
        ordering = ["-visit_date"]
