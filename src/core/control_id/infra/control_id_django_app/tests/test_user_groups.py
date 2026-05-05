import pytest
from rest_framework import status


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
        "src.core.control_id.infra.control_id_django_app.views.user_groups.UserGroupViewSet.create_in_catraca",
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
    assert "FOREIGN KEY constraint failed" in response.data["details"]
    assert not UserGroup.objects.filter(user=user, group=group).exists()
