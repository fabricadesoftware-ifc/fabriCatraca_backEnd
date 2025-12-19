"""
Testes de integração para sincronização com a API da catraca.
Usa mocks para simular a API sem fazer chamadas reais.
"""
import pytest
from unittest.mock import Mock, patch


@pytest.mark.integration
@pytest.mark.django_db
class TestSystemConfigSync:
    """Testes de sincronização do SystemConfig."""
    
    @patch('src.core.__seedwork__.infra.catraca_sync.requests.request')
    def test_sync_from_catraca_success(self, mock_req, device_factory, mock_catraca_response):
        """Deve sincronizar SystemConfig da catraca com sucesso."""
        from src.core.control_id_config.infra.control_id_config_django_app.mixins import SystemConfigSyncMixin
        from src.core.control_id_config.infra.control_id_config_django_app.models import SystemConfig
        
        device = device_factory()
        
        login_response = Mock()
        login_response.status_code = 200
        login_response.json.return_value = {'session': 'test_session'}

        sys_data = mock_catraca_response('system')
        # Ensure we have the fields we expect
        if 'general' not in sys_data:
             sys_data['general'] = {}
        sys_data['general']['online'] = '1'
        sys_data['general']['language'] = 'pt'

        config_response = Mock()
        config_response.status_code = 200
        config_response.json.return_value = sys_data

        def side_effect(*args, **kwargs):
            # Check positional args or kwargs for URL info
            # requests.request(method, url, ...)
            url = kwargs.get('url')
            if not url and len(args) > 1:
                url = args[1]

            if url and 'login.fcgi' in url:
                return login_response
            return config_response

        mock_req.side_effect = side_effect
        
        # Executar sync
        mixin = SystemConfigSyncMixin()
        mixin.set_device(device)
        result = mixin.sync_system_config_from_catraca()
        
        # Verificar resultado
        assert result.status_code == 200
        
        # Verificar que foi criado no banco
        config = SystemConfig.objects.get(device=device)
        assert config.online is True
        assert config.language == 'pt'
    
    @patch('src.core.__seedwork__.infra.catraca_sync.requests.request')
    def test_sync_to_catraca_success(self, mock_req, system_config_factory):
        """Deve enviar SystemConfig para catraca com sucesso."""
        from src.core.control_id_config.infra.control_id_config_django_app.mixins import SystemConfigSyncMixin
        
        # Cria config com valor específico
        config = system_config_factory(online=True, language='en')

        login_response = Mock()
        login_response.status_code = 200
        login_response.json.return_value = {'session': 'test_session'}

        action_response = Mock()
        action_response.status_code = 200
        action_response.json.return_value = {'success': True}
        
        def side_effect(*args, **kwargs):
            url = kwargs.get('url')
            if not url and len(args) > 1:
                url = args[1]
            if url and 'login.fcgi' in url:
                return login_response
            return action_response

        mock_req.side_effect = side_effect
        
        # Executar update
        mixin = SystemConfigSyncMixin()
        mixin.set_device(config.device)
        result = mixin.update_system_config_in_catraca(config)
        
        assert mock_req.called
        assert result.status_code == 200

