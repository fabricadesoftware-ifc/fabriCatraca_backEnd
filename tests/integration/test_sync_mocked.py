"""
Testes de integração para sincronização com a API da catraca.
Usa mocks para simular a API sem fazer chamadas reais.
"""
import pytest
from unittest.mock import Mock, patch
from rest_framework import status


@pytest.mark.integration
@pytest.mark.django_db
class TestSystemConfigSync:
    """Testes de sincronização do SystemConfig."""
    
    @patch('requests.post')
    def test_sync_from_catraca_success(self, mock_post, device_factory, mock_catraca_response):
        """Deve sincronizar SystemConfig da catraca com sucesso."""
        from src.core.control_id_config.infra.control_id_config_django_app.mixins import SystemConfigSyncMixin
        from src.core.control_id_config.infra.control_id_config_django_app.models import SystemConfig
        
        device = device_factory()
        
        # Mock da resposta da API
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_catraca_response('system')
        mock_post.return_value = mock_response
        
        # Executar sync
        mixin = SystemConfigSyncMixin()
        mixin.set_device(device)
        result = mixin.sync_system_config_from_catraca()
        
        # Verificar resultado
        assert result.status_code == 200
        
        # Verificar que foi criado no banco
        config = SystemConfig.objects.get(device=device)
        assert config.name == 'Catraca Teste'
        assert config.date == '30/09/2025'
    
    @patch('requests.post')
    def test_sync_to_catraca_success(self, mock_post, system_config_factory):
        """Deve enviar SystemConfig para catraca com sucesso."""
        from src.core.control_id_config.infra.control_id_config_django_app.mixins import SystemConfigSyncMixin
        
        config = system_config_factory(name='Catraca Atualizada')
        
        # Mock da resposta da API
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True}
        mock_post.return_value = mock_response
        
        # Executar update
        mixin = SystemConfigSyncMixin()
        mixin.set_device(config.device)
        result = mixin.update_system_config_in_catraca(config)
        
        # Verificar que chamou a API
        assert mock_post.called
        assert result.status_code == 200


