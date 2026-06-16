import pytest
from rest_framework import status
from rest_framework.response import Response


@pytest.mark.unit
@pytest.mark.django_db
def test_user_group_device_sync_service_ensures_group_user_and_relation(
    mocker,
    device_factory,
    user_factory,
):
    from src.core.control_id.infra.control_id_django_app.models import (
        CustomGroup,
        UserGroup,
    )
    from src.core.control_id.infra.control_id_django_app.services import (
        UserGroupDeviceSyncService,
    )
    from src.core.user.infra.user_django_app.models import User

    device = device_factory(name="Catraca Fabrica")
    user = user_factory(
        name="Aluno Teste",
        registration="A123",
        device_scope=User.DeviceScope.SELECTED,
    )
    user.selected_devices.add(device)
    group = CustomGroup.objects.create(name="1INFO1")
    instance = UserGroup(user=user, group=group)
    gateway = mocker.Mock()
    gateway.create_or_update_objects.return_value = Response(
        {"success": True},
        status=status.HTTP_200_OK,
    )
    service = UserGroupDeviceSyncService(gateway=gateway)

    service.create(instance)

    gateway.set_device.assert_called_once_with(device)
    assert [call.args[0] for call in gateway.create_or_update_objects.call_args_list] == [
        "groups",
        "users",
        "user_groups",
    ]
    assert gateway.create_or_update_objects.call_args_list[0].args[1] == [
        {"id": group.id, "name": group.name}
    ]
    assert gateway.create_or_update_objects.call_args_list[1].args[1] == [
        {
            "id": user.id,
            "name": user.name,
            "registration": user.registration,
            "begin_time": 0,
            "end_time": 0,
        }
    ]
    assert gateway.create_or_update_objects.call_args_list[2].args[1] == [
        {"user_id": user.id, "group_id": group.id}
    ]
    assert [
        call.kwargs["device_ids"]
        for call in gateway.create_or_update_objects.call_args_list
    ] == [[device.id], [device.id], [device.id]]


@pytest.mark.integration
@pytest.mark.django_db
def test_user_group_create_returns_sync_error_and_rolls_back_local_relation(
    api_client_admin, mocker, user_factory
):
    from src.core.__seedwork__.infra.catraca_sync import CatracaSyncError
    from src.core.control_id.infra.control_id_django_app.models import (
        CustomGroup,
        UserGroup,
    )

    user = user_factory(name="Aluno Vinculo", registration="UG001")
    group = CustomGroup.objects.create(name="1INFO1")
    mocker.patch(
        "src.core.control_id.infra.control_id_django_app.services.UserGroupDeviceSyncService.create",
        side_effect=CatracaSyncError(
            "Falha ao criar/atualizar 'user_groups' no device 'Catraca Fabrica': {'error': 'constraint failed: FOREIGN KEY constraint failed', 'code': 1}",
            status_code=status.HTTP_400_BAD_REQUEST,
        ),
    )

    response = api_client_admin.post(
        "/api/control_id/user_groups/",
        {"user": user.id, "group": group.id},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        response.data["error"]
        == "Erro ao sincronizar vinculo de usuario e grupo na catraca."
    )
    assert response.data["code"] == "user_group_sync_failed"
    assert "FOREIGN KEY constraint failed" in response.data["details"]
    assert not UserGroup.objects.filter(user=user, group=group).exists()
