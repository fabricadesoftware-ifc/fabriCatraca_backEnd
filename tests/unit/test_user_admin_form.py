import pytest

from src.core.user.infra.user_django_app.admin import UserAdminForm
from src.core.user.infra.user_django_app.models import User


@pytest.mark.unit
def test_user_admin_form_does_not_expose_model_password_field():
    user = User(name="User Test", email="user@example.com")
    user.set_password("secret")

    form = UserAdminForm(instance=user)

    assert "password" not in form.fields
    assert "new_password" in form.fields

