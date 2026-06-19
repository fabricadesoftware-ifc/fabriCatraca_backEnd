from __future__ import annotations

import pytest
from rest_framework import status
from rest_framework.response import Response

from src.core.control_id.infra.control_id_django_app.models import (
    AccessRule,
    AccessRuleTimeZone,
    Area,
    CustomGroup,
    GroupAccessRule,
    Portal,
    PortalGroup,
    PortalAccessRule,
    TimeZone,
    UserAccessRule,
)
from src.core.control_id.infra.control_id_django_app.services import (
    AccessRuleRelationDeviceSyncService,
    AccessRuleRelationSyncError,
)


@pytest.fixture
def access_rule(db):
    return AccessRule.objects.create(name="Regra Teste", type=1, priority=10)


@pytest.fixture
def portal(db):
    area_from = Area.objects.create(name="Area Origem")
    area_to = Area.objects.create(name="Area Destino")
    return Portal.objects.create(
        name="Portal Teste",
        area_from=area_from,
        area_to=area_to,
    )


@pytest.fixture
def portal_group(db, device_factory):
    first_device = device_factory(name="Catraca A")
    second_device = device_factory(name="Catraca B")
    group = PortalGroup.objects.create(name="Portais Teste")
    group.devices.add(first_device, second_device)
    return group


@pytest.fixture
def time_zone(db):
    return TimeZone.objects.create(name="Horario Teste")


@pytest.mark.unit
@pytest.mark.django_db
def test_access_rule_sync_service_creates_user_rule_for_portal_group_devices(
    mocker,
    user_factory,
    access_rule,
    portal_group,
):
    user = user_factory()
    instance = UserAccessRule(
        user=user,
        access_rule=access_rule,
        portal_group=portal_group,
    )
    gateway = mocker.Mock()
    gateway.create_or_update_objects.return_value = Response(
        {"success": True},
        status=status.HTTP_200_OK,
    )
    service = AccessRuleRelationDeviceSyncService(gateway=gateway)

    service.create_user_rule(instance)

    expected_device_ids = sorted(portal_group.devices.values_list("id", flat=True))
    gateway.create_or_update_objects.assert_called_once_with(
        "user_access_rules",
        [{"user_id": user.id, "access_rule_id": access_rule.id}],
        device_ids=expected_device_ids,
    )


@pytest.mark.unit
@pytest.mark.django_db
def test_access_rule_sync_service_updates_global_rule_to_portal_group_scope(
    mocker,
    user_factory,
    device_factory,
    access_rule,
):
    user = user_factory()
    kept_device = device_factory(name="Catraca Mantida")
    removed_device = device_factory(name="Catraca Removida")
    portal_group = PortalGroup.objects.create(name="Portais Mantidos")
    portal_group.devices.add(kept_device)
    instance = UserAccessRule(
        user=user,
        access_rule=access_rule,
        portal_group=portal_group,
    )
    gateway = mocker.Mock()
    gateway.destroy_objects.return_value = Response(
        {"success": True},
        status=status.HTTP_204_NO_CONTENT,
    )
    gateway.update_objects.return_value = Response(
        {"success": True},
        status=status.HTTP_200_OK,
    )
    service = AccessRuleRelationDeviceSyncService(gateway=gateway)

    service.update_user_rule(
        instance,
        previous_payload={"user_id": user.id, "access_rule_id": access_rule.id},
        old_device_ids=None,
    )

    gateway.destroy_objects.assert_called_once_with(
        "user_access_rules",
        {
            "user_access_rules": {
                "user_id": user.id,
                "access_rule_id": access_rule.id,
            }
        },
        device_ids=[removed_device.id],
    )
    gateway.update_objects.assert_called_once_with(
        "user_access_rules",
        {"user_id": user.id, "access_rule_id": access_rule.id},
        {
            "user_access_rules": {
                "user_id": user.id,
                "access_rule_id": access_rule.id,
            }
        },
        device_ids=[kept_device.id],
    )
    gateway.create_or_update_objects.assert_not_called()


@pytest.mark.unit
@pytest.mark.django_db
def test_access_rule_sync_service_creates_portal_rule_globally(
    mocker,
    access_rule,
    portal,
):
    instance = PortalAccessRule(portal=portal, access_rule=access_rule)
    gateway = mocker.Mock()
    gateway.create_or_update_objects.return_value = Response(
        {"success": True},
        status=status.HTTP_200_OK,
    )
    service = AccessRuleRelationDeviceSyncService(gateway=gateway)

    service.create_portal_rule(instance)

    gateway.create_or_update_objects.assert_called_once_with(
        "portal_access_rules",
        [{"portal_id": portal.id, "access_rule_id": access_rule.id}],
        device_ids=None,
    )


@pytest.mark.unit
@pytest.mark.django_db
def test_access_rule_sync_service_creates_time_zone_rule_globally(
    mocker,
    access_rule,
    time_zone,
):
    instance = AccessRuleTimeZone(access_rule=access_rule, time_zone=time_zone)
    gateway = mocker.Mock()
    gateway.create_or_update_objects.return_value = Response(
        {"success": True},
        status=status.HTTP_200_OK,
    )
    service = AccessRuleRelationDeviceSyncService(gateway=gateway)

    service.create_time_zone_rule(instance)

    gateway.create_or_update_objects.assert_called_once_with(
        "access_rule_time_zones",
        [{"access_rule_id": access_rule.id, "time_zone_id": time_zone.id}],
        device_ids=None,
    )


