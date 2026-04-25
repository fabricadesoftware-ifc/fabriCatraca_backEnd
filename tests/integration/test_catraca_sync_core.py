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
def test_normalize_config_value_recursively():
    # Testa normalizacao exigida pela API Control iD: folhas como string.
    from src.core.__seedwork__.infra.catraca_sync import _normalize_config_value

    assert _normalize_config_value(
        {"a": True, "b": [False, None, 3], "c": {"d": "ok"}}
    ) == {"a": "1", "b": ["0", "", "3"], "c": {"d": "ok"}}


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


@pytest.mark.integration
@pytest.mark.django_db
def test_execute_remote_endpoint_in_devices_reports_missing_empty_success_and_failure(
    mocker, make_response, device_factory
):
    # Testa agregacao multi-device sem vazar excecoes para a API.
    from src.core.__seedwork__.infra.catraca_sync import CatracaSyncError, ControlIDSyncMixin

    mixin = ControlIDSyncMixin()
    missing = mixin.execute_remote_endpoint_in_devices("x.fcgi", {}, [9999])
    assert missing.status_code == 400
    assert "9999" in missing.data["error"]

    empty = mixin.execute_remote_endpoint_in_devices("x.fcgi", {}, [])
    assert empty.status_code == 400

    device_1 = device_factory(name="Catraca Um")
    device_2 = device_factory(name="Catraca Dois")
    mocked = mocker.patch.object(
        mixin,
        "execute_remote_endpoint",
        side_effect=[
            make_response(status_code=200, json_data={"ok": 1}, text='{"ok": 1}'),
            CatracaSyncError("offline", status_code=502),
        ],
    )

    response = mixin.execute_remote_endpoint_in_devices(
        "status.fcgi", {"ping": True}, [device_1.id, device_2.id]
    )

    assert response.status_code == 502
    assert response.data["processed_devices"] == 2
    assert response.data["successful_devices"] == 1
    assert response.data["failed_devices"] == 1
    assert response.data["results"][0]["response"] == {"ok": 1}
    assert response.data["results"][1]["error"] == "offline"
    assert mocked.call_count == 2


@pytest.mark.integration
@pytest.mark.django_db
def test_get_target_devices_prioritizes_explicit_device_and_active_filters(device_factory):
    # Testa resolucao de alvo: device fixo, ids ativos e todos ativos.
    from src.core.__seedwork__.infra.catraca_sync import ControlIDSyncMixin

    active = device_factory(is_active=True)
    inactive = device_factory(is_active=False)
    mixin = ControlIDSyncMixin()

    assert list(mixin._get_target_devices([active.id, inactive.id])) == [active]
    assert list(mixin._get_target_devices()) == [active]

    mixin.set_device(inactive)
    assert mixin._get_target_devices([active.id]) == [inactive]


@pytest.mark.integration
@pytest.mark.django_db
def test_load_objects_success_and_error(mocker, make_response):
    # Testa load_objects com filtros opcionais e erro remoto.
    from src.core.__seedwork__.infra.catraca_sync import CatracaSyncError, ControlIDSyncMixin

    mixin = ControlIDSyncMixin()
    mocked = mocker.patch.object(
        mixin,
        "_make_request",
        return_value=make_response(json_data={"users": [{"id": 1}]}),
    )

    assert mixin.load_objects("users", fields=["id"], order_by=["id"]) == [{"id": 1}]
    assert mocked.call_args.kwargs["json_data"] == {
        "object": "users",
        "fields": ["id"],
        "order_by": ["id"],
    }

    mocked.return_value = make_response(status_code=500, json_data={"error": "bad"})
    with pytest.raises(CatracaSyncError) as exc:
        mixin.load_objects("users")
    assert exc.value.status_code == 500


@pytest.mark.integration
@pytest.mark.django_db
def test_create_objects_validates_targets_required_fields_and_remote_errors(
    mocker, make_response, device_factory
):
    # Testa criacao multi-device, validacao obrigatoria e falha da catraca.
    from src.core.__seedwork__.infra.catraca_sync import CatracaSyncError, ControlIDSyncMixin
    from src.core.control_Id.infra.control_id_django_app.models import Device

    Device.objects.all().delete()
    mixin = ControlIDSyncMixin()
    no_devices = mixin.create_objects("users", [{"id": 1, "name": "A"}])
    assert no_devices.status_code == 400

    device = device_factory()
    with pytest.raises(CatracaSyncError) as validation:
        mixin.create_objects("users", [{"id": 1, "name": ""}])
    assert validation.value.status_code == 400

    bad_json = make_response(json_data={"ids": [1]})
    bad_json.json.side_effect = RuntimeError("invalid json")
    mocked = mocker.patch.object(mixin, "_make_request", return_value=bad_json)
    success = mixin.create_objects("unknown_object", [{"free": "field"}])
    assert success.status_code == 201
    assert success.data == {"success": True}

    mocked.return_value = make_response(status_code=409, json_data={"error": "duplicate"})
    with pytest.raises(CatracaSyncError) as remote:
        mixin.create_objects("users", [{"id": 2, "name": "B"}], device_ids=[device.id])
    assert remote.value.status_code == 409


