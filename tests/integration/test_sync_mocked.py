import pytest


def _patch_request(mocker, make_response, payload, status_code=200):
    return mocker.patch(
        "src.core.__seedwork__.infra.catraca_sync.ControlIDSyncMixin._make_request",
        return_value=make_response(status_code=status_code, json_data=payload),
    )


@pytest.mark.integration
@pytest.mark.django_db
def test_system_config_sync_from_catraca_updates_local_model(
    mocker, make_response, device_factory, mock_catraca_response
):
    # Testa leitura da configuracao geral da catraca e persistencia local.
    from src.core.control_id_config.infra.control_id_config_django_app.mixins import (
        SystemConfigSyncMixin,
    )
    from src.core.control_id_config.infra.control_id_config_django_app.models import (
        SystemConfig,
    )

    device = device_factory()
    mocked = _patch_request(mocker, make_response, mock_catraca_response("system"))

    mixin = SystemConfigSyncMixin()
    mixin.set_device(device)
    response = mixin.sync_system_config_from_catraca()

    assert response.status_code == 200
    config = SystemConfig.objects.get(device=device)
    assert config.online is True
    assert config.local_identification is True
    assert config.language == "pt_BR"
    assert mocked.call_args.kwargs["json_data"]["general"] == [
        "online",
        "auto_reboot",
        "catra_timeout",
        "local_identification",
        "exception_mode",
        "language",
        "daylight_savings_time_start",
        "daylight_savings_time_end",
    ]


@pytest.mark.integration
@pytest.mark.django_db
def test_system_config_update_normalizes_booleans_and_language(
    mocker, make_response, system_config_factory
):
    # Testa payload enviado ao firmware para configuracao geral.
    from src.core.control_id_config.infra.control_id_config_django_app.mixins import (
        SystemConfigSyncMixin,
    )

    config = system_config_factory(online=True, local_identification=False, language="pt")
    mocked = _patch_request(mocker, make_response, {"success": True})

    mixin = SystemConfigSyncMixin()
    mixin.set_device(config.device)
    response = mixin.update_system_config_in_catraca(config)

    assert response.status_code == 200
    assert mocked.call_args.kwargs["json_data"] == {
        "general": {
            "catra_timeout": "30000",
            "online": "1",
            "local_identification": "0",
            "language": "pt_BR",
        }
    }


@pytest.mark.integration
@pytest.mark.django_db
def test_catra_config_sync_from_catraca_handles_boolean_strings(
    mocker, make_response, device_factory, mock_catraca_response
):
    # Testa conversao de flags "0"/"1" da secao catra.
    from src.core.control_id_config.infra.control_id_config_django_app.mixins import (
        CatraConfigSyncMixin,
    )
    from src.core.control_id_config.infra.control_id_config_django_app.models import (
        CatraConfig,
    )

    payload = mock_catraca_response(
        "catra",
        catra={
            "anti_passback": "1",
            "daily_reset": "0",
            "gateway": "anticlockwise",
            "operation_mode": "both_open",
        },
    )
    device = device_factory()
    _patch_request(mocker, make_response, payload)

    mixin = CatraConfigSyncMixin()
    mixin.set_device(device)
    response = mixin.sync_catra_config_from_catraca()

    assert response.status_code == 200
    config = CatraConfig.objects.get(device=device)
    assert config.anti_passback is True
    assert config.daily_reset is False
    assert config.gateway == "anticlockwise"
    assert config.operation_mode == "both_open"


@pytest.mark.integration
@pytest.mark.django_db
def test_catra_config_update_returns_remote_error(
    mocker, make_response, catra_config_factory
):
    # Testa falha HTTP do firmware ao atualizar a secao catra.
    from src.core.control_id_config.infra.control_id_config_django_app.mixins import (
        CatraConfigSyncMixin,
    )

    config = catra_config_factory(anti_passback=True)
    _patch_request(mocker, make_response, {"error": "invalid"}, status_code=500)

    mixin = CatraConfigSyncMixin()
    mixin.set_device(config.device)
    response = mixin.update_catra_config_in_catraca(config)

    assert response.status_code == 500
    assert response.data["success"] is False


@pytest.mark.integration
@pytest.mark.django_db
def test_push_server_config_sync_and_update_payload(
    mocker, make_response, device_factory, push_server_config_factory, mock_catraca_response
):
    # Testa round trip da configuracao de push server sem rede real.
    from src.core.control_id_config.infra.control_id_config_django_app.mixins import (
        PushServerConfigSyncMixin,
    )
    from src.core.control_id_config.infra.control_id_config_django_app.models import (
        PushServerConfig,
    )

    device = device_factory()
    sync_payload = mock_catraca_response(
        "push_server",
        push_server={
            "push_request_timeout": "20000",
            "push_request_period": "120",
            "push_remote_address": "192.0.2.80:9090",
        },
    )
    mocked = _patch_request(mocker, make_response, sync_payload)
    mixin = PushServerConfigSyncMixin()
    mixin.set_device(device)

    sync_response = mixin.sync_push_server_config_from_catraca()
    assert sync_response.status_code == 200
    saved = PushServerConfig.objects.get(device=device)
    assert saved.push_request_timeout == 20000
    assert saved.push_request_period == 120

    mocked.return_value = make_response(json_data={"success": True})
    response = mixin.update_push_server_config_in_catraca(saved)
    assert response.status_code == 200
    assert mocked.call_args.kwargs["json_data"]["push_server"] == {
        "push_request_timeout": "20000",
        "push_request_period": "120",
        "push_remote_address": "192.0.2.80:9090",
    }


