from __future__ import annotations

from src.core.user.infra.user_django_app.models import User


class UserModificationForbidden(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UserModificationPolicy:
    def can_modify_any_user(self, actor: User) -> bool:
        return bool(
            actor.is_superuser
            or actor.effective_app_role == User.AppRole.ADMIN
        )

    def assert_can_create(self, actor: User, validated_data: dict) -> None:
        if self.can_modify_any_user(actor):
            return

        if validated_data.get("user_type_id") == User.UserType.VISITOR:
            return

        raise UserModificationForbidden(
            "Apenas administradores podem criar usuarios nao-visitantes."
        )

    def assert_can_modify(self, actor: User, target: User) -> None:
        if self.can_modify_any_user(actor):
            return

        if target.user_type_id == User.UserType.VISITOR:
            return

        raise UserModificationForbidden(
            "Apenas administradores podem modificar usuarios nao-visitantes."
        )