@pytest.mark.integration
@pytest.mark.django_db
def test_create_or_update_update_and_destroy_objects_cover_success_and_errors(
    mocker, make_response, device_factory
):
    # Testa create_or_update, update, destroy e aliases em sucesso/falha.
    from src.core.__seedwork__.infra.catraca_sync import CatracaSyncError, ControlIDSyncMixin

    device = device_factory()
    mixin = ControlIDSyncMixin()
    mocked = mocker.patch.object(
        mixin, "_make_request", return_value=make_response(json_data={"ok": True})
    )

    assert mixin.create_or_update_objects("groups", [{"id": 1, "name": "G"}]).status_code == 200
    assert mocked.call_args.args[0] == "create_or_modify_objects.fcgi"

    assert mixin.update_objects("groups", {"name": "G2"}, {"id": 1}).status_code == 200
    assert mocked.call_args.args[0] == "modify_objects.fcgi"

    mocked.return_value = make_response(status_code=204, json_data={})
    assert mixin.destroy_objects("groups", {"id": 1}).status_code == 204
    assert mocked.call_args.args[0] == "destroy_objects.fcgi"

    mocked.return_value = make_response(status_code=500, json_data={"error": "bad"})
    with pytest.raises(CatracaSyncError):
        mixin.create_or_update_objects("groups", [{"id": 2, "name": "G"}], device_ids=[device.id])
    with pytest.raises(CatracaSyncError):
        mixin.update_objects("groups", {"name": "G"}, {"id": 2}, device_ids=[device.id])
    with pytest.raises(CatracaSyncError):
        mixin.destroy_objects("groups", {"id": 2}, device_ids=[device.id])


@pytest.mark.integration
@pytest.mark.django_db
def test_object_mutations_return_400_without_active_devices(mocker):
    # Testa protecao contra mutacao quando nao ha catracas ativas.
    from src.core.__seedwork__.infra.catraca_sync import ControlIDSyncMixin
    from src.core.control_Id.infra.control_id_django_app.models import Device

    Device.objects.all().delete()
    mixin = ControlIDSyncMixin()

    assert mixin.create_or_update_objects("groups", [{"id": 1, "name": "G"}]).status_code == 400
    assert mixin.update_objects("groups", {"name": "G"}, {"id": 1}).status_code == 400
    assert mixin.destroy_objects("groups", {"id": 1}).status_code == 400


@pytest.mark.integration
@pytest.mark.django_db
def test_remote_enroll_maps_non_200_timeout_and_login_errors(
    mocker, make_response, device_factory
):
    # Testa respostas de erro do cadastro remoto interativo.
    from src.core.__seedwork__.infra.catraca_sync import CatracaSyncError, ControlIDSyncMixin

    mixin = ControlIDSyncMixin()
    mixin.set_device(device_factory())
    mocker.patch.object(mixin, "login", return_value="sess")
    post = mocker.patch(
        "src.core.__seedwork__.infra.catraca_sync.requests.post",
        return_value=make_response(status_code=422, text="invalid finger"),
    )

    response = mixin.remote_enroll(1, "biometry", save=True, sync=True)
    assert response.status_code == 422
    assert response.data["details"]["content"] == "invalid finger"

    post.side_effect = requests.Timeout()
    timeout = mixin.remote_enroll(1, "biometry", save=True, sync=True)
    assert timeout.status_code == 408

    mocker.patch.object(mixin, "login", side_effect=CatracaSyncError("login", 502))
    login_error = mixin.remote_enroll(1, "card", save=False, sync=False)
    assert login_error.status_code == 502
    assert login_error.data["error"] == "Erro ao processar cadastro"


@pytest.mark.integration
@pytest.mark.django_db
def test_set_configuration_normalizes_payloads_and_reports_errors(
    mocker, make_response, device_factory
):
    # Testa normalizacao, deteccao de secao raiz e falha por device.
    from src.core.__seedwork__.infra.catraca_sync import CatracaSyncError, ControlIDSyncMixin
    from src.core.control_Id.infra.control_id_django_app.models import Device

    Device.objects.all().delete()
    mixin = ControlIDSyncMixin()
    assert mixin.set_configuration({"online": True}).status_code == 400

    device_factory()
    mocked = mocker.patch.object(
        mixin, "_make_request", return_value=make_response(json_data={"success": True})
    )

    response = mixin.set_configuration({"online": True, "nested": {"timeout": 30}})
    assert response.status_code == 200
    assert mocked.call_args.kwargs["json_data"] == {
        "general": {"online": "1", "nested": {"timeout": "30"}}
    }

    response = mixin.set_configuration({"catra": {"daily_reset": False}})
    assert response.status_code == 200
    assert mocked.call_args.kwargs["json_data"] == {"catra": {"daily_reset": "0"}}

    mocked.return_value = make_response(status_code=500, json_data={"error": "offline"})
    with pytest.raises(CatracaSyncError) as exc:
        mixin.set_configuration({"online": True})
    assert exc.value.status_code == 500
