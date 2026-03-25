import pytest

from src.core.user.infra.user_django_app.serializers import (
    RoleAwareUserReadSerializer,
    UserSerializer,
)
from src.core.user.infra.user_django_app.views import UserViewSet


@pytest.mark.unit
def test_me_uses_user_serializer_without_role_restrictions():
    viewset = UserViewSet()

    viewset.action = "me"
    assert viewset.get_serializer_class() is UserSerializer

    viewset.action = "retrieve"
    assert viewset.get_serializer_class() is RoleAwareUserReadSerializer

