from rest_framework.permissions import BasePermission

from .models import User


class AppRolePermission(BasePermission):
    allowed_roles: tuple[str, ...] = tuple()

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "is_superuser", False):
            return True
        return getattr(user, "effective_app_role", User.AppRole.NONE) in self.allowed_roles


class IsAdminRole(AppRolePermission):
    allowed_roles = (User.AppRole.ADMIN,)


class IsAdminOrGuaritaRole(AppRolePermission):
    allowed_roles = (User.AppRole.ADMIN, User.AppRole.GUARITA)


class IsAdminOrSisaeRole(AppRolePermission):
    allowed_roles = (User.AppRole.ADMIN, User.AppRole.SISAE)


class IsOperationalRole(AppRolePermission):
    allowed_roles = (
        User.AppRole.ADMIN,
        User.AppRole.GUARITA,
        User.AppRole.SISAE,
    )
