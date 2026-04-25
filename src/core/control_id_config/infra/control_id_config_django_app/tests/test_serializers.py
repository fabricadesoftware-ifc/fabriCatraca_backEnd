"""
Testes unitários para os serializers de configuração.
"""
import pytest
from rest_framework.exceptions import ValidationError


@pytest.mark.unit
@pytest.mark.django_db
class TestSystemConfigSerializer:
    """Testes para SystemConfigSerializer."""
    
    def test_serialize_system_config(self, system_config_factory):
        """Deve serializar SystemConfig corretamente."""
        from src.core.control_id_config.infra.control_id_config_django_app.serializers import SystemConfigSerializer
        
        config = system_config_factory()
        serializer = SystemConfigSerializer(config)
        
        assert 'id' in serializer.data
        assert 'device' in serializer.data
        assert 'auto_reboot_hour' in serializer.data
        assert 'online' in serializer.data
        assert 'language' in serializer.data
    
    def test_deserialize_valid_data(self, device_factory):
        """Deve criar SystemConfig a partir de dados válidos."""
        from src.core.control_id_config.infra.control_id_config_django_app.serializers import SystemConfigSerializer
        
        device = device_factory()
        data = {
            'device': device.id,
            'auto_reboot_hour': 5,
            'auto_reboot_minute': 30,
            'online': True,
            'language': 'en'
        }
        
        serializer = SystemConfigSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        config = serializer.save()
        
        assert config.auto_reboot_hour == 5
        assert config.device.id == device.id


@pytest.mark.unit
@pytest.mark.django_db
class TestCatraConfigSerializer:
    """Testes para CatraConfigSerializer."""
    
    def test_serialize_catra_config(self, catra_config_factory):
        """Deve serializar CatraConfig corretamente."""
        from src.core.control_id_config.infra.control_id_config_django_app.serializers import CatraConfigSerializer
        
        config = catra_config_factory(gateway='anticlockwise')
        serializer = CatraConfigSerializer(config)
        
        assert serializer.data['gateway'] == 'anticlockwise'
        assert 'gateway_display' in serializer.data
        assert 'operation_mode_display' in serializer.data
    
    def test_validate_gateway_valid(self, device_factory):
        """Deve aceitar gateway válido."""
        from src.core.control_id_config.infra.control_id_config_django_app.serializers import CatraConfigSerializer
        
        device = device_factory()
        data = {
            'device': device.id,
            'gateway': 'clockwise',
            'operation_mode': 'blocked'
        }
        
        serializer = CatraConfigSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
    
    def test_validate_gateway_invalid(self, device_factory):
        """Deve rejeitar gateway inválido."""
        from src.core.control_id_config.infra.control_id_config_django_app.serializers import CatraConfigSerializer
        
        device = device_factory()
        data = {
            'device': device.id,
            'gateway': 'invalid_gateway',
            'operation_mode': 'blocked'
        }
        
        serializer = CatraConfigSerializer(data=data)
        assert not serializer.is_valid()
        assert 'gateway' in serializer.errors
    
    def test_validate_operation_mode_valid(self, device_factory):
        """Deve aceitar operation_mode válido."""
        from src.core.control_id_config.infra.control_id_config_django_app.serializers import CatraConfigSerializer
        
        device = device_factory()
        valid_modes = ['blocked', 'entrance_open', 'exit_open', 'both_open']
        
        for mode in valid_modes:
            data = {
                'device': device.id,
                'gateway': 'clockwise',
                'operation_mode': mode
            }
            
            serializer = CatraConfigSerializer(data=data)
            assert serializer.is_valid(), f"Failed for mode: {mode}, errors: {serializer.errors}"
    
    def test_validate_operation_mode_invalid(self, device_factory):
        """Deve rejeitar operation_mode inválido."""
        from src.core.control_id_config.infra.control_id_config_django_app.serializers import CatraConfigSerializer
        
        device = device_factory()
        data = {
            'device': device.id,
            'gateway': 'clockwise',
            'operation_mode': 'invalid_mode'
        }
        
        serializer = CatraConfigSerializer(data=data)
        assert not serializer.is_valid()
        assert 'operation_mode' in serializer.errors


