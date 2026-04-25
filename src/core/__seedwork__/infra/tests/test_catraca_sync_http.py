import pytest
import requests


@pytest.mark.integration
def test_catraca_sync_error_carries_status_code():
    # Testa a excecao de dominio usada para rollback/control flow.
    from rest_framework import status
    from src.core.__seedwork__.infra.catraca_sync import CatracaSyncError

    exc = CatracaSyncError("falhou", status_code=status.HTTP_400_BAD_REQUEST)

    assert str(exc) == "falhou"
    assert exc.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.integration
@pytest.mark.django_db
def test_device_property_supports_default_config_and_requires_device(settings):
    # Testa uso explicito de settings e erro quando nenhum device foi definido.
    from src.core.__seedwork__.infra.catraca_sync import (
        CatracaSyncError,
        ControlIDSyncMixin,
        DefaultDeviceClass,
    )

    mixin = ControlIDSyncMixin()
    with pytest.raises(CatracaSyncError, match="Device"):
        _ = mixin.device

    settings.CATRAKA_URL = "http://catraca.local"
    settings.CATRAKA_USER = "root"
    settings.CATRAKA_PASS = "secret"
    mixin._use_default_config = True

    assert mixin.device == DefaultDeviceClass(
        ip="http://catraca.local", username="root", password="secret"
    )


@pytest.mark.integration
@pytest.mark.django_db
def test_get_url_adds_http_only_when_missing(device_factory):
    # Testa montagem de URL para IP cru e URL ja normalizada.
    from src.core.__seedwork__.infra.catraca_sync import ControlIDSyncMixin

    mixin = ControlIDSyncMixin()
    device = device_factory(ip="192.0.2.110")
    mixin.set_device(device)
    assert mixin.get_url("login.fcgi") == "http://192.0.2.110/login.fcgi"

    device.ip = "https://catraca.example.test"
    assert mixin.get_url("login.fcgi") == "https://catraca.example.test/login.fcgi"


@pytest.mark.integration
@pytest.mark.django_db
def test_login_uses_cached_session_and_resets_on_failure(
    mocker, make_response, device_factory
):
    # Testa cache de sessao, force_new e conversao de erro de rede em CatracaSyncError.
    from src.core.__seedwork__.infra.catraca_sync import CatracaSyncError, ControlIDSyncMixin

    mixin = ControlIDSyncMixin()
    mixin.set_device(device_factory(ip="192.0.2.111"))
    post = mocker.patch(
        "src.core.__seedwork__.infra.catraca_sync.requests.post",
        return_value=make_response(json_data={"session": "sess-1"}),
    )

    assert mixin.login() == "sess-1"
    assert mixin.login() == "sess-1"
    assert post.call_count == 1

    post.return_value = make_response(json_data={"session": "sess-2"})
    assert mixin.login(force_new=True) == "sess-2"

    post.side_effect = requests.RequestException("offline")
    with pytest.raises(CatracaSyncError) as exc:
        mixin.login(force_new=True)

    assert exc.value.status_code == 502
    assert mixin.session is None


@pytest.mark.integration
@pytest.mark.django_db
def test_make_request_retries_once_when_session_expires(
    mocker, make_response, device_factory
):
    # Testa retry automatico com novo login quando a catraca retorna 401.
    from src.core.__seedwork__.infra.catraca_sync import ControlIDSyncMixin

    mixin = ControlIDSyncMixin()
    mixin.set_device(device_factory(ip="192.0.2.112"))
    mocker.patch.object(mixin, "login", side_effect=["old", "new"])
    request = mocker.patch(
        "src.core.__seedwork__.infra.catraca_sync.requests.request",
        side_effect=[
            make_response(status_code=401, json_data={"error": "expired"}),
            make_response(status_code=200, json_data={"ok": True}),
        ],
    )

    response = mixin._make_request("load_objects.fcgi", json_data={"object": "users"})

    assert response.status_code == 200
    assert request.call_count == 2
    assert request.call_args_list[0].kwargs["url"].endswith("session=old")
    assert request.call_args_list[1].kwargs["url"].endswith("session=new")


@pytest.mark.integration
@pytest.mark.django_db
def test_make_request_wraps_transport_errors(mocker, device_factory):
    # Testa timeout/conexao recusada no request principal.
    from src.core.__seedwork__.infra.catraca_sync import CatracaSyncError, ControlIDSyncMixin

    mixin = ControlIDSyncMixin()
    mixin.set_device(device_factory())
    mocker.patch.object(mixin, "login", return_value="sess")
    mocker.patch(
        "src.core.__seedwork__.infra.catraca_sync.requests.request",
        side_effect=requests.RequestException("boom"),
    )

    with pytest.raises(CatracaSyncError) as exc:
        mixin._make_request("load_objects.fcgi")

    assert exc.value.status_code == 502
    assert "load_objects.fcgi" in str(exc.value)


@pytest.mark.integration
def test_extract_response_data_handles_empty_json_and_text(make_response):
    # Testa parsing defensivo das respostas de firmware.
    from src.core.__seedwork__.infra.catraca_sync import ControlIDSyncMixin

    empty = make_response(json_data={})
    empty.text = ""
    assert ControlIDSyncMixin._extract_response_data(empty) is None

    parsed = make_response(json_data={"ok": True}, text='{"ok": true}')
    assert ControlIDSyncMixin._extract_response_data(parsed) == {"ok": True}

    raw = make_response(text="not-json")
    raw.json.side_effect = ValueError("invalid")
    assert ControlIDSyncMixin._extract_response_data(raw) == "not-json"


@pytest.mark.integration
@pytest.mark.django_db
def test_execute_remote_endpoint_delegates_to_make_request(mocker):
    # Testa wrapper simples usado por views de acoes remotas.
    from src.core.__seedwork__.infra.catraca_sync import ControlIDSyncMixin

    mixin = ControlIDSyncMixin()
    mocked = mocker.patch.object(mixin, "_make_request", return_value="ok")

    assert mixin.execute_remote_endpoint("door.fcgi", {"a": 1}, method="GET") == "ok"
    mocked.assert_called_once_with(
        endpoint="door.fcgi",
        method="GET",
        json_data={"a": 1},
        request_timeout=10,
    )
