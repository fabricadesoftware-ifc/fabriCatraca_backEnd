import pytest


@pytest.mark.integration
@pytest.mark.django_db
def test_device_test_connection_returns_result_without_api_error(
    api_client_admin,
    device_factory,
    mocker,
    settings,
):
    from src.core.__seedwork__.infra.catraca_sync import CatracaSyncError

    settings.DEVICE_CONNECTION_TEST_TIMEOUT_SECONDS = 1.5
    device = device_factory(is_active=True)
    login = mocker.patch(
        "src.core.__seedwork__.infra.catraca_sync.ControlIDSyncMixin.login",
        side_effect=CatracaSyncError("offline", status_code=502),
    )

    response = api_client_admin.get(
        f"/api/control_id/devices/{device.id}/test_connection/"
    )

    assert response.status_code == 200
    assert response.data["success"] is False
    assert "1.5s" in response.data["message"]
    login.assert_called_once_with(force_new=True, request_timeout=1.5)
    device.refresh_from_db()
    assert device.is_active is False
