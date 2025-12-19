
import pytest
from unittest.mock import Mock, patch, MagicMock
from rest_framework import status

@pytest.mark.integration
@pytest.mark.django_db
class TestCoreEntityMixins:
    """Testes para os mixins de entidades core (User, Card, Template, etc)."""

    @pytest.fixture
    def user_factory(self, db):
        from src.core.user.infra.user_django_app.models import User
        def create_user(**kwargs):
            defaults = {'name': 'Test User', 'registration': '12345'}
            defaults.update(kwargs)
            return User.objects.create(**defaults)
        return create_user

    @patch('requests.post')
    def test_user_sync_create(self, mock_post, device_factory, user_factory):
        """Testa criação de usuário na catraca via mixin."""
        from src.core.user.infra.user_django_app.sync_mixins.user import UserSyncMixin
        
        device = device_factory()
        user = user_factory()
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'ids': [user.id]}
        mock_post.return_value = mock_response
        
        mixin = UserSyncMixin()
        mixin.set_device(device)
        
        # Simula criação
        response = mixin.create_objects("users", [{
            "id": user.id,
            "name": user.name,
            "registration": user.registration
        }])
        
        assert response.status_code == 201
        assert "create_objects.fcgi" in mock_post.call_args[0][0]

    @patch('requests.post')
    def test_template_remote_enroll_flow(self, mock_post, device_factory):
        """
        Testa o fluxo de cadastro remoto de biometria (fix recente).
        Garante que usa o timeout correto e device correto.
        """
        from src.core.__seedwork__.infra.catraca_sync import ControlIDSyncMixin
        
        device = device_factory()
        mixin = ControlIDSyncMixin()
        mixin.set_device(device)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"template": "data_base64"}
        mock_post.return_value = mock_response
        
        response = mixin.remote_enroll(user_id=1, type="biometry", save=False, sync=True)
        
        assert response.status_code == 201
        
        # Verifica argumentos
        args, kwargs = mock_post.call_args
        assert "remote_enroll.fcgi" in args[0]
        
        payload = kwargs['json']
        assert payload['timeout'] == 30  # Timeout da catraca
        assert kwargs['timeout'] == 35   # Timeout do request (30 + 5)
