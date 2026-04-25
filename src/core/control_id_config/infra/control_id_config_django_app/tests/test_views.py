from time import perf_counter

import pytest
from rest_framework import status
from rest_framework.response import Response


def _results(response):
    return response.data["results"] if isinstance(response.data, dict) else response.data


def _patch_config_sync(mocker, view_path, sync_payload=None):
    sync_payload = sync_payload or {"success": True, "config_id": 1}
    mocker.patch(
        f"{view_path}.update_catra_config_in_catraca",
        return_value=Response({"success": True}, status=status.HTTP_200_OK),
        create=True,
    )
    mocker.patch(
        f"{view_path}.update_push_server_config_in_catraca",
        return_value=Response({"success": True}, status=status.HTTP_200_OK),
        create=True,
    )
    mocker.patch(
        f"{view_path}.update_system_config_in_catraca",
        return_value=Response({"success": True}, status=status.HTTP_200_OK),
        create=True,
    )
    mocker.patch(
        f"{view_path}.sync_catra_config_from_catraca",
        return_value=Response(sync_payload, status=status.HTTP_200_OK),
        create=True,
    )
    mocker.patch(
        f"{view_path}.sync_push_server_config_from_catraca",
        return_value=Response(sync_payload, status=status.HTTP_200_OK),
        create=True,
    )
    mocker.patch(
        f"{view_path}.sync_system_config_from_catraca",
        return_value=Response(sync_payload, status=status.HTTP_200_OK),
        create=True,
    )


@pytest.mark.integration
@pytest.mark.django_db
def test_catra_config_list_requires_authentication(
    anonymous_client, api_client_operator, catra_config_factory
):
    # Testa que anonimo nao lista configs, mas operador autenticado pode consultar.
    catra_config_factory()

    anonymous = anonymous_client.get("/api/control_id_config/catra-configs/")
    operator = api_client_operator.get("/api/control_id_config/catra-configs/")

    assert anonymous.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    assert operator.status_code == status.HTTP_200_OK
    assert len(_results(operator)) == 1


@pytest.mark.integration
@pytest.mark.django_db
def test_catra_config_crud_and_filters(api_client_admin, mocker, device_factory, catra_config_factory):
    # Testa CRUD completo de CatraConfig com sync externo mockado.
    from src.core.control_id_config.infra.control_id_config_django_app.models import (
        CatraConfig,
    )

    _patch_config_sync(
        mocker,
        "src.core.control_id_config.infra.control_id_config_django_app.views.catra_config.CatraConfigViewSet",
    )
    device = device_factory()
    existing = catra_config_factory(gateway="anticlockwise")

    list_response = api_client_admin.get("/api/control_id_config/catra-configs/")
    assert list_response.status_code == status.HTTP_200_OK
    assert list_response["Content-Type"].startswith("application/json")

    filtered = api_client_admin.get("/api/control_id_config/catra-configs/?gateway=anticlockwise")
    assert filtered.status_code == status.HTTP_200_OK
    assert all(item["gateway"] == "anticlockwise" for item in _results(filtered))

    retrieve = api_client_admin.get(f"/api/control_id_config/catra-configs/{existing.id}/")
    assert retrieve.status_code == status.HTTP_200_OK
    assert retrieve.data["gateway_display"]

    create = api_client_admin.post(
        "/api/control_id_config/catra-configs/",
        {
            "device": device.id,
            "anti_passback": True,
            "daily_reset": False,
            "gateway": "clockwise",
            "operation_mode": "entrance_open",
        },
        format="json",
    )
    assert create.status_code == status.HTTP_201_CREATED
    created = CatraConfig.objects.get(device=device)
    assert created.anti_passback is True

    patch = api_client_admin.patch(
        f"/api/control_id_config/catra-configs/{created.id}/",
        {"operation_mode": "both_open"},
        format="json",
    )
    assert patch.status_code == status.HTTP_200_OK
    created.refresh_from_db()
    assert created.operation_mode == "both_open"

    delete = api_client_admin.delete(f"/api/control_id_config/catra-configs/{created.id}/")
    assert delete.status_code == status.HTTP_204_NO_CONTENT
    assert not CatraConfig.objects.filter(id=created.id).exists()


