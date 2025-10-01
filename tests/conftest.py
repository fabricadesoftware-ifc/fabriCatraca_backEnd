import pytest
from rest_framework.test import APIClient
from faker import Faker

fake = Faker('pt_BR')


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def device_factory(db):
    from src.core.control_Id.infra.control_id_django_app.models import Device
    
    def create_device(**kwargs):
        defaults = {
            'name': fake.company(),
            'ip': fake.ipv4(),
            'username': 'admin',
            'password': 'admin',
            'is_active': True,
        }
        defaults.update(kwargs)
        return Device.objects.create(**defaults)
    
    return create_device


@pytest.fixture
def catra_config_factory(db, device_factory):
    from src.core.control_id_config.infra.control_id_config_django_app.models import CatraConfig
    
    def create_catra_config(**kwargs):
        if 'device' not in kwargs:
            kwargs['device'] = device_factory()
        
        defaults = {
            'anti_passback': False,
            'daily_reset': False,
            'gateway': 'clockwise',
            'operation_mode': 'blocked',
        }
        defaults.update(kwargs)
        return CatraConfig.objects.create(**defaults)
    
    return create_catra_config


@pytest.fixture
def push_server_config_factory(db, device_factory):
    from src.core.control_id_config.infra.control_id_config_django_app.models import PushServerConfig
    
    def create_push_server_config(**kwargs):
        if 'device' not in kwargs:
            kwargs['device'] = device_factory()
        
        defaults = {
            'push_request_timeout': 15000,
            'push_request_period': 60,
            'push_remote_address': f'{fake.ipv4()}:8080',
        }
        defaults.update(kwargs)
        return PushServerConfig.objects.create(**defaults)
    
    return create_push_server_config


@pytest.fixture
def system_config_factory(db, device_factory):
    from src.core.control_id_config.infra.control_id_config_django_app.models import SystemConfig
    
    def create_system_config(**kwargs):
        if 'device' not in kwargs:
            kwargs['device'] = device_factory()
        
        defaults = {
            'auto_reboot_hour': 3,
            'auto_reboot_minute': 0,
            'clear_expired_users': False,
            'keep_user_image': True,
            'url_reboot_enabled': True,
            'web_server_enabled': True,
            'online': True,
            'local_identification': True,
            'language': 'pt',
            'catra_timeout': 30,
        }
        defaults.update(kwargs)
        return SystemConfig.objects.create(**defaults)
    
    return create_system_config


@pytest.fixture
def hardware_config_factory(db, device_factory):
    from src.core.control_id_config.infra.control_id_config_django_app.models import HardwareConfig
    
    def create_hardware_config(**kwargs):
        if 'device' not in kwargs:
            kwargs['device'] = device_factory()
        
        defaults = {
            'beep_enabled': True,
            'bell_enabled': False,
            'bell_relay': 1,
            'ssh_enabled': False,
            'relayN_enabled': False,
            'relayN_timeout': 5,
            'relayN_auto_close': True,
            'door_sensorN_enabled': False,
            'door_sensorN_idle': 10,
            'doorN_interlock': False,
            'exception_mode': False,
            'doorN_exception_mode': False,
        }
        defaults.update(kwargs)
        return HardwareConfig.objects.create(**defaults)
    
    return create_hardware_config


@pytest.fixture
def security_config_factory(db, device_factory):
    from src.core.control_id_config.infra.control_id_config_django_app.models import SecurityConfig
    
    def create_security_config(**kwargs):
        if 'device' not in kwargs:
            kwargs['device'] = device_factory()
        
        defaults = {
            'password_only': False,
            'hide_password_only': False,
            'password_only_tip': '',
            'hide_name_on_identification': False,
            'denied_transaction_code': '',
            'send_code_when_not_identified': False,
            'send_code_when_not_authorized': False,
        }
        defaults.update(kwargs)
        return SecurityConfig.objects.create(**defaults)
    
    return create_security_config


@pytest.fixture
def ui_config_factory(db, device_factory):
    from src.core.control_id_config.infra.control_id_config_django_app.models import UIConfig
    
    def create_ui_config(**kwargs):
        if 'device' not in kwargs:
            kwargs['device'] = device_factory()
        
        defaults = {
            'screen_always_on': False,
        }
        defaults.update(kwargs)
        return UIConfig.objects.create(**defaults)
    
    return create_ui_config


@pytest.fixture
def monitor_config_factory(db, device_factory):
    from src.core.control_id_config.infra.control_id_config_django_app.models import MonitorConfig
    
    def create_monitor_config(**kwargs):
        if 'device' not in kwargs:
            kwargs['device'] = device_factory()
        
        defaults = {}
        defaults.update(kwargs)
        return MonitorConfig.objects.create(**defaults)
    
    return create_monitor_config


@pytest.fixture
def mock_catraca_response():
    def create_response(config_type='system', success=True, **extra_data):
        if not success:
            return {'error': 'Connection failed', 'code': 500}
        
        responses = {
            'system': {
                'system': {
                    'name': 'Catraca Teste',
                    'date': '30/09/2025',
                    'time': '14:30:00',
                    'timezone': 'America/Sao_Paulo',
                    'dst': '0'
                }
            },
            'catra': {
                'catra': {
                    'anti_passback': '0',
                    'daily_reset': '0',
                    'gateway': 'clockwise',
                    'operation_mode': 'blocked'
                }
            },
            'push_server': {
                'push_server': {
                    'push_request_timeout': '15000',
                    'push_request_period': '60',
                    'push_remote_address': '192.168.1.100:8080'
                }
            }
        }
        
        response = responses.get(config_type, {})
        response.update(extra_data)
        return response
    
    return create_response
