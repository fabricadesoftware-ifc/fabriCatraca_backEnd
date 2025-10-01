"""
Testes unitários para os models de configuração.
Testes rápidos que não dependem de APIs externas.
"""
import pytest
from django.core.exceptions import ValidationError


@pytest.mark.unit
@pytest.mark.django_db
class TestSystemConfigModel:
    """Testes para o model SystemConfig."""
    
    def test_create_system_config(self, system_config_factory):
        """Deve criar SystemConfig com sucesso."""
        config = system_config_factory(auto_reboot_hour=5, online=True)
        
        assert config.id is not None
        assert config.auto_reboot_hour == 5
        assert config.online is True
        assert config.device is not None
    
    def test_system_config_str(self, system_config_factory):
        """Deve retornar representação string correta."""
        config = system_config_factory()
        
        assert str(config) == f"Configuração do Sistema - {config.device.name}"
    
    def test_system_config_one_to_one_relationship(self, device_factory):
        """Deve garantir relacionamento OneToOne com Device."""
        from src.core.control_id_config.infra.control_id_config_django_app.models import SystemConfig
        from django.db import IntegrityError
        
        device = device_factory()
        config1 = SystemConfig.objects.create(device=device)
        
        # Tentar criar outro config para o mesmo device deve falhar
        with pytest.raises(IntegrityError):
            config2 = SystemConfig.objects.create(device=device)


@pytest.mark.unit
@pytest.mark.django_db
class TestHardwareConfigModel:
    """Testes para o model HardwareConfig."""
    
    def test_create_hardware_config(self, hardware_config_factory):
        """Deve criar HardwareConfig com sucesso."""
        config = hardware_config_factory(relayN_timeout=10)
        
        assert config.id is not None
        assert config.relayN_timeout == 10
    
    def test_boolean_fields_default_values(self, device_factory):
        """Deve usar valores padrão para campos booleanos."""
        from src.core.control_id_config.infra.control_id_config_django_app.models import HardwareConfig
        
        device = device_factory()
        config = HardwareConfig.objects.create(device=device)
        
        assert config.beep_enabled is True
        assert config.bell_enabled is False


@pytest.mark.unit
@pytest.mark.django_db
class TestSecurityConfigModel:
    """Testes para o model SecurityConfig."""
    
    def test_create_security_config(self, security_config_factory):
        """Deve criar SecurityConfig com sucesso."""
        config = security_config_factory(password_only=True)
        
        assert config.id is not None
        assert config.password_only is True
    
    def test_password_only_defaults(self, device_factory):
        """Deve ter password_only desabilitado por padrão."""
        from src.core.control_id_config.infra.control_id_config_django_app.models import SecurityConfig
        
        device = device_factory()
        config = SecurityConfig.objects.create(device=device)
        
        assert config.password_only is False


@pytest.mark.unit
@pytest.mark.django_db
class TestUIConfigModel:
    """Testes para o model UIConfig."""
    
    def test_create_ui_config(self, ui_config_factory):
        """Deve criar UIConfig com sucesso."""
        config = ui_config_factory(screen_always_on=True)
        
        assert config.id is not None
        assert config.screen_always_on is True
    
    def test_screen_always_on_default(self, device_factory):
        """Deve ter screen_always_on desabilitado por padrão."""
        from src.core.control_id_config.infra.control_id_config_django_app.models import UIConfig
        
        device = device_factory()
        config = UIConfig.objects.create(device=device)
        
        assert config.screen_always_on is False


@pytest.mark.unit
@pytest.mark.django_db
class TestCatraConfigModel:
    """Testes para o model CatraConfig."""
    
    def test_create_catra_config(self, catra_config_factory):
        """Deve criar CatraConfig com sucesso."""
        config = catra_config_factory(
            anti_passback=True,
            gateway='anticlockwise'
        )
        
        assert config.id is not None
        assert config.anti_passback is True
        assert config.gateway == 'anticlockwise'
    
    def test_gateway_choices(self, device_factory):
        """Deve validar choices de gateway."""
        from src.core.control_id_config.infra.control_id_config_django_app.models import CatraConfig
        
        device = device_factory()
        
        # Valores válidos
        config1 = CatraConfig.objects.create(
            device=device,
            gateway='clockwise'
        )
        assert config1.gateway == 'clockwise'
        
        config1.gateway = 'anticlockwise'
        config1.save()
        assert config1.gateway == 'anticlockwise'
    
    def test_operation_mode_choices(self, catra_config_factory):
        """Deve validar choices de operation_mode."""
        valid_modes = ['blocked', 'entrance_open', 'exit_open', 'both_open']
        
        for mode in valid_modes:
            config = catra_config_factory(operation_mode=mode)
            assert config.operation_mode == mode
    
    def test_default_values(self, device_factory):
        """Deve usar valores padrão corretos."""
        from src.core.control_id_config.infra.control_id_config_django_app.models import CatraConfig
        
        device = device_factory()
        config = CatraConfig.objects.create(device=device)
        
        assert config.anti_passback is False
        assert config.daily_reset is False
        assert config.gateway == 'clockwise'
        assert config.operation_mode == 'blocked'


@pytest.mark.unit
@pytest.mark.django_db
class TestPushServerConfigModel:
    """Testes para o model PushServerConfig."""
    
    def test_create_push_server_config(self, push_server_config_factory):
        """Deve criar PushServerConfig com sucesso."""
        config = push_server_config_factory(
            push_request_timeout=20000,
            push_remote_address='10.0.0.1:9090'
        )
        
        assert config.id is not None
        assert config.push_request_timeout == 20000
        assert config.push_remote_address == '10.0.0.1:9090'
    
    def test_default_values(self, device_factory):
        """Deve usar valores padrão corretos."""
        from src.core.control_id_config.infra.control_id_config_django_app.models import PushServerConfig
        
        device = device_factory()
        config = PushServerConfig.objects.create(device=device)
        
        assert config.push_request_timeout == 15000
        assert config.push_request_period == 60
        assert config.push_remote_address == ''
    
    def test_timeout_range(self, push_server_config_factory):
        """Deve aceitar timeouts dentro do range válido."""
        config = push_server_config_factory(push_request_timeout=0)
        assert config.push_request_timeout == 0
        
        config.push_request_timeout = 300000
        config.save()
        assert config.push_request_timeout == 300000
    
    def test_period_range(self, push_server_config_factory):
        """Deve aceitar períodos dentro do range válido."""
        config = push_server_config_factory(push_request_period=0)
        assert config.push_request_period == 0
        
        config.push_request_period = 86400
        config.save()
        assert config.push_request_period == 86400