@pytest.mark.integration
@pytest.mark.django_db
def test_user_access_rule_create_returns_sync_error_and_rolls_back(
    api_client_admin,
    mocker,
    user_factory,
    access_rule,
):
    user = user_factory()
    mocker.patch(
        "src.core.control_id.infra.control_id_django_app.services."
        "AccessRuleRelationDeviceSyncService.create_user_rule",
        side_effect=AccessRuleRelationSyncError(
            "Falha na catraca",
            details={"error": "falhou"},
        ),
    )

    response = api_client_admin.post(
        "/api/control_id/user_access_rules/",
        {"user_id": user.id, "access_rule_id": access_rule.id},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "user_access_rule_sync_failed"
    assert response.data["details"] == {"error": "falhou"}
    assert not UserAccessRule.objects.filter(
        user=user,
        access_rule=access_rule,
    ).exists()


@pytest.mark.integration
@pytest.mark.django_db
def test_group_access_rule_create_returns_sync_error_and_rolls_back(
    api_client_admin,
    mocker,
    access_rule,
):
    group = CustomGroup.objects.create(name="Turma Teste")
    mocker.patch(
        "src.core.control_id.infra.control_id_django_app.services."
        "AccessRuleRelationDeviceSyncService.create_group_rule",
        side_effect=AccessRuleRelationSyncError(
            "Falha na catraca",
            details={"error": "falhou"},
        ),
    )

    response = api_client_admin.post(
        "/api/control_id/group_access_rules/",
        {"group_id": group.id, "access_rule_id": access_rule.id},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "group_access_rule_sync_failed"
    assert response.data["details"] == {"error": "falhou"}
    assert not GroupAccessRule.objects.filter(
        group=group,
        access_rule=access_rule,
    ).exists()


@pytest.mark.integration
@pytest.mark.django_db
def test_portal_access_rule_create_returns_sync_error_and_rolls_back(
    api_client_admin,
    mocker,
    access_rule,
    portal,
):
    mocker.patch(
        "src.core.control_id.infra.control_id_django_app.services."
        "AccessRuleRelationDeviceSyncService.create_portal_rule",
        side_effect=AccessRuleRelationSyncError(
            "Falha na catraca",
            details={"error": "falhou"},
        ),
    )

    response = api_client_admin.post(
        "/api/control_id/portal_access_rules/",
        {"portal_id": portal.id, "access_rule_id": access_rule.id},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "portal_access_rule_sync_failed"
    assert response.data["details"] == {"error": "falhou"}
    assert not PortalAccessRule.objects.filter(
        portal=portal,
        access_rule=access_rule,
    ).exists()


@pytest.mark.integration
@pytest.mark.django_db
def test_portal_access_rule_create_existing_returns_ok_without_sync(
    api_client_admin,
    mocker,
    access_rule,
    portal,
):
    instance = PortalAccessRule.objects.create(
        portal=portal,
        access_rule=access_rule,
    )
    create_portal_rule = mocker.patch(
        "src.core.control_id.infra.control_id_django_app.services."
        "AccessRuleRelationDeviceSyncService.create_portal_rule",
    )

    response = api_client_admin.post(
        "/api/control_id/portal_access_rules/",
        {"portal_id": portal.id, "access_rule_id": access_rule.id},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == instance.id
    create_portal_rule.assert_not_called()


@pytest.mark.integration
@pytest.mark.django_db
def test_access_rule_time_zone_create_returns_sync_error_and_rolls_back(
    api_client_admin,
    mocker,
    access_rule,
    time_zone,
):
    mocker.patch(
        "src.core.control_id.infra.control_id_django_app.services."
        "AccessRuleRelationDeviceSyncService.create_time_zone_rule",
        side_effect=AccessRuleRelationSyncError(
            "Falha na catraca",
            details={"error": "falhou"},
        ),
    )

    response = api_client_admin.post(
        "/api/control_id/access_rule_time_zones/",
        {"access_rule_id": access_rule.id, "time_zone_id": time_zone.id},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "access_rule_time_zone_sync_failed"
    assert response.data["details"] == {"error": "falhou"}
    assert not AccessRuleTimeZone.objects.filter(
        access_rule=access_rule,
        time_zone=time_zone,
    ).exists()


@pytest.mark.integration
@pytest.mark.django_db
def test_access_rule_time_zone_create_existing_returns_ok_without_sync(
    api_client_admin,
    mocker,
    access_rule,
    time_zone,
):
    instance = AccessRuleTimeZone.objects.create(
        access_rule=access_rule,
        time_zone=time_zone,
    )
    create_time_zone_rule = mocker.patch(
        "src.core.control_id.infra.control_id_django_app.services."
        "AccessRuleRelationDeviceSyncService.create_time_zone_rule",
    )

    response = api_client_admin.post(
        "/api/control_id/access_rule_time_zones/",
        {"access_rule_id": access_rule.id, "time_zone_id": time_zone.id},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == instance.id
    create_time_zone_rule.assert_not_called()
