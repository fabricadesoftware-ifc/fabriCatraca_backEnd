import pytest
from django.urls import reverse

from src.core.user.infra.user_django_app.models import User


@pytest.mark.integration
@pytest.mark.django_db
def test_me_returns_full_user_fields(api_client):
    user = User.objects.create(
        name="Admin SISAE",
        email="admin@sisae.test",
        app_role=User.AppRole.SISAE,
        panel_access_only=True,
        is_active=True,
        is_staff=True,
    )
    user.set_password("admin")
    user.save(update_fields=["password"])

    api_client.force_authenticate(user=user)
    url = reverse("user-me")
    response = api_client.get(url)

    assert response.status_code == 200
    assert response.data["email"] == "admin@sisae.test"
    assert response.data["app_role"] == User.AppRole.SISAE
    assert "effective_app_role" in response.data
    assert "panel_access_only" in response.data