@pytest.mark.integration
@pytest.mark.django_db
class TestCatraConfigSync:
    """Testes de sincronização do CatraConfig."""
    
    @patch('requests.post')
    def test_sync_from_catraca_success(self, mock_post, device_factory, mock_catraca_response):
        """Deve sincronizar CatraConfig da catraca com sucesso."""
        from src.core.control_id_config.infra.control_id_config_django_app.mixins import CatraConfigSyncMixin
        from src.core.control_id_config.infra.control_id_config_django_app.models import CatraConfig
        
        device = device_factory()
        
        # Mock da resposta da API
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_catraca_response('catra')
        mock_post.return_value = mock_response
        
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
    
    @patch('requests.post')
    def test_sync_to_catraca_success(self, mock_post, catra_config_factory):
        """Deve enviar CatraConfig para catraca com sucesso."""
        from src.core.control_id_config.infra.control_id_config_django_app.mixins import CatraConfigSyncMixin
        
        config = catra_config_factory(
            anti_passback=True,
            gateway='anticlockwise'
        )
        
        # Mock da resposta da API
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True}
        mock_post.return_value = mock_response
        
        # Executar update
        mixin = CatraConfigSyncMixin()
        mixin.set_device(config.device)
        result = mixin.update_catra_config_in_catraca(config)
        
        # Verificar que chamou a API
        assert mock_post.called
        
        # Verificar payload enviado
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        
        assert 'catra' in payload
        assert payload['catra']['anti_passback'] == '1'  # Boolean convertido para string
        assert payload['catra']['gateway'] == 'anticlockwise'
        
        assert result.status_code == 200
    
    @patch('requests.post')
    def test_sync_from_catraca_connection_error(self, mock_post, device_factory):
        """Deve tratar erro de conexão com a catraca."""
        from src.core.control_id_config.infra.control_id_config_django_app.mixins import CatraConfigSyncMixin
        
        device = device_factory()
        
        # Mock de erro de conexão
        mock_post.side_effect = Exception("Connection refused")
        
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
    
    @patch('requests.post')
    def test_sync_from_catraca_success(self, mock_post, device_factory, mock_catraca_response):
        """Deve sincronizar PushServerConfig da catraca com sucesso."""
        from src.core.control_id_config.infra.control_id_config_django_app.mixins import PushServerConfigSyncMixin
        from src.core.control_id_config.infra.control_id_config_django_app.models import PushServerConfig
        
        device = device_factory()
        
        # Mock da resposta da API
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_catraca_response('push_server')
        mock_post.return_value = mock_response
        
        # Executar sync
        mixin = PushServerConfigSyncMixin()
        mixin.set_device(device)
        result = mixin.sync_push_server_config_from_catraca()
        
        # Verificar resultado
        assert result.status_code == 200
        
        # Verificar que foi criado no banco
        config = PushServerConfig.objects.get(device=device)
        assert config.push_request_timeout == 15000
        assert config.push_request_period == 60
        assert config.push_remote_address == '192.168.1.100:8080'
    
    @patch('requests.post')
    def test_sync_to_catraca_with_validation(self, mock_post, push_server_config_factory):
        """Deve validar dados antes de enviar para catraca."""
        from src.core.control_id_config.infra.control_id_config_django_app.mixins import PushServerConfigSyncMixin
        
        config = push_server_config_factory(
            push_request_timeout=20000,
            push_request_period=120,
            push_remote_address='10.0.0.5:9090'
        )
        
        # Mock da resposta da API
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True}
        mock_post.return_value = mock_response
        
        # Executar update
        mixin = PushServerConfigSyncMixin()
        mixin.set_device(config.device)
        result = mixin.update_push_server_config_in_catraca(config)
        
        # Verificar payload enviado
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        
        assert 'push_server' in payload
        assert payload['push_server']['push_request_timeout'] == '20000'
        assert payload['push_server']['push_request_period'] == '120'
        assert payload['push_server']['push_remote_address'] == '10.0.0.5:9090'
        
        assert result.status_code == 200


@pytest.mark.integration
@pytest.mark.django_db
class TestCeleryTask:
    """Testes para a task Celery de sincronização."""
    
    @patch('requests.post')
    def test_run_config_sync_all_configs(self, mock_post, device_factory):
        """Deve sincronizar todos os tipos de config."""
        from src.core.control_id_config.infra.control_id_config_django_app.tasks import run_config_sync
        
        # Criar 2 dispositivos ativos
        device1 = device_factory(is_active=True)
        device2 = device_factory(is_active=True)
        
        # Mock das respostas
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'system': {'name': 'Test'},
            'hardware': {},
            'security': {},
            'ui': {},
            'monitor': {},
            'catra': {},
            'push_server': {}
        }
        mock_post.return_value = mock_response
        
        # Executar task
        result = run_config_sync()
        
        # Verificar resultado
        assert result['success'] is True
        assert result['stats']['devices'] == 2
        
        # Deve ter chamado a API para cada config de cada device
        # 7 configs * 2 devices = 14 chamadas
        assert mock_post.call_count == 14
    
    @patch('requests.post')
    def test_run_config_sync_only_active_devices(self, mock_post, device_factory):
        """Deve sincronizar apenas dispositivos ativos."""
        from src.core.control_id_config.infra.control_id_config_django_app.tasks import run_config_sync
        
        # Criar dispositivos (1 ativo, 1 inativo)
        device_active = device_factory(is_active=True)
        device_inactive = device_factory(is_active=False)
        
        # Mock das respostas
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'system': {},
            'hardware': {},
            'security': {},
            'ui': {},
            'monitor': {},
            'catra': {},
            'push_server': {}
        }
        mock_post.return_value = mock_response
        
        # Executar task
        result = run_config_sync()
        
        # Verificar que processou apenas 1 device
        assert result['stats']['devices'] == 1
