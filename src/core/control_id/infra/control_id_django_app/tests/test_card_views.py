from __future__ import annotations

import pytest
from rest_framework import status

from src.core.control_id.infra.control_id_django_app.models.cards import Card
from src.core.user.infra.user_django_app.models import User


@pytest.mark.integration
@pytest.mark.django_db
def test_card_create_requires_user(api_client_admin, device_factory):
    device = device_factory()

    response = api_client_admin.post(
        "/api/control_id/cards/",
        {"enrollment_device_id": device.id},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {
        "error": "Usuario (user_id) e obrigatorio",
        "code": "card_user_required",
    }


@pytest.mark.integration
@pytest.mark.django_db
def test_card_create_captures_and_saves_card(
    mocker,
    api_client_admin,
    user_factory,
    device_factory,
):
    user = user_factory()
    device = device_factory(name="Catraca Cartao")
    capture_card = mocker.patch(
        "src.core.control_id.infra.control_id_django_app.services.CardEnrollmentService.capture_card",
        return_value=555123,
    )
    sync_cards = mocker.patch(
        "src.core.control_id.infra.control_id_django_app.services.CardDeviceSyncService.create_card_for_user_devices"
    )

    response = api_client_admin.post(
        "/api/control_id/cards/",
        {"user_id": user.id, "enrollment_device_id": device.id},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["value"] == "555123"
    assert response.data["user"]["id"] == user.id
    assert Card.objects.filter(user=user, value="555123").exists()
    capture_card.assert_called_once()
    sync_cards.assert_called_once()


@pytest.mark.integration
@pytest.mark.django_db
def test_card_create_rejects_enrollment_device_outside_user_scope(
    mocker,
    api_client_admin,
    user_factory,
    device_factory,
):
    allowed_device = device_factory(name="Catraca Permitida")
    blocked_device = device_factory(name="Catraca Bloqueada")
    user = user_factory(device_scope=User.DeviceScope.SELECTED)
    user.selected_devices.add(allowed_device)
    capture_card = mocker.patch(
        "src.core.control_id.infra.control_id_django_app.services.CardEnrollmentService.capture_card"
    )

    response = api_client_admin.post(
        "/api/control_id/cards/",
        {"user_id": user.id, "enrollment_device_id": blocked_device.id},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {
        "error": "A catraca escolhida nao faz parte do escopo do usuario.",
        "code": "card_enrollment_device_out_of_scope",
    }
    capture_card.assert_not_called()


@pytest.mark.integration
@pytest.mark.django_db
def test_card_update_uses_sync_service(
    mocker,
    api_client_admin,
    user_factory,
    device_factory,
):
    user = user_factory()
    device_factory()
    card = Card.objects.create(user=user, value="123456")
    sync_cards = mocker.patch(
        "src.core.control_id.infra.control_id_django_app.services.CardDeviceSyncService.update_card_for_user_devices"
    )

    response = api_client_admin.patch(
        f"/api/control_id/cards/{card.id}/",
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == card.id
    sync_cards.assert_called_once()


@pytest.mark.integration
@pytest.mark.django_db
def test_card_delete_uses_sync_service(
    mocker,
    api_client_admin,
    user_factory,
    device_factory,
):
    user = user_factory()
    device_factory()
    card = Card.objects.create(user=user, value="123456")
    sync_cards = mocker.patch(
        "src.core.control_id.infra.control_id_django_app.services.CardDeviceSyncService.delete_card_for_user_devices"
    )

    response = api_client_admin.delete(f"/api/control_id/cards/{card.id}/")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Card.objects.filter(id=card.id).exists()
    sync_cards.assert_called_once()
