from __future__ import annotations

from django.utils import timezone

from src.core.user.infra.user_django_app.models import User


class UserControlIDMapper:
    @staticmethod
    def datetime_to_device_timestamp(value) -> int:
        if not value:
            return 0

        aware_value = value
        if timezone.is_naive(aware_value):
            aware_value = timezone.make_aware(
                aware_value,
                timezone.get_current_timezone(),
            )
        return int(aware_value.timestamp())

    @classmethod
    def to_user_payload(cls, user: User) -> dict[str, int | str]:
        return {
            "id": user.id,
            "name": user.name,
            "registration": user.registration or "",
            "begin_time": cls.datetime_to_device_timestamp(user.start_date),
            "end_time": cls.datetime_to_device_timestamp(user.end_date),
        }