@pytest.mark.integration
@pytest.mark.django_db
class TestCatraConfigSync:
    """Testes de sincronização do CatraConfig."""
    
    @patch('src.core.__seedwork__.infra.catraca_sync.requests.request')
    def test_sync_from_catraca_success(self, mock_req, device_factory, mock_catraca_response):
        """Deve sincronizar CatraConfig da catraca com sucesso."""
        from src.core.control_id_config.infra.control_id_config_django_app.mixins import CatraConfigSyncMixin
        from src.core.control_id_config.infra.control_id_config_django_app.models import CatraConfig
        
        device = device_factory()
        
        login_response = Mock()
        login_response.status_code = 200
        login_response.json.return_value = {'session': 'test_session'}

        config_response = Mock()
        config_response.status_code = 200
        config_response.json.return_value = mock_catraca_response('catra')

        def side_effect(*args, **kwargs):
            url = kwargs.get('url')
            if not url and len(args) > 1:
                url = args[1]
            if url and 'login.fcgi' in url:
                return login_response
            return config_response

        mock_req.side_effect = side_effect
        
        # Executar sync
        mixin = CatraConfigSyncMixin()
        mixin.set_device(device)
        result = mixin.sync_catra_config_from_catraca()
        
        # Verificar resultado
        assert result.status_code == 200
        
        # Verificar que foi criado no banco
        config = CatraConfig.objects.get(device=device)
        assert config.gateway == 'clockwise'
        assert config.operation_mode == 'blocked'
        assert config.anti_passback is False
    
    @patch('src.core.__seedwork__.infra.catraca_sync.requests.request')
    def test_sync_to_catraca_success(self, mock_req, catra_config_factory):
        """Deve enviar CatraConfig para catraca com sucesso."""
        from src.core.control_id_config.infra.control_id_config_django_app.mixins import CatraConfigSyncMixin
        
        config = catra_config_factory(
            anti_passback=True,
            gateway='anticlockwise'
        )
        
        login_response = Mock()
        login_response.status_code = 200
        login_response.json.return_value = {'session': 'test_session'}

        action_response = Mock()
        action_response.status_code = 200
        action_response.json.return_value = {'success': True}

        def side_effect(*args, **kwargs):
            url = kwargs.get('url')
            if not url and len(args) > 1:
                url = args[1]
            if url and 'login.fcgi' in url:
                return login_response
            return action_response

        mock_req.side_effect = side_effect
        
        # Executar update
        mixin = CatraConfigSyncMixin()
        mixin.set_device(config.device)
        result = mixin.update_catra_config_in_catraca(config)
        
        # Verificar que chamou a API
        assert mock_req.called
        
        # Verificar payload enviado
        found_payload = False
        for call in mock_req.call_args_list:
            # Check kwargs
            if 'json' in call.kwargs and 'catra' in call.kwargs['json']:
                payload = call.kwargs['json']
                assert payload['catra']['anti_passback'] == '1'
                assert payload['catra']['gateway'] == 'anticlockwise'
                found_payload = True
                break
            # Check positional args? requests.request(method, url, json=?)
            # json is usually kwarg in requests.request

        assert found_payload, "Payload de catra não encontrado nas chamadas"
        assert result.status_code == 200
    
    @patch('src.core.__seedwork__.infra.catraca_sync.requests.request')
    def test_sync_from_catraca_connection_error(self, mock_req, device_factory):
        """Deve tratar erro de conexão com a catraca."""
        from src.core.control_id_config.infra.control_id_config_django_app.mixins import CatraConfigSyncMixin
        
        device = device_factory()
        
        # Mock de erro de conexão logo no login
        mock_req.side_effect = Exception("Connection refused")
        
        # Executar sync
        mixin = CatraConfigSyncMixin()
        mixin.set_device(device)
        result = mixin.sync_catra_config_from_catraca()
        
        # Verificar que retornou erro
        assert result.status_code == 500


