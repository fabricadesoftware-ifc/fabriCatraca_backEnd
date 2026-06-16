from __future__ import annotations

import pytest
from rest_framework import status
from rest_framework.response import Response

from src.core.control_id.infra.control_id_django_app.services import (
    CardDeviceSyncError,
    CardDeviceSyncService,
    CardEnrollmentError,
    CardEnrollmentService,
)


@pytest.mark.unit
@pytest.mark.django_db
def test_card_enrollment_service_returns_captured_value(mocker, device_factory):
    device = device_factory()
    gateway = mocker.Mock()
    gateway.remote_enroll.return_value = Response(
        {"card_value": 123456},
        status=status.HTTP_201_CREATED,
    )
    service = CardEnrollmentService(gateway=gateway)

    captured_value = service.capture_card(device, user_id=0)

    assert captured_value == 123456
    gateway.set_device.assert_called_once_with(device)
    gateway.remote_enroll.assert_called_once_with(
        user_id=0,
        enrollment_type="card",
        save=False,
        sync=True,
    )


@pytest.mark.unit
@pytest.mark.django_db
def test_card_enrollment_service_raises_when_card_value_is_missing(
    mocker,
    device_factory,
):
    device = device_factory()
    gateway = mocker.Mock()
    gateway.remote_enroll.return_value = Response({}, status=status.HTTP_201_CREATED)
    service = CardEnrollmentService(gateway=gateway)

    with pytest.raises(CardEnrollmentError) as exc_info:
        service.capture_card(device)

    assert exc_info.value.code == "card_value_missing"
    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.unit
@pytest.mark.django_db
def test_card_device_sync_service_creates_card_in_device(
    mocker,
    user_factory,
    device_factory,
):
    user = user_factory()
    device = device_factory()
    card = user.cards.create(value="123456")
    gateway = mocker.Mock()
    gateway.create_objects.return_value = Response(
        {"success": True},
        status=status.HTTP_201_CREATED,
    )
    service = CardDeviceSyncService(gateway=gateway)

    service.create_card_in_device(device, card)

    gateway.set_device.assert_called_once_with(device)
    gateway.create_objects.assert_called_once_with(
        "cards",
        [{"id": card.id, "user_id": user.id, "value": 123456}],
        device_ids=[device.id],
    )


@pytest.mark.unit
@pytest.mark.django_db
def test_card_device_sync_service_raises_on_device_error(
    mocker,
    user_factory,
    device_factory,
):
    user = user_factory()
    device = device_factory()
    card = user.cards.create(value="123456")
    gateway = mocker.Mock()
    gateway.create_objects.return_value = Response(
        {"error": "falhou"},
        status=status.HTTP_400_BAD_REQUEST,
    )
    service = CardDeviceSyncService(gateway=gateway)

    with pytest.raises(CardDeviceSyncError):
        service.create_card_in_device(device, card)