@pytest.mark.integration
@pytest.mark.django_db
def test_catra_config_rejects_bad_payload(api_client_admin, device_factory):
    # Testa validacao de choice invalida.
    device = device_factory()

    response = api_client_admin.post(
        "/api/control_id_config/catra-configs/",
        {"device": device.id, "gateway": "invalid", "operation_mode": "blocked"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "gateway" in response.data


@pytest.mark.integration
@pytest.mark.django_db
def test_push_server_config_validations_and_crud(api_client_admin, mocker, device_factory):
    # Testa validacoes de ranges, formato de endereco e persistencia.
    from src.core.control_id_config.infra.control_id_config_django_app.models import (
        PushServerConfig,
    )

    _patch_config_sync(
        mocker,
        "src.core.control_id_config.infra.control_id_config_django_app.views.push_server_config.PushServerConfigViewSet",
    )
    device = device_factory()

    invalid_timeout = api_client_admin.post(
        "/api/control_id_config/push-server-configs/",
        {
            "device": device.id,
            "push_request_timeout": 300001,
            "push_request_period": 60,
        },
        format="json",
    )
    assert invalid_timeout.status_code == status.HTTP_400_BAD_REQUEST
    assert "push_request_timeout" in invalid_timeout.data

    invalid_period = api_client_admin.post(
        "/api/control_id_config/push-server-configs/",
        {
            "device": device.id,
            "push_request_timeout": 15000,
            "push_request_period": 86401,
        },
        format="json",
    )
    assert invalid_period.status_code == status.HTTP_400_BAD_REQUEST
    assert "push_request_period" in invalid_period.data

    invalid_address = api_client_admin.post(
        "/api/control_id_config/push-server-configs/",
        {
            "device": device.id,
            "push_request_timeout": 15000,
            "push_request_period": 60,
            "push_remote_address": "sem-porta",
        },
        format="json",
    )
    assert invalid_address.status_code == status.HTTP_400_BAD_REQUEST
    assert "push_remote_address" in invalid_address.data

    create = api_client_admin.post(
        "/api/control_id_config/push-server-configs/",
        {
            "device": device.id,
            "push_request_timeout": 20000,
            "push_request_period": 120,
            "push_remote_address": "",
        },
        format="json",
    )
    assert create.status_code == status.HTTP_201_CREATED
    saved = PushServerConfig.objects.get(device=device)
    assert saved.push_remote_address == ""

    update = api_client_admin.patch(
        f"/api/control_id_config/push-server-configs/{saved.id}/",
        {"push_remote_address": "192.0.2.60:8080"},
        format="json",
    )
    assert update.status_code == status.HTTP_200_OK
    saved.refresh_from_db()
    assert saved.push_remote_address == "192.0.2.60:8080"


@pytest.mark.integration
@pytest.mark.django_db
def test_system_config_list_filter_and_performance(
    api_client_admin, system_config_factory, device_factory
):
    # Testa filtro por device e tempo minimo esperado para endpoint critico.
    device_1 = device_factory(name="Catraca Rapida")
    device_2 = device_factory(name="Catraca Lenta")
    system_config_factory(device=device_1, online=True)
    system_config_factory(device=device_2, online=False)

    url = f"/api/control_id_config/system-configs/?device={device_1.id}"
    warmup = api_client_admin.get(url)
    assert warmup.status_code == status.HTTP_200_OK

    started = perf_counter()
    response = api_client_admin.get(url)
    elapsed_ms = (perf_counter() - started) * 1000

    assert response.status_code == status.HTTP_200_OK
    assert elapsed_ms < 800
    data = _results(response)
    assert len(data) == 1
    assert data[0]["device"] == device_1.id


@pytest.mark.integration
@pytest.mark.django_db
def test_system_config_create_rolls_back_when_remote_update_fails(
    api_client_admin, mocker, device_factory
):
    # Testa rollback local quando a catraca recusa configuracao recem criada.
    from src.core.control_id_config.infra.control_id_config_django_app.models import (
        SystemConfig,
    )

    mocker.patch(
        "src.core.control_id_config.infra.control_id_config_django_app.views.system_config.SystemConfigViewSet.update_system_config_in_catraca",
        return_value=Response({"success": False}, status=status.HTTP_502_BAD_GATEWAY),
    )
    device = device_factory()

    response = api_client_admin.post(
        "/api/control_id_config/system-configs/",
        {
            "device": device.id,
            "auto_reboot_hour": 5,
            "auto_reboot_minute": 30,
            "online": True,
            "language": "pt_BR",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert not SystemConfig.objects.filter(device=device).exists()
