from __future__ import annotations

import pytest
from rest_framework import status
from rest_framework.response import Response

from src.core.control_id.infra.control_id_django_app.models import AccessRule
from src.core.control_id.infra.control_id_django_app.services import (
    AccessRuleDeviceSyncError,
    AccessRuleDeviceSyncService,
)


@pytest.mark.unit
@pytest.mark.django_db
def test_access_rule_sync_service_creates_access_rule_payload(mocker):
    access_rule = AccessRule.objects.create(
        name="Entrada Normal",
        type=1,
        priority=20,
    )
    gateway = mocker.Mock()
    gateway.create_objects.return_value = Response(
        {"success": True},
        status=status.HTTP_201_CREATED,
    )
    service = AccessRuleDeviceSyncService(gateway=gateway)

    service.create(access_rule)

    gateway.create_objects.assert_called_once_with(
        "access_rules",
        [
            {
                "id": access_rule.id,
                "name": "Entrada Normal",
                "type": 1,
                "priority": 20,
            }
        ],
    )


@pytest.mark.integration
@pytest.mark.django_db
def test_access_rule_create_returns_sync_error_and_rolls_back(api_client_admin, mocker):
    mocker.patch(
        "src.core.control_id.infra.control_id_django_app.services."
        "AccessRuleDeviceSyncService.create",
        side_effect=AccessRuleDeviceSyncError(
            "Falha na catraca",
            details={"error": "falhou"},
        ),
    )

    response = api_client_admin.post(
        "/api/control_id/access_rules/",
        {"name": "Regra Falha", "type": 1, "priority": 5},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "access_rule_sync_failed"
    assert response.data["details"] == {"error": "falhou"}
    assert not AccessRule.objects.filter(name="Regra Falha").exists()


@pytest.mark.integration
@pytest.mark.django_db
def test_access_rule_update_returns_sync_error_and_rolls_back(api_client_admin, mocker):
    access_rule = AccessRule.objects.create(
        name="Regra Original",
        type=1,
        priority=10,
    )
    mocker.patch(
        "src.core.control_id.infra.control_id_django_app.services."
        "AccessRuleDeviceSyncService.update",
        side_effect=AccessRuleDeviceSyncError(
            "Falha na catraca",
            details={"error": "falhou"},
        ),
    )

    response = api_client_admin.patch(
        f"/api/control_id/access_rules/{access_rule.id}/",
        {"name": "Regra Alterada"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "access_rule_sync_failed"
    access_rule.refresh_from_db()
    assert access_rule.name == "Regra Original"


@pytest.mark.integration
@pytest.mark.django_db
def test_access_rule_delete_returns_sync_error_and_keeps_local_record(
    api_client_admin,
    mocker,
):
    access_rule = AccessRule.objects.create(
        name="Regra Protegida",
        type=1,
        priority=10,
    )
    mocker.patch(
        "src.core.control_id.infra.control_id_django_app.services."
        "AccessRuleDeviceSyncService.delete",
        side_effect=AccessRuleDeviceSyncError(
            "Falha na catraca",
            details={"error": "falhou"},
        ),
    )

    response = api_client_admin.delete(
        f"/api/control_id/access_rules/{access_rule.id}/",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "access_rule_sync_failed"
    assert AccessRule.objects.filter(id=access_rule.id).exists()
