from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from django.db import transaction

from src.core.control_id.infra.control_id_django_app.models.cards import Card
from src.core.control_id.infra.control_id_django_app.services import (
    CardDeviceSyncService,
)
from src.core.user.infra.user_django_app.models import User, Visitas
from src.core.user.infra.user_django_app.services import (
    UserDeviceSyncService,
    VisitorService,
)
from src.core.user.infra.user_django_app.use_cases.shared import normalize_user_type


@dataclass(frozen=True)
class CreateVisitorWithCardResult:
    user: User
    card: Card
    visit: Visitas
    reused_existing_user: bool


class CreateVisitorWithCardUseCase:
    def __init__(
        self,
        visitor_service: VisitorService | None = None,
        user_sync_service: UserDeviceSyncService | None = None,
        card_sync_service: CardDeviceSyncService | None = None,
    ) -> None:
        self.visitor_service = visitor_service or VisitorService()
        self.user_sync_service = user_sync_service or UserDeviceSyncService()
        self.card_sync_service = card_sync_service or CardDeviceSyncService()

    def execute(
        self,
        serializer,
        actor: User,
        *,
        raw_data: dict[str, Any],
        serializer_factory: Callable[..., Any],
        captured_value: int,
    ) -> CreateVisitorWithCardResult:
        with transaction.atomic():
            reused_existing = False
            created_new_user = False

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

            normalize_user_type(user)

            card = Card.objects.create(user=user, value=str(captured_value))

            if not user.panel_access_only:
                for device in self.user_sync_service.get_active_target_devices(user):
                    if created_new_user:
                        self.user_sync_service.create_user_in_device(device, user)
                    else:
                        self.user_sync_service.upsert_user_in_device(device, user)
                    self.card_sync_service.create_card_in_device(device, card)

            visit = self.visitor_service.create_visit_record(user, actor, card=card)
            return CreateVisitorWithCardResult(
                user=user,
                card=card,
                visit=visit,
                reused_existing_user=reused_existing,
            )
