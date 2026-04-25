"""
Testes End-to-End (E2E) com chamadas reais à API da catraca.
ATENÇÃO: Estes testes fazem requisições reais. Configure um dispositivo de teste.

Para rodar apenas estes testes:
    pdm test-e2e

Para pular estes testes:
    pdm test -m "not e2e"
"""
import pytest
import os
from django.conf import settings


# Configuração do dispositivo de teste
# Pode ser configurado via variáveis de ambiente
TEST_DEVICE_IP = os.getenv('TEST_CATRACA_IP', '192.168.1.100')
TEST_DEVICE_PORT = os.getenv('TEST_CATRACA_PORT', '80')

# Pular testes E2E se não estiver configurado
skip_if_no_test_device = pytest.mark.skipif(
    not os.getenv('RUN_E2E_TESTS'),
    reason="E2E tests skipped. Set RUN_E2E_TESTS=1 to run."
)


@pytest.mark.e2e
@pytest.mark.slow
@skip_if_no_test_device
@pytest.mark.django_db
class TestSystemConfigE2E:
    """Testes E2E para SystemConfig com catraca real."""
    
    def test_real_sync_from_catraca(self, device_factory):
        """Deve sincronizar SystemConfig de uma catraca real."""
        from src.core.control_id_config.infra.control_id_config_django_app.mixins import SystemConfigSyncMixin
        from src.core.control_id_config.infra.control_id_config_django_app.models import SystemConfig
        
        # Criar device com IP real
        device = device_factory(
            ip=TEST_DEVICE_IP,
            port=TEST_DEVICE_PORT,
            name='Catraca Teste E2E'
        )
        
        # Executar sync real
        mixin = SystemConfigSyncMixin()
        mixin.set_device(device)
        result = mixin.sync_system_config_from_catraca()
        
        # Verificar resultado
        assert result.status_code == 200, f"Failed: {result.data}"
        
        # Verificar que foi salvo no banco
        config = SystemConfig.objects.get(device=device)
        assert config.name is not None
        assert config.date is not None
        
        print(f"\n✓ SystemConfig sincronizado da catraca:")
        print(f"  Nome: {config.name}")
        print(f"  Data: {config.date}")
        print(f"  Hora: {config.time}")
    
    def test_real_update_to_catraca(self, device_factory, system_config_factory):
        """Deve enviar SystemConfig para uma catraca real."""
        from src.core.control_id_config.infra.control_id_config_django_app.mixins import SystemConfigSyncMixin
        
        # Criar device com IP real
        device = device_factory(
            ip=TEST_DEVICE_IP,
            port=TEST_DEVICE_PORT,
            name='Catraca Teste E2E'
        )
        
        # Criar config para enviar
        config = system_config_factory(
            device=device,
            name='Teste E2E Atualizado'
        )
        
        # Executar update real
        mixin = SystemConfigSyncMixin()
        mixin.set_device(device)
        result = mixin.update_system_config_in_catraca(config)
        
        # Verificar resultado
        assert result.status_code == 200, f"Failed: {result.data}"
        
        print(f"\n✓ SystemConfig enviado para catraca com sucesso")


