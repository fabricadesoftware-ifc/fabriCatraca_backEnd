from typing import Any, Mapping

from django.contrib.auth.base_user import BaseUserManager
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from safedelete.config import FIELD_NAME
from safedelete.managers import SafeDeleteManager


class CustomUserManager(SafeDeleteManager, BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """

    def create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given email and password.
        """
        if not email:
            raise ValueError(_("The Email must be set"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        return self.create_user(email, password, **extra_fields)

    def update_or_create(
        self,
        defaults: Mapping[str, Any] | None = None,
        create_defaults: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ):
        """
        Compatibilidade com a assinatura moderna do Django Manager.update_or_create.

        Quando create_defaults nao for informado, delega ao comportamento do
        SafeDeleteManager. Quando informado, aplica defaults em updates e
        create_defaults na criacao/reativacao do objeto.
        """
        if create_defaults is None:
            return SafeDeleteManager.update_or_create(self, defaults=defaults, **kwargs)

        defaults = dict(defaults or {})
        create_defaults = dict(create_defaults)

        with transaction.atomic():
            obj = self.filter(**kwargs).first()
            if obj is not None:
                for key, value in defaults.items():
                    setattr(obj, key, value)
                if defaults:
                    obj.save(update_fields=list(defaults.keys()))
                else:
                    obj.save()
                return obj, False

            deleted_obj = self.all_with_deleted().filter(**kwargs).exclude(**{FIELD_NAME: None}).first()
            if deleted_obj is not None:
                for key, value in create_defaults.items():
                    setattr(deleted_obj, key, value)
                deleted_obj.save()
                return deleted_obj, True

            params = {**kwargs, **create_defaults}
            return self.create(**params), True
