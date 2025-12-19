
import pytest
from unittest.mock import MagicMock, patch
from src.core.control_id_monitor.infra.control_id_monitor_django_app.models import MonitorConfig
from src.core.control_id_monitor.infra.control_id_monitor_django_app.mixins import MonitorConfigSyncMixin

class MockMonitorSync(MonitorConfigSyncMixin):
    """Classe mock para testar o mixin sem dependencias do Django ViewSet"""
    def __init__(self, device):
        self._device = device
        self.session = "mock_session"

@pytest.fixture
def monitor_config_factory(db, device_factory):
    def create_monitor_config(**kwargs):
        if 'device' not in kwargs:
            kwargs['device'] = device_factory()
            
        defaults = {}
        defaults.update(kwargs)
        return MonitorConfig.objects.create(**kwargs)
        
    return create_monitor_config

@pytest.mark.unit
@pytest.mark.django_db
class TestMonitorConfigSync:

    @patch('src.core.__seedwork__.infra.catraca_sync.requests')
    def test_sync_cleared_fields(self, mock_requests, device_factory):
        """
        Verifica se campos vazios (hostname, port, path) são enviados como strings vazias
        para limpar a configuração na catraca.
        """
        device = device_factory(ip='192.168.1.10', username='admin', password='pw')
        
        # Cria config com campos vazios (simulando limpeza)
        config = MonitorConfig(
            device=device,
            hostname="",
            port="",
            path="",
            request_timeout=1000
        )
        
        # Mock do login e resposta da catraca
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        
        # O método _make_request usa requests.request
        mock_requests.request.return_value = mock_response
        
        # Instancia o mixin
        mixin = MockMonitorSync(device)
        
        # Mock do login para não tentar conectar de verdade
        with patch.object(mixin, 'login', return_value='session_123'):
             mixin.update_monitor_config_in_catraca(config)
             
        # Verifica argumentos da chamada requests.request
        args, kwargs = mock_requests.request.call_args
        
        # args[0] é o method (POST), args[1] é url (se passado como arg) ou kwargs['url']
        assert kwargs['method'] == "POST"
        assert "set_configuration.fcgi" in kwargs['url']
        
        payload = kwargs['json']
        monitor_payload = payload.get('monitor')
        
        # Verifica se enviou as chaves com valores vazios
        assert monitor_payload['hostname'] == ""
        assert monitor_payload['port'] == ""
        assert monitor_payload['path'] == ""
        assert monitor_payload['request_timeout'] == "1000"

    @patch('src.core.__seedwork__.infra.catraca_sync.requests')
    def test_sync_filled_fields(self, mock_requests, device_factory):
        """
        Verifica se campos preenchidos são enviados corretamente.
        """
        device = device_factory()
        
        config = MonitorConfig(
            device=device,
            hostname="api.test.com",
            port="8080",
            path="/events",
            request_timeout=5000
        )
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_requests.request.return_value = mock_response
        
        mixin = MockMonitorSync(device)
        
        with patch.object(mixin, 'login', return_value='session_123'):
             mixin.update_monitor_config_in_catraca(config)
             
        # Verifica payload
        args, kwargs = mock_requests.request.call_args
        payload = kwargs['json']
        monitor_payload = payload.get('monitor')
        
        assert monitor_payload['hostname'] == "api.test.com"
        assert monitor_payload['port'] == "8080"
        assert monitor_payload['path'] == "/events"
        assert monitor_payload['request_timeout'] == "5000"
