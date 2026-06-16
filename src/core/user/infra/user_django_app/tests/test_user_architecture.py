from __future__ import annotations

import pytest
from rest_framework import status
from rest_framework.response import Response

from src.core.user.infra.user_django_app.services import (
    UserDeviceSyncService,
    UserDeviceSyncSnapshot,
)


@pytest.mark.integration
@pytest.mark.django_db
def test_legacy_user_sync_endpoint_is_disabled(api_client_admin):
    response = api_client_admin.get("/api/users/users/sync/")

    assert response.status_code == status.HTTP_410_GONE
    assert response.data == {
        "error": "Sincronizacao de usuarios desativada.",
        "code": "legacy_user_sync_disabled",
        "details": "Esta funcao nao esta disponivel no momento.",
    }


@pytest.mark.integration
@pytest.mark.django_db
def test_operator_cannot_create_non_visitor_user(api_client_operator):
    response = api_client_operator.post(
        "/api/users/users/",
        {
            "name": "Aluno Protegido",
            "registration": "ALUNO-001",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data == {
        "error": "Apenas administradores podem criar usuarios nao-visitantes.",
        "code": "user_modification_forbidden",
    }


@pytest.mark.integration
@pytest.mark.django_db
def test_enroll_card_requires_enrollment_device(api_client_admin):
    response = api_client_admin.post(
        "/api/users/users/enroll_card/",
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {
        "error": "E necessario especificar uma catraca para captura do cartao",
        "code": "card_enrollment_device_required",
    }


@pytest.mark.integration
@pytest.mark.django_db
def test_enroll_card_returns_captured_value(
    mocker,
    api_client_admin,
    device_factory,
):
    device = device_factory(name="Catraca Cadastro")
    mocker.patch(
        "src.core.user.infra.user_django_app.views.user.CardEnrollmentService.capture_card",
        return_value=987654,
    )

    response = api_client_admin.post(
        "/api/users/users/enroll_card/",
        {"enrollment_device_id": device.id},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {
        "device_id": device.id,
        "device_name": "Catraca Cadastro",
        "card_value": 987654,
    }


@pytest.mark.unit
@pytest.mark.django_db
def test_user_device_sync_service_applies_device_diff(
    mocker,
    user_factory,
    device_factory,
):
    user = user_factory(panel_access_only=False)
    removed_device = device_factory(name="Catraca Removida")
    unchanged_device = device_factory(name="Catraca Mantida")
    added_device = device_factory(name="Catraca Adicionada")
    service = UserDeviceSyncService(gateway=mocker.Mock())

    delete_user = mocker.patch.object(service, "delete_user_from_device")
    create_user = mocker.patch.object(service, "create_user_in_device")
    update_user = mocker.patch.object(service, "update_user_in_device")

    previous = UserDeviceSyncSnapshot(
        panel_access_only=False,
        device_admin=False,
        devices=(removed_device, unchanged_device),
    )
    current = UserDeviceSyncSnapshot(
        panel_access_only=False,
        device_admin=False,
        devices=(unchanged_device, added_device),
    )

    service.apply_update(user, previous, current)

    delete_user.assert_called_once_with(removed_device, user)
    create_user.assert_called_once_with(added_device, user)
    update_user.assert_called_once_with(
        unchanged_device,
        user,
        previous_device_admin=False,
    )


@pytest.mark.unit
@pytest.mark.django_db
def test_user_device_sync_service_targets_single_device_when_creating_user(
    mocker,
    user_factory,
    device_factory,
):
    user = user_factory(name="Aluno Target", registration="TGT001")
    device = device_factory(name="Catraca Target")
    gateway = mocker.Mock()
    gateway.create_objects.return_value = Response(
        {"success": True},
        status=status.HTTP_201_CREATED,
    )
    service = UserDeviceSyncService(gateway=gateway)
    sync_pin = mocker.patch.object(service, "sync_pin")

    service.create_user_in_device(device, user)

    gateway.set_device.assert_called_once_with(device)
    gateway.create_objects.assert_called_once_with(
        "users",
        [
            {
                "id": user.id,
                "name": user.name,
                "registration": user.registration,
                "begin_time": 0,
                "end_time": 0,
            }
        ],
        device_ids=[device.id],
    )
    sync_pin.assert_called_once_with(device, user, allow_create=True)


@pytest.mark.unit
@pytest.mark.django_db
def test_user_device_sync_service_removes_devices_when_panel_only_is_enabled(
    mocker,
    user_factory,
    device_factory,
):
    user = user_factory(panel_access_only=True)
    previous_device = device_factory(name="Catraca Antiga")
    service = UserDeviceSyncService(gateway=mocker.Mock())

    delete_user = mocker.patch.object(service, "delete_user_from_device")
    create_user = mocker.patch.object(service, "create_user_in_device")
    update_user = mocker.patch.object(service, "update_user_in_device")

    previous = UserDeviceSyncSnapshot(
        panel_access_only=False,
        device_admin=False,
        devices=(previous_device,),
    )
    current = UserDeviceSyncSnapshot(
        panel_access_only=True,
        device_admin=False,
        devices=(),
    )

    service.apply_update(user, previous, current)

    delete_user.assert_called_once_with(previous_device, user)
    create_user.assert_not_called()
    update_user.assert_not_called()
