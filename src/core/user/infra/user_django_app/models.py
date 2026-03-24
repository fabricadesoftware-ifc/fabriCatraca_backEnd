import random

from django.db import models
from django.contrib.auth.models import AbstractUser
from .managers import CustomUserManager


def generate_pin():
    """Gera um PIN aleatório de 4 dígitos (0000-9999)."""
    return str(random.randint(0, 9999)).zfill(4)


class User(AbstractUser):
    class UserType(models.IntegerChoices):
        VISITOR = 1  # Tem id

    class AppRole(models.TextChoices):
        NONE = "", "Sem perfil"
        ADMIN = "admin", "Administrador"
        GUARITA = "guarita", "Guarita"
        SISAE = "sisae", "SISAE"

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
        help_text="Perfil de aplicação para acesso ao painel.",
    )
    panel_access_only = models.BooleanField(
        default=False,
        help_text="Quando ativo, a conta é apenas do painel e não deve ser sincronizada com as catracas.",
    )
    user_type_id = models.IntegerField(
        choices=UserType.choices,
        null=True,
        blank=True,
        help_text="Visitantes terão id 1, usuarios cadastrados serão nulo",
    )
    pin = models.CharField(
        max_length=4,
        default=generate_pin,
        help_text="PIN de 4 dígitos para acesso na catraca (campo 'password' na API Control iD)",
    )

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

    def __str__(self):
        return f"{self.pk} - {self.name}"

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
