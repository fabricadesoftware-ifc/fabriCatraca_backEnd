from __future__ import annotations

from src.core.user.infra.user_django_app.models import User


def normalize_user_type(user: User) -> None:
    if user.user_type_id in (0, "0"):
        user.user_type_id = None
        user.save(update_fields=["user_type_id"])
