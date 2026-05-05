import pytest
from rest_framework import status
from rest_framework.response import Response


@pytest.mark.integration
@pytest.mark.django_db
def test_user_group_sync_ensures_group_and_user_before_relation(
    mocker, device_factory, user_factory
):
    from src.core.__seedwork__.infra.mixins.user_groups import UserGroupsSyncMixin
    from src.core.control_id.infra.control_id_django_app.models import (
        CustomGroup,
        UserGroup,
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

    mixin = UserGroupsSyncMixin()
    create_or_update = mocker.patch.object(
        mixin,
        "create_or_update_objects",
        side_effect=[
            Response({"success": True}, status=status.HTTP_200_OK),
            Response({"success": True}, status=status.HTTP_200_OK),
            Response({"success": True}, status=status.HTTP_200_OK),
        ],
    )

    response = mixin.create_in_catraca(instance)

    assert response.status_code == status.HTTP_201_CREATED
    assert [call.args[0] for call in create_or_update.call_args_list] == [
        "groups",
        "users",
        "user_groups",
    ]
    assert create_or_update.call_args_list[0].args[1] == [
        {"id": group.id, "name": group.name}
    ]
    assert create_or_update.call_args_list[1].args[1] == [
        {
            "id": user.id,
            "name": user.name,
            "registration": user.registration,
            "begin_time": 0,
            "end_time": 0,
        }
    ]
    assert create_or_update.call_args_list[2].args[1] == [
        {"user_id": user.id, "group_id": group.id}
    ]
