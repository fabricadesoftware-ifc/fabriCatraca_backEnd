import pytest
import requests


@pytest.mark.integration
@pytest.mark.django_db
def test_template_remote_enroll_returns_created_payload(
    mocker, make_response, device_factory
):
    # Testa o cadastro remoto interativo sem chamada real ao equipamento.
    from src.core.__seedwork__.infra.catraca_sync import ControlIDSyncMixin

    device = device_factory(ip="192.0.2.31")
    mixin = ControlIDSyncMixin()
    mixin.set_device(device)
    mixin.session = "cached-session"
    remote_post = mocker.patch(
        "src.core.__seedwork__.infra.catraca_sync.requests.post",
        return_value=make_response(
            json_data={
                "type": "biometry",
                "template": "data_base64",
                "success": True,
            }
        ),
    )

    response = mixin.remote_enroll(
        user_id=1, type="biometry", save=False, sync=True
    )

    assert response.status_code == 201
    assert response.data["success"] is True
    assert "remote_enroll.fcgi?session=cached-session" in remote_post.call_args.args[0]
    assert remote_post.call_args.kwargs["json"] == {
        "user_id": 1,
        "type": "biometry",
        "save": False,
        "sync": True,
    }
    assert remote_post.call_args.kwargs["timeout"] == 40


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
