import pytest

from src.core.user.infra.user_django_app.serializers import (
    RoleAwareUserReadSerializer,
    UserSerializer,
)
from src.core.user.infra.user_django_app.models import User
from src.core.user.infra.user_django_app.views import UserViewSet


@pytest.mark.unit
def test_me_uses_user_serializer_without_role_restrictions():
    viewset = UserViewSet()

    viewset.action = "me"
    assert viewset.get_serializer_class() is UserSerializer

    viewset.action = "retrieve"
    assert viewset.get_serializer_class() is RoleAwareUserReadSerializer


@pytest.mark.unit
@pytest.mark.django_db
def test_user_serializer_requires_selected_devices_when_scope_is_selected(
    device_factory,
):
    device = device_factory()
    serializer = UserSerializer(
        data={
            "name": "Visitante",
            "registration": "V123",
            "device_scope": User.DeviceScope.SELECTED,
            "selected_device_ids": [device.id],
        }
    )

    assert serializer.is_valid(), serializer.errors

    serializer_without_devices = UserSerializer(
        data={
            "name": "Visitante 2",
            "registration": "V124",
            "device_scope": User.DeviceScope.SELECTED,
        }
    )

    assert not serializer_without_devices.is_valid()
    assert "selected_device_ids" in serializer_without_devices.errors


@pytest.mark.unit
@pytest.mark.django_db
def test_user_serializer_rejects_panel_only_with_non_none_scope():
    serializer = UserSerializer(
        data={
            "name": "Painel",
            "email": "painel@example.com",
            "password": "123456",
            "app_role": User.AppRole.ADMIN,
            "panel_access_only": True,
            "device_scope": User.DeviceScope.ALL_ACTIVE,
        }
    )

    assert not serializer.is_valid()
    assert "device_scope" in serializer.errors