@pytest.mark.unit
@pytest.mark.django_db
class TestPushServerConfigSerializer:
    """Testes para PushServerConfigSerializer."""
    
    def test_serialize_push_server_config(self, push_server_config_factory):
        """Deve serializar PushServerConfig corretamente."""
        from src.core.control_id_config.infra.control_id_config_django_app.serializers import PushServerConfigSerializer
        
        config = push_server_config_factory()
        serializer = PushServerConfigSerializer(config)
        
        assert 'push_request_timeout' in serializer.data
        assert 'push_request_period' in serializer.data
        assert 'push_remote_address' in serializer.data
    
    def test_validate_timeout_valid(self, device_factory):
        """Deve aceitar timeout válido (0-300000ms)."""
        from src.core.control_id_config.infra.control_id_config_django_app.serializers import PushServerConfigSerializer
        
        device = device_factory()
        
        valid_timeouts = [0, 1000, 15000, 300000]
        for timeout in valid_timeouts:
            data = {
                'device': device.id,
                'push_request_timeout': timeout,
                'push_request_period': 60
            }
            
            serializer = PushServerConfigSerializer(data=data)
            assert serializer.is_valid(), f"Failed for timeout: {timeout}, errors: {serializer.errors}"
    
    def test_validate_timeout_invalid(self, device_factory):
        """Deve rejeitar timeout inválido (> 300000ms)."""
        from src.core.control_id_config.infra.control_id_config_django_app.serializers import PushServerConfigSerializer
        
        device = device_factory()
        data = {
            'device': device.id,
            'push_request_timeout': 300001,
            'push_request_period': 60
        }
        
        serializer = PushServerConfigSerializer(data=data)
        assert not serializer.is_valid()
        assert 'push_request_timeout' in serializer.errors
    
    def test_validate_period_valid(self, device_factory):
        """Deve aceitar período válido (0-86400s)."""
        from src.core.control_id_config.infra.control_id_config_django_app.serializers import PushServerConfigSerializer
        
        device = device_factory()
        
        valid_periods = [0, 60, 3600, 86400]
        for period in valid_periods:
            data = {
                'device': device.id,
                'push_request_timeout': 15000,
                'push_request_period': period
            }
            
            serializer = PushServerConfigSerializer(data=data)
            assert serializer.is_valid(), f"Failed for period: {period}, errors: {serializer.errors}"
    
    def test_validate_period_invalid(self, device_factory):
        """Deve rejeitar período inválido (> 86400s)."""
        from src.core.control_id_config.infra.control_id_config_django_app.serializers import PushServerConfigSerializer
        
        device = device_factory()
        data = {
            'device': device.id,
            'push_request_timeout': 15000,
            'push_request_period': 86401
        }
        
        serializer = PushServerConfigSerializer(data=data)
        assert not serializer.is_valid()
        assert 'push_request_period' in serializer.errors
    
    def test_validate_address_format_valid(self, device_factory):
        """Deve aceitar endereço no formato IP:porta."""
        from src.core.control_id_config.infra.control_id_config_django_app.serializers import PushServerConfigSerializer
        
        device = device_factory()
        
        valid_addresses = [
            '192.168.1.100:8080',
            '10.0.0.1:80',
            '172.16.0.1:9090',
            ''  # Vazio é permitido
        ]
        
        for address in valid_addresses:
            data = {
                'device': device.id,
                'push_request_timeout': 15000,
                'push_request_period': 60,
                'push_remote_address': address
            }
            
            serializer = PushServerConfigSerializer(data=data)
            assert serializer.is_valid(), f"Failed for address: {address}, errors: {serializer.errors}"
    
    def test_validate_address_format_invalid(self, device_factory):
        """Deve rejeitar endereço em formato inválido."""
        from src.core.control_id_config.infra.control_id_config_django_app.serializers import PushServerConfigSerializer
        
        device = device_factory()
        
        invalid_addresses = [
            '192.168.1.100',  # Sem porta
            'invalid',
            '192.168.1.100:99999',  # Porta inválida
        ]
        
        for address in invalid_addresses:
            data = {
                'device': device.id,
                'push_request_timeout': 15000,
                'push_request_period': 60,
                'push_remote_address': address
            }
            
            serializer = PushServerConfigSerializer(data=data)
            assert not serializer.is_valid(), f"Should fail for address: {address}"
            assert 'push_remote_address' in serializer.errors