@pytest.mark.integration
@pytest.mark.django_db
class TestPushServerConfigSync:
    """Testes de sincronização do PushServerConfig."""
    
    @patch('src.core.__seedwork__.infra.catraca_sync.requests.request')
    def test_sync_from_catraca_success(self, mock_req, device_factory, mock_catraca_response):
        """Deve sincronizar PushServerConfig da catraca com sucesso."""
        from src.core.control_id_config.infra.control_id_config_django_app.mixins import PushServerConfigSyncMixin
        from src.core.control_id_config.infra.control_id_config_django_app.models import PushServerConfig
        
        device = device_factory()
        
        # Mock Sequência
        login_response = Mock()
        login_response.status_code = 200
        login_response.json.return_value = {'session': 'test_session'}

        config_response = Mock()
        config_response.status_code = 200
        config_response.json.return_value = mock_catraca_response('push_server')

        mock_req.side_effect = [login_response, config_response]
        
        # Executar sync
        mixin = PushServerConfigSyncMixin()
        mixin.set_device(device)
        result = mixin.sync_push_server_config_from_catraca()
        
        # Verificar resultado
        assert result.status_code == 200
        
        # Verificar que foi criado no banco
        config = PushServerConfig.objects.get(device=device)
        assert config.push_request_timeout == 15000
    
    @patch('src.core.__seedwork__.infra.catraca_sync.requests.request')
    def test_sync_to_catraca_with_validation(self, mock_req, push_server_config_factory):
        """Deve validar dados antes de enviar para catraca."""
        from src.core.control_id_config.infra.control_id_config_django_app.mixins import PushServerConfigSyncMixin
        
        config = push_server_config_factory(
            push_request_timeout=20000,
            push_request_period=120,
            push_remote_address='10.0.0.5:9090'
        )
        
        login_response = Mock()
        login_response.status_code = 200
        login_response.json.return_value = {'session': 'test_session'}

        action_response = Mock()
        action_response.status_code = 200
        action_response.json.return_value = {'success': True}

        mock_req.side_effect = [login_response, action_response]
        
        # Executar update
        mixin = PushServerConfigSyncMixin()
        mixin.set_device(config.device)
        result = mixin.update_push_server_config_in_catraca(config)
        
        # Verificar payload
        found_payload = False
        for call in mock_req.call_args_list:
            if 'json' in call[1] and 'push_server' in call[1]['json']:
                payload = call[1]['json']
                assert payload['push_server']['push_request_timeout'] == '20000'
                assert payload['push_server']['push_remote_address'] == '10.0.0.5:9090'
                found_payload = True
                break

        assert found_payload
        assert result.status_code == 200

@pytest.mark.integration
@pytest.mark.django_db
class TestHardwareConfigSync:
    """Testes de sincronização do HardwareConfig."""
    @patch('src.core.__seedwork__.infra.catraca_sync.requests.request')
    def test_sync_from_catraca_success(self, mock_req, device_factory, mock_catraca_response):
        """Deve sincronizar HardwareConfig da catraca com sucesso."""
        from src.core.control_id_config.infra.control_id_config_django_app.mixins import HardwareConfigSyncMixin
        from src.core.control_id_config.infra.control_id_config_django_app.models import HardwareConfig
        device = device_factory()
        login_response = Mock()
        login_response.status_code = 200
        login_response.json.return_value = {'session': 'test_session'}

        config_response = Mock()
        config_response.status_code = 200
        config_response.json.return_value = mock_catraca_response('hardware', beep_enabled='1')

        mock_req.side_effect = [login_response, config_response]

        mixin = HardwareConfigSyncMixin()
        mixin.set_device(device)
        result = mixin.sync_hardware_config_from_catraca()
        
        assert result.status_code == 200
        config = HardwareConfig.objects.get(device=device)
        assert config.beep_enabled is True

@pytest.mark.integration
@pytest.mark.django_db
class TestSecurityConfigSync:
    """Testes de sincronização do SecurityConfig."""
    @patch('src.core.__seedwork__.infra.catraca_sync.requests.request')
    def test_sync_from_catraca_success(self, mock_req, device_factory, mock_catraca_response):
        """Deve sincronizar SecurityConfig da catraca com sucesso."""
        from src.core.control_id_config.infra.control_id_config_django_app.mixins import SecurityConfigSyncMixin
        from src.core.control_id_config.infra.control_id_config_django_app.models import SecurityConfig
        device = device_factory()
        login_response = Mock()
        login_response.status_code = 200
        login_response.json.return_value = {'session': 'test_session'}

        config_response = Mock()
        config_response.status_code = 200
        config_response.json.return_value = mock_catraca_response('security', password_only='1')

        mock_req.side_effect = [login_response, config_response]

        mixin = SecurityConfigSyncMixin()
        mixin.set_device(device)
        result = mixin.sync_security_config_from_catraca()
        
        assert result.status_code == 200
        config = SecurityConfig.objects.get(device=device)
        assert config.password_only is True

