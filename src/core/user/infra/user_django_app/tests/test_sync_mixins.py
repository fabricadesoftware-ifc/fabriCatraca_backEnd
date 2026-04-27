import pytest


@pytest.mark.integration
@pytest.mark.django_db
def test_user_sync_create_sends_valid_payload_to_selected_device(
    mocker, make_response, device_factory, user_factory
):
    # Testa que usuarios sao criados na catraca com payload obrigatorio completo.
    from src.core.user.infra.user_django_app.sync_mixins.user import UserSyncMixin

    device = device_factory(ip="192.0.2.30")
    user = user_factory(name="Maria Sync", registration="SYNC001")
    login = mocker.patch(
        "src.core.__seedwork__.infra.catraca_sync.requests.post",
        return_value=make_response(json_data={"session": "sess-1"}),
    )
    request = mocker.patch(
        "src.core.__seedwork__.infra.catraca_sync.requests.request",
        return_value=make_response(json_data={"ids": [user.id]}),
    )

    mixin = UserSyncMixin()
    mixin.set_device(device)

    response = mixin.create_objects(
        "users",
        [{"id": user.id, "name": user.name, "registration": user.registration}],
    )

    assert response.status_code == 201
    login.assert_called_once()
    request.assert_called_once()
    assert request.call_args.kwargs["url"].endswith(
        "/create_objects.fcgi?session=sess-1"
    )
    assert request.call_args.kwargs["json"] == {
        "object": "users",
        "values": [
            {
                "id": user.id,
                "name": "Maria Sync",
                "registration": "SYNC001",
            }
        ],
    }
