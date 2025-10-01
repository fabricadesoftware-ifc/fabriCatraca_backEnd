"""
Testes de integração para as ViewSets (API REST).
"""
import pytest
from rest_framework import status
from django.urls import reverse


@pytest.mark.integration
@pytest.mark.django_db
class TestCatraConfigViewSet:
    """Testes para a API REST de CatraConfig."""
    
    def test_list_catra_configs(self, api_client, catra_config_factory):
        """Deve listar todos os CatraConfigs."""
        # Criar alguns configs
        config1 = catra_config_factory()
        config2 = catra_config_factory()
        
        url = '/api/control_id_config/catra-configs/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 2
    
    def test_create_catra_config(self, api_client, device_factory):
        """Deve criar um novo CatraConfig via API."""
        device = device_factory()
        
        url = '/api/control_id_config/catra-configs/'
        data = {
            'device': device.id,
            'anti_passback': True,
            'daily_reset': False,
            'gateway': 'clockwise',
            'operation_mode': 'entrance_open'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['gateway'] == 'clockwise'
        assert response.data['anti_passback'] is True
    
    def test_retrieve_catra_config(self, api_client, catra_config_factory):
        """Deve buscar um CatraConfig específico."""
        config = catra_config_factory(gateway='anticlockwise')
        
        url = f'/api/control_id_config/catra-configs/{config.id}/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['gateway'] == 'anticlockwise'
        assert 'gateway_display' in response.data
    
    def test_update_catra_config(self, api_client, catra_config_factory):
        """Deve atualizar um CatraConfig via API."""
        config = catra_config_factory(operation_mode='blocked')
        
        url = f'/api/control_id_config/catra-configs/{config.id}/'
        data = {
            'device': config.device.id,
            'anti_passback': config.anti_passback,
            'daily_reset': config.daily_reset,
            'gateway': config.gateway,
            'operation_mode': 'both_open'
        }
        
        response = api_client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['operation_mode'] == 'both_open'
    
    def test_delete_catra_config(self, api_client, catra_config_factory):
        """Deve deletar um CatraConfig via API."""
        config = catra_config_factory()
        
        url = f'/api/control_id_config/catra-configs/{config.id}/'
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
    
    def test_filter_by_gateway(self, api_client, catra_config_factory):
        """Deve filtrar configs por gateway."""
        config1 = catra_config_factory(gateway='clockwise')
        config2 = catra_config_factory(gateway='anticlockwise')
        
        url = '/api/control_id_config/catra-configs/?gateway=clockwise'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        assert all(item['gateway'] == 'clockwise' for item in response.data)
    
    def test_validate_invalid_gateway(self, api_client, device_factory):
        """Deve rejeitar gateway inválido."""
        device = device_factory()
        
        url = '/api/control_id_config/catra-configs/'
        data = {
            'device': device.id,
            'gateway': 'invalid_value',
            'operation_mode': 'blocked'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'gateway' in response.data


@pytest.mark.integration
@pytest.mark.django_db
class TestPushServerConfigViewSet:
    """Testes para a API REST de PushServerConfig."""
    
    def test_list_push_server_configs(self, api_client, push_server_config_factory):
        """Deve listar todos os PushServerConfigs."""
        config1 = push_server_config_factory()
        config2 = push_server_config_factory()
        
        url = '/api/control_id_config/push-server-configs/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 2
    
    def test_create_push_server_config(self, api_client, device_factory):
        """Deve criar um novo PushServerConfig via API."""
        device = device_factory()
        
        url = '/api/control_id_config/push-server-configs/'
        data = {
            'device': device.id,
            'push_request_timeout': 20000,
            'push_request_period': 120,
            'push_remote_address': '192.168.1.50:8080'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['push_request_timeout'] == 20000
        assert response.data['push_remote_address'] == '192.168.1.50:8080'
    
    def test_validate_timeout_range(self, api_client, device_factory):
        """Deve validar range de timeout."""
        device = device_factory()
        
        url = '/api/control_id_config/push-server-configs/'
        data = {
            'device': device.id,
            'push_request_timeout': 400000,  # Maior que 300000
            'push_request_period': 60
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'push_request_timeout' in response.data
    
    def test_validate_period_range(self, api_client, device_factory):
        """Deve validar range de período."""
        device = device_factory()
        
        url = '/api/control_id_config/push-server-configs/'
        data = {
            'device': device.id,
            'push_request_timeout': 15000,
            'push_request_period': 100000  # Maior que 86400
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'push_request_period' in response.data
    
    def test_validate_address_format(self, api_client, device_factory):
        """Deve validar formato de endereço."""
        device = device_factory()
        
        url = '/api/control_id_config/push-server-configs/'
        data = {
            'device': device.id,
            'push_request_timeout': 15000,
            'push_request_period': 60,
            'push_remote_address': 'invalid_address'  # Sem porta
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'push_remote_address' in response.data
    
    def test_empty_address_allowed(self, api_client, device_factory):
        """Deve permitir endereço vazio."""
        device = device_factory()
        
        url = '/api/control_id_config/push-server-configs/'
        data = {
            'device': device.id,
            'push_request_timeout': 15000,
            'push_request_period': 60,
            'push_remote_address': ''
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['push_remote_address'] == ''


@pytest.mark.integration
@pytest.mark.django_db
class TestSystemConfigViewSet:
    """Testes para a API REST de SystemConfig."""
    
    def test_list_system_configs(self, api_client, system_config_factory):
        """Deve listar todos os SystemConfigs."""
        config1 = system_config_factory()
        config2 = system_config_factory()
        
        url = '/api/control_id_config/system-configs/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 2
    
    def test_filter_by_device(self, api_client, device_factory, system_config_factory):
        """Deve filtrar configs por dispositivo."""
        device1 = device_factory()
        device2 = device_factory()
        
        config1 = system_config_factory(device=device1)
        config2 = system_config_factory(device=device2)
        
        url = f'/api/control_id_config/system-configs/?device={device1.id}'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        assert all(item['device'] == device1.id for item in response.data)