@pytest.mark.integration
@pytest.mark.django_db
class TestUIConfigSync:
    """Testes de sincronização do UIConfig."""

    @patch('src.core.__seedwork__.infra.catraca_sync.requests.request')
    def test_sync_from_catraca_success(self, mock_req, device_factory, mock_catraca_response):
        """Deve sincronizar UIConfig da catraca com sucesso."""
        from src.core.control_id_config.infra.control_id_config_django_app.mixins import UIConfigSyncMixin
        from src.core.control_id_config.infra.control_id_config_django_app.models import UIConfig
        device = device_factory()
        login_response = Mock()
        login_response.status_code = 200
        login_response.json.return_value = {'session': 'test_session'}

        config_response = Mock()
        config_response.status_code = 200
        config_response.json.return_value = mock_catraca_response('ui', screen_always_on='1')

        mock_req.side_effect = [login_response, config_response]

        mixin = UIConfigSyncMixin()
        mixin.set_device(device)
        result = mixin.sync_ui_config_from_catraca()

        assert result.status_code == 200
        config = UIConfig.objects.get(device=device)
        assert config.screen_always_on is True


@pytest.mark.integration
@pytest.mark.django_db
class TestCeleryTask:
    """Testes para a task Celery de sincronização."""
    
    @patch('src.core.__seedwork__.infra.catraca_sync.requests.request')
    def test_run_config_sync_all_configs(self, mock_req, device_factory):
        """Deve sincronizar todos os tipos de config."""
        from src.core.control_id_config.infra.control_id_config_django_app.tasks import run_config_sync
        
        # Criar 2 dispositivos ativos
        device1 = device_factory(is_active=True)
        device2 = device_factory(is_active=True)
        
        login_response = Mock()
        login_response.status_code = 200
        login_response.json.return_value = {'session': 'task_session'}

        data_response = Mock()
        data_response.status_code = 200
        data_response.json.return_value = {
            'system': {'name': 'Test'},
            'hardware': {},
            'security': {},
            'ui': {},
            'monitor': {},
            'catra': {},
            'push_server': {}
        }

        def side_effect(*args, **kwargs):
            url = args[0] if args else kwargs.get('url', '')
            if 'login.fcgi' in url:
                return login_response
            return data_response

        mock_req.side_effect = side_effect
        
        # Executar task
        result = run_config_sync()
        
        # Verificar resultado
        assert result['success'] is True
        assert result['stats']['devices'] == 2
    
    @patch('src.core.__seedwork__.infra.catraca_sync.requests.request')
    def test_run_config_sync_only_active_devices(self, mock_req, device_factory):
        """Deve sincronizar apenas dispositivos ativos."""
        from src.core.control_id_config.infra.control_id_config_django_app.tasks import run_config_sync
        
        # Criar dispositivos (1 ativo, 1 inativo)
        device_active = device_factory(is_active=True)
        device_inactive = device_factory(is_active=False)
        
        login_response = Mock()
        login_response.status_code = 200
        login_response.json.return_value = {'session': 'task_session'}

        data_response = Mock()
        data_response.status_code = 200
        data_response.json.return_value = {}

        def side_effect(*args, **kwargs):
            url = args[0] if args else kwargs.get('url', '')
            if 'login.fcgi' in url:
                return login_response
            return data_response

        mock_req.side_effect = side_effect
        
        # Executar task
        result = run_config_sync()
        
        # Verificar que processou apenas 1 device
        assert result['stats']['devices'] == 1