@pytest.mark.e2e
@pytest.mark.slow
@skip_if_no_test_device
@pytest.mark.django_db
class TestCatraConfigE2E:
    """Testes E2E para CatraConfig com catraca real."""
    
    def test_real_sync_from_catraca(self, device_factory):
        """Deve sincronizar CatraConfig de uma catraca real."""
        from src.core.control_id_config.infra.control_id_config_django_app.mixins import CatraConfigSyncMixin
        from src.core.control_id_config.infra.control_id_config_django_app.models import CatraConfig
        
        device = device_factory(
            ip=TEST_DEVICE_IP,
            port=TEST_DEVICE_PORT
        )
        
        mixin = CatraConfigSyncMixin()
        mixin.set_device(device)
        result = mixin.sync_catra_config_from_catraca()
        
        assert result.status_code == 200, f"Failed: {result.data}"
        
        config = CatraConfig.objects.get(device=device)
        assert config.gateway is not None
        assert config.operation_mode is not None
        
        print(f"\n✓ CatraConfig sincronizado da catraca:")
        print(f"  Gateway: {config.gateway}")
        print(f"  Operation Mode: {config.operation_mode}")
        print(f"  Anti-passback: {config.anti_passback}")
        print(f"  Daily Reset: {config.daily_reset}")
    
    def test_real_update_to_catraca(self, device_factory, catra_config_factory):
        """Deve enviar CatraConfig para uma catraca real."""
        from src.core.control_id_config.infra.control_id_config_django_app.mixins import CatraConfigSyncMixin
        
        device = device_factory(
            ip=TEST_DEVICE_IP,
            port=TEST_DEVICE_PORT
        )
        
        config = catra_config_factory(
            device=device,
            anti_passback=True,
            gateway='clockwise',
            operation_mode='blocked'
        )
        
        mixin = CatraConfigSyncMixin()
        mixin.set_device(device)
        result = mixin.update_catra_config_in_catraca(config)
        
        assert result.status_code == 200, f"Failed: {result.data}"
        
        print(f"\n✓ CatraConfig enviado para catraca com sucesso")
    
    def test_real_roundtrip_sync(self, device_factory):
        """Deve fazer sync completo: enviar e receber da catraca."""
        from src.core.control_id_config.infra.control_id_config_django_app.mixins import CatraConfigSyncMixin
        from src.core.control_id_config.infra.control_id_config_django_app.models import CatraConfig
        
        device = device_factory(
            ip=TEST_DEVICE_IP,
            port=TEST_DEVICE_PORT
        )
        
        mixin = CatraConfigSyncMixin()
        mixin.set_device(device)
        
        # 1. Buscar config atual
        result1 = mixin.sync_catra_config_from_catraca()
        assert result1.status_code == 200
        
        original_config = CatraConfig.objects.get(device=device)
        original_gateway = original_config.gateway
        
        # 2. Mudar valor
        new_gateway = 'anticlockwise' if original_gateway == 'clockwise' else 'clockwise'
        original_config.gateway = new_gateway
        original_config.save()
        
        # 3. Enviar para catraca
        result2 = mixin.update_catra_config_in_catraca(original_config)
        assert result2.status_code == 200
        
        # 4. Buscar novamente e verificar
        result3 = mixin.sync_catra_config_from_catraca()
        assert result3.status_code == 200
        
        updated_config = CatraConfig.objects.get(device=device)
        assert updated_config.gateway == new_gateway
        
        print(f"\n✓ Roundtrip sync completo:")
        print(f"  Gateway original: {original_gateway}")
        print(f"  Gateway atualizado: {new_gateway}")
        print(f"  Gateway confirmado: {updated_config.gateway}")


@pytest.mark.e2e
@pytest.mark.slow
@skip_if_no_test_device
@pytest.mark.django_db
class TestPushServerConfigE2E:
    """Testes E2E para PushServerConfig com catraca real."""
    
    def test_real_sync_from_catraca(self, device_factory):
        """Deve sincronizar PushServerConfig de uma catraca real."""
        from src.core.control_id_config.infra.control_id_config_django_app.mixins import PushServerConfigSyncMixin
        from src.core.control_id_config.infra.control_id_config_django_app.models import PushServerConfig
        
        device = device_factory(
            ip=TEST_DEVICE_IP,
            port=TEST_DEVICE_PORT
        )
        
        mixin = PushServerConfigSyncMixin()
        mixin.set_device(device)
        result = mixin.sync_push_server_config_from_catraca()
        
        assert result.status_code == 200, f"Failed: {result.data}"
        
        config = PushServerConfig.objects.get(device=device)
        assert config.push_request_timeout is not None
        assert config.push_request_period is not None
        
        print(f"\n✓ PushServerConfig sincronizado da catraca:")
        print(f"  Timeout: {config.push_request_timeout}ms")
        print(f"  Period: {config.push_request_period}s")
        print(f"  Address: {config.push_remote_address or '(não configurado)'}")
    
    def test_real_update_to_catraca(self, device_factory, push_server_config_factory):
        """Deve enviar PushServerConfig para uma catraca real."""
        from src.core.control_id_config.infra.control_id_config_django_app.mixins import PushServerConfigSyncMixin
        
        device = device_factory(
            ip=TEST_DEVICE_IP,
            port=TEST_DEVICE_PORT
        )
        
        config = push_server_config_factory(
            device=device,
            push_request_timeout=20000,
            push_request_period=120
        )
        
        mixin = PushServerConfigSyncMixin()
        mixin.set_device(device)
        result = mixin.update_push_server_config_in_catraca(config)
        
        assert result.status_code == 200, f"Failed: {result.data}"
        
        print(f"\n✓ PushServerConfig enviado para catraca com sucesso")


