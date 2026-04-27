import pytest


@pytest.mark.integration
def test_normalize_config_value_recursively():
    # Testa normalizacao exigida pela API Control iD: folhas como string.
    from src.core.__seedwork__.infra.catraca_sync import _normalize_config_value

    assert _normalize_config_value(
        {"a": True, "b": [False, None, 3], "c": {"d": "ok"}}
    ) == {"a": "1", "b": ["0", "", "3"], "c": {"d": "ok"}}


@pytest.mark.integration
@pytest.mark.django_db
def test_set_configuration_normalizes_payloads_and_reports_errors(
    mocker, make_response, device_factory
):
    # Testa normalizacao, deteccao de secao raiz e falha por device.
    from src.core.__seedwork__.infra.catraca_sync import (
        CatracaSyncError,
        ControlIDSyncMixin,
    )
    from src.core.control_id.infra.control_id_django_app.models import Device

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
