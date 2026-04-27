import pytest
from rest_framework import status


@pytest.mark.integration
@pytest.mark.django_db
def test_template_upload_raw_capture_handles_incomplete_and_completed_session(
    mocker, make_response, api_client_admin, device_factory
):
    # Testa fluxo completo de tres tentativas de captura biometrica local.
    from src.core.user.infra.user_django_app.models import User
    from src.core.control_id.infra.control_id_django_app.models import (
        BiometricCaptureSession,
        Template,
    )

    extractor = device_factory(name="Catraca A", is_default=True, ip="192.0.2.90")
    device_factory(name="Catraca B", ip="192.0.2.91")
    user = User.objects.create(name="Maria", registration="2026001")
    session = BiometricCaptureSession.objects.create(
        user=user,
        extractor_device=extractor,
        sensor_identifier="local-default",
    )

    mock_post = mocker.patch("requests.post")
    mocker.patch(
        "src.core.__seedwork__.infra.catraca_sync.requests.request",
        return_value=make_response(json_data={"ids": [1]}),
    )
    mock_post.side_effect = [
        make_response(json_data={"session": "sess-1"}),
        make_response(json_data={"quality": 40, "template": "tpl-40"}),
        make_response(json_data={"session": "sess-2"}),
        make_response(json_data={"quality": 82, "template": "tpl-82"}),
        make_response(json_data={"session": "sess-3"}),
        make_response(json_data={"quality": 61, "template": "tpl-61"}),
        make_response(json_data={"session": "sess-a"}),
        make_response(json_data={"session": "sess-b"}),
    ]

    attempt1 = api_client_admin.post(
        f"/api/control_id/templates/local-capture/{session.id}/upload-raw/?api_key=troque-esta-chave-do-dispositivo&capture_token={session.token}&attempt=1&total_attempts=3",
        b"\x11" * 32,
        content_type="application/octet-stream",
    )
    assert attempt1.status_code == status.HTTP_200_OK
    assert attempt1.data["completed"] is False
    assert attempt1.data["capture_session"]["template_id"] is None

    attempt2 = api_client_admin.post(
        f"/api/control_id/templates/local-capture/{session.id}/upload-raw/?api_key=troque-esta-chave-do-dispositivo&capture_token={session.token}&attempt=2&total_attempts=3",
        b"\x22" * 32,
        content_type="application/octet-stream",
    )
    assert attempt2.status_code == status.HTTP_200_OK
    assert attempt2.data["completed"] is False

    response = api_client_admin.post(
        f"/api/control_id/templates/local-capture/{session.id}/upload-raw/?api_key=troque-esta-chave-do-dispositivo&capture_token={session.token}&attempt=3&total_attempts=3",
        b"\x33" * 32,
        content_type="application/octet-stream",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["completed"] is True
    assert response.data["template"]["template"] == "tpl-82"
    assert response.data["template"]["best_quality"] == 82
    assert len(response.data["template"]["attempts"]) == 3

    saved = Template.objects.get(user=user)
    assert saved.template == "tpl-82"
    session.refresh_from_db()
    assert session.status == "completed"
    assert session.selected_quality == 82
    assert session.template_id == saved.id