@pytest.mark.e2e
@pytest.mark.slow
@skip_if_no_test_device
@pytest.mark.django_db
class TestFullSyncE2E:
    """Testes E2E para sincronização completa de todos os configs."""
    
    def test_sync_all_configs_from_real_catraca(self, device_factory):
        """Deve sincronizar TODOS os 7 tipos de config de uma catraca real."""
        from src.core.control_id_config.infra.control_id_config_django_app.mixins import (
            SystemConfigSyncMixin,
            HardwareConfigSyncMixin,
            SecurityConfigSyncMixin,
            UIConfigSyncMixin,
            MonitorConfigSyncMixin,
            CatraConfigSyncMixin,
            PushServerConfigSyncMixin
        )
        from src.core.control_id_config.infra.control_id_config_django_app.models import (
            SystemConfig,
            HardwareConfig,
            SecurityConfig,
            UIConfig,
            MonitorConfig,
            CatraConfig,
            PushServerConfig
        )
        
        device = device_factory(
            ip=TEST_DEVICE_IP,
            port=TEST_DEVICE_PORT,
            name='Catraca Full Sync E2E'
        )
        
        results = {}
        
        # Sync SystemConfig
        mixin = SystemConfigSyncMixin()
        mixin.set_device(device)
        results['system'] = mixin.sync_system_config_from_catraca()
        
        # Sync HardwareConfig
        mixin = HardwareConfigSyncMixin()
        mixin.set_device(device)
        results['hardware'] = mixin.sync_hardware_config_from_catraca()
        
        # Sync SecurityConfig
        mixin = SecurityConfigSyncMixin()
        mixin.set_device(device)
        results['security'] = mixin.sync_security_config_from_catraca()
        
        # Sync UIConfig
        mixin = UIConfigSyncMixin()
        mixin.set_device(device)
        results['ui'] = mixin.sync_ui_config_from_catraca()
        
        # Sync MonitorConfig
        mixin = MonitorConfigSyncMixin()
        mixin.set_device(device)
        results['monitor'] = mixin.sync_monitor_config_from_catraca()
        
        # Sync CatraConfig
        mixin = CatraConfigSyncMixin()
        mixin.set_device(device)
        results['catra'] = mixin.sync_catra_config_from_catraca()
        
        # Sync PushServerConfig
        mixin = PushServerConfigSyncMixin()
        mixin.set_device(device)
        results['push_server'] = mixin.sync_push_server_config_from_catraca()
        
        # Verificar que todos foram bem-sucedidos
        for config_type, result in results.items():
            assert result.status_code == 200, f"Failed to sync {config_type}: {result.data}"
        
        # Verificar que todos foram salvos no banco
        assert SystemConfig.objects.filter(device=device).exists()
        assert HardwareConfig.objects.filter(device=device).exists()
        assert SecurityConfig.objects.filter(device=device).exists()
        assert UIConfig.objects.filter(device=device).exists()
        assert MonitorConfig.objects.filter(device=device).exists()
        assert CatraConfig.objects.filter(device=device).exists()
        assert PushServerConfig.objects.filter(device=device).exists()
        
        print(f"\n✓ Todos os 7 tipos de config sincronizados com sucesso!")
        print(f"  Device: {device.name} ({device.ip}:{device.port})")
