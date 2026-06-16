from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from django.db import transaction

from src.core.user.infra.user_django_app.models import User, Visitas
from src.core.user.infra.user_django_app.services import (
    UserDeviceSyncService,
    VisitorService,
)
from src.core.user.infra.user_django_app.use_cases.shared import normalize_user_type


@dataclass(frozen=True)
class CreateUserResult:
    user: User
    visit: Visitas | None = None
    reused_existing_user: bool = False


class CreateUserUseCase:
    def __init__(
        self,
        visitor_service: VisitorService | None = None,
        sync_service: UserDeviceSyncService | None = None,
    ) -> None:
        self.visitor_service = visitor_service or VisitorService()
        self.sync_service = sync_service or UserDeviceSyncService()

    def execute(
        self,
        serializer,
        actor: User,
        *,
        raw_data: dict[str, Any],
        serializer_factory: Callable[..., Any],
    ) -> CreateUserResult:
        with transaction.atomic():
            reused_existing = False
            created_new_user = False

            if self.visitor_service.is_visitor_payload(serializer.validated_data):
                existing_visitor = self.visitor_service.find_existing_visitor(
                    serializer.validated_data
                )
                if existing_visitor:
                    update_serializer = serializer_factory(
                        existing_visitor,
                        data=raw_data,
                        partial=True,
                    )
                    update_serializer.is_valid(raise_exception=True)
                    user = update_serializer.save()
                    reused_existing = True
                else:
                    user = serializer.save()
                    created_new_user = True
            else:
                user = serializer.save()
                created_new_user = True

            normalize_user_type(user)

            try:
                self.sync_service.create_or_upsert_user(
                    user,
                    created_new_user=created_new_user,
                )
            except Exception:
                if created_new_user:
                    user.delete()
                raise

            visit = None
            if self.visitor_service.is_visitor(user):
                visit = self.visitor_service.create_visit_record(user, actor)

            return CreateUserResult(
                user=user,
                visit=visit,
                reused_existing_user=reused_existing,
            )
