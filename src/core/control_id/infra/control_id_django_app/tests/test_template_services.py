from __future__ import annotations

import pytest
from rest_framework import status
from rest_framework.response import Response

from src.core.control_id.infra.control_id_django_app.services import (
    BiometricEnrollmentService,
    BiometricTemplateExtractionService,
    TemplateDeviceSyncError,
    TemplateDeviceSyncService,
)


@pytest.mark.unit
@pytest.mark.django_db
def test_biometric_enrollment_service_returns_captured_template(
    mocker,
    device_factory,
):
    device = device_factory()
    gateway = mocker.Mock()
    gateway.remote_enroll.return_value = Response(
        {"template": "template-base64"},
        status=status.HTTP_201_CREATED,
    )
    service = BiometricEnrollmentService(gateway=gateway)

    captured_template = service.capture_template(device, user_id=123)

    assert captured_template == "template-base64"
    gateway.set_device.assert_called_once_with(device)
    gateway.remote_enroll.assert_called_once_with(
        user_id=123,
        enrollment_type="biometry",
        save=False,
        sync=True,
    )


@pytest.mark.unit
@pytest.mark.django_db
def test_template_device_sync_service_targets_single_device(
    mocker,
    user_factory,
    device_factory,
):
    user = user_factory()
    device = device_factory()
    template = user.templates.create(template="tpl")
    gateway = mocker.Mock()
    gateway.create_objects.return_value = Response(
        {"success": True},
        status=status.HTTP_201_CREATED,
    )
    service = TemplateDeviceSyncService(gateway=gateway)

    service.create_template_in_device(device, template)

    gateway.set_device.assert_called_once_with(device)
    gateway.create_objects.assert_called_once_with(
        "templates",
        [
            {
                "id": template.id,
                "user_id": user.id,
                "template": "tpl",
                "finger_type": 0,
                "finger_position": 0,
            }
        ],
        device_ids=[device.id],
    )


@pytest.mark.unit
@pytest.mark.django_db
def test_template_device_sync_service_raises_on_device_error(
    mocker,
    user_factory,
    device_factory,
):
    user = user_factory()
    device = device_factory()
    template = user.templates.create(template="tpl")
    gateway = mocker.Mock()
    gateway.create_objects.return_value = Response(
        {"error": "falhou"},
        status=status.HTTP_400_BAD_REQUEST,
    )
    service = TemplateDeviceSyncService(gateway=gateway)

    with pytest.raises(TemplateDeviceSyncError):
        service.create_template_in_device(device, template)


@pytest.mark.unit
@pytest.mark.django_db
def test_biometric_template_extraction_service_expands_and_extracts(
    mocker,
    user_factory,
    device_factory,
):
    user = user_factory()
    extractor = device_factory()
    session = user.biometric_capture_sessions.create(extractor_device=extractor)
    gateway = mocker.Mock()
    gateway.extract_template.return_value = {"quality": 88, "template": "tpl-88"}
    service = BiometricTemplateExtractionService(gateway=gateway)

    extracted = service.extract_template_from_raw_capture(session, b"\x1f")

    assert extracted == {"quality": 88, "template": "tpl-88"}
    gateway.extract_template.assert_called_once_with(extractor, b"\x11\xff")
