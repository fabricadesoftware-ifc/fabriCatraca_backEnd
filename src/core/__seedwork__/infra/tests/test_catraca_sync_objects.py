import pytest


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