@pytest.mark.integration
@pytest.mark.django_db
def test_hardware_config_sync_preserves_network_interlock(
    mocker, make_response, hardware_config_factory, mock_catraca_response
):
    # Testa que campos locais de intertravamento nao sao apagados pelo sync.
    from src.core.control_id_config.infra.control_id_config_django_app.mixins import (
        HardwareConfigSyncMixin,
    )

    existing = hardware_config_factory(
        network_interlock_enabled=True,
        network_interlock_api_bypass_enabled=True,
        network_interlock_rex_bypass_enabled=False,
    )
    _patch_request(mocker, make_response, mock_catraca_response("hardware"))

    mixin = HardwareConfigSyncMixin()
    mixin.set_device(existing.device)
    response = mixin.sync_hardware_config_from_catraca()

    assert response.status_code == 200
    existing.refresh_from_db()
    assert existing.beep_enabled is True
    assert existing.network_interlock_enabled is True
    assert existing.network_interlock_api_bypass_enabled is True


@pytest.mark.integration
@pytest.mark.django_db
def test_hardware_config_update_requires_both_configuration_calls(
    mocker, make_response, hardware_config_factory
):
    # Testa que hardware envia configuracao geral e intertravamento de rede.
    from src.core.control_id_config.infra.control_id_config_django_app.mixins import (
        HardwareConfigSyncMixin,
    )

    config = hardware_config_factory(
        beep_enabled=False,
        network_interlock_enabled=True,
        network_interlock_api_bypass_enabled=True,
    )
    mocked = mocker.patch(
        "src.core.__seedwork__.infra.catraca_sync.ControlIDSyncMixin._make_request",
        side_effect=[
            make_response(json_data={"success": True}),
            make_response(json_data={"success": True}),
        ],
    )

    mixin = HardwareConfigSyncMixin()
    mixin.set_device(config.device)
    response = mixin.update_hardware_config_in_catraca(config)

    assert response.status_code == 200
    assert mocked.call_args_list[0].args[0] == "set_configuration.fcgi"
    assert mocked.call_args_list[1].args[0] == "set_network_interlock.fcgi"
    assert mocked.call_args_list[1].kwargs["json_data"] == {
        "interlock_enabled": 1,
        "api_bypass_enabled": 1,
        "rex_bypass_enabled": 0,
    }


@pytest.mark.integration
@pytest.mark.django_db
def test_security_config_sync_and_update_identifier_payload(
    mocker, make_response, device_factory, mock_catraca_response
):
    # Testa o bloco identifier usado pela configuracao de seguranca.
    from src.core.control_id_config.infra.control_id_config_django_app.mixins import (
        SecurityConfigSyncMixin,
    )
    from src.core.control_id_config.infra.control_id_config_django_app.models import (
        SecurityConfig,
    )

    device = device_factory()
    mocked = _patch_request(mocker, make_response, mock_catraca_response("security"))
    mixin = SecurityConfigSyncMixin()
    mixin.set_device(device)

    sync_response = mixin.sync_security_config_from_catraca()
    assert sync_response.status_code == 200
    saved = SecurityConfig.objects.get(device=device)
    assert saved.verbose_logging_enabled is True
    assert saved.multi_factor_authentication_enabled is True

    mocked.return_value = make_response(json_data={"success": True})
    saved.log_type = True
    response = mixin.update_security_config_in_catraca(saved)

    assert response.status_code == 200
    assert mocked.call_args.kwargs["json_data"] == {
        "identifier": {
            "multi_factor_authentication": "1",
            "verbose_logging": "1",
            "log_type": "1",
        }
    }


@pytest.mark.integration
@pytest.mark.django_db
def test_ui_config_sync_is_local_only(device_factory):
    # Testa que UIConfig nao chama firmware no build atual e cria registro local.
    from src.core.control_id_config.infra.control_id_config_django_app.mixins import (
        UIConfigSyncMixin,
    )
    from src.core.control_id_config.infra.control_id_config_django_app.models import UIConfig

    device = device_factory()
    mixin = UIConfigSyncMixin()
    mixin.set_device(device)

    response = mixin.sync_ui_config_from_catraca()

    assert response.status_code == 200
    assert UIConfig.objects.filter(device=device).exists()


@pytest.mark.integration
@pytest.mark.django_db
def test_sync_mixin_returns_500_when_transport_raises(mocker, device_factory):
    # Testa tratamento de falha de transporte no sync de catra.
    from src.core.control_id_config.infra.control_id_config_django_app.mixins import (
        CatraConfigSyncMixin,
    )

    mocker.patch(
        "src.core.__seedwork__.infra.catraca_sync.ControlIDSyncMixin._make_request",
        side_effect=RuntimeError("offline"),
    )
    mixin = CatraConfigSyncMixin()
    mixin.set_device(device_factory())

    response = mixin.sync_catra_config_from_catraca()

    assert response.status_code == 500
    assert "offline" in response.data["error"]
