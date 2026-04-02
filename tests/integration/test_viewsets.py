"""
Testes de integração para as ViewSets (API REST).
"""
import pytest
from rest_framework import status
from django.urls import reverse
from unittest.mock import Mock, patch


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


@pytest.mark.integration
@pytest.mark.django_db
class TestTemplateViewSet:
    @patch("requests.post")
    def test_upload_raw_capture_creates_template_and_marks_session_completed(
        self,
        mock_post,
        api_client,
        device_factory,
    ):
        from src.core.user.infra.user_django_app.models import User
        from src.core.control_Id.infra.control_id_django_app.models import (
            BiometricCaptureSession,
            Template,
        )

        extractor = device_factory(name="Catraca A", is_default=True, ip="10.0.0.10")
        device_factory(name="Catraca B", ip="10.0.0.11")
        user = User.objects.create(name="Maria", registration="2026001")
        session = BiometricCaptureSession.objects.create(
            user=user,
            extractor_device=extractor,
            sensor_identifier="local-default",
        )

        def build_response(status_code=200, json_data=None, text=""):
            response = Mock()
            response.status_code = status_code
            response.json.return_value = json_data or {}
            response.text = text
            response.content = text.encode() if text else b"{}"
            response.raise_for_status = Mock()
            return response

        mock_post.side_effect = [
            build_response(json_data={"session": "sess-1"}),
            build_response(json_data={"quality": 40, "template": "tpl-40"}),
            build_response(json_data={"session": "sess-2"}),
            build_response(json_data={"quality": 82, "template": "tpl-82"}),
            build_response(json_data={"session": "sess-3"}),
            build_response(json_data={"quality": 61, "template": "tpl-61"}),
            build_response(json_data={"session": "sess-a"}),
            build_response(json_data={"ids": [1]}),
            build_response(json_data={"session": "sess-b"}),
            build_response(json_data={"ids": [1]}),
        ]

        attempt1 = api_client.post(
            f"/api/control_id/templates/local-capture/{session.id}/upload-raw/?api_key=troque-esta-chave-do-dispositivo&capture_token={session.token}&attempt=1&total_attempts=3",
            b"\x11" * 32,
            content_type="application/octet-stream",
        )
        assert attempt1.status_code == status.HTTP_200_OK
        assert attempt1.data["completed"] is False

        attempt2 = api_client.post(
            f"/api/control_id/templates/local-capture/{session.id}/upload-raw/?api_key=troque-esta-chave-do-dispositivo&capture_token={session.token}&attempt=2&total_attempts=3",
            b"\x22" * 32,
            content_type="application/octet-stream",
        )
        assert attempt2.status_code == status.HTTP_200_OK
        assert attempt2.data["completed"] is False

        response = api_client.post(
            f"/api/control_id/templates/local-capture/{session.id}/upload-raw/?api_key=troque-esta-chave-do-dispositivo&capture_token={session.token}&attempt=3&total_attempts=3",
            b"\x33" * 32,
            content_type="application/octet-stream",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["completed"] is True
        assert response.data["template"]["template"] == "tpl-82"
        assert response.data["template"]["best_quality"] == 82
        assert len(response.data["template"]["attempts"]) == 3
        assert any(item["selected"] for item in response.data["template"]["attempts"])

        saved = Template.objects.get(user=user)
        assert saved.template == "tpl-82"

        session.refresh_from_db()
        assert session.status == "completed"
        assert session.selected_quality == 82
        assert session.template_id == saved.id

        create_calls = [
            call for call in mock_post.call_args_list if "create_objects.fcgi" in call.args[0]
        ]
        assert len(create_calls) == 2
