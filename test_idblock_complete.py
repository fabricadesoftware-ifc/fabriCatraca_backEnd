"""
Script de teste para validar sync de configurações da IDBLOCK
Testa todos os campos disponíveis documentados
"""
import os
import sys
import django

# Configuração do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
django.setup()

def test_idblock_sync():
    """Testa sincronização completa com IDBLOCK"""
    from src.core.control_Id.infra.control_id_django_app.models import Device
    from src.core.control_id_config.infra.control_id_config_django_app.models import (
        SystemConfig, HardwareConfig, SecurityConfig, UIConfig
    )
    
    print("\n" + "="*80)
    print("TESTE DE SINCRONIZAÇÃO COMPLETA - IDBLOCK")
    print("="*80)
    
    # Pega o primeiro device ativo
    device = Device.objects.filter(is_active=True).first()
    if not device:
        print("❌ Nenhum device ativo encontrado")
        return
    
    print(f"\n📡 Device: {device.name} ({device.ip})")
    
    # Cria viewset mock para usar os mixins
    from rest_framework.viewsets import ModelViewSet
    from src.core.control_id_config.infra.control_id_config_django_app.mixins.system_config_mixin import SystemConfigSyncMixin
    from src.core.control_id_config.infra.control_id_config_django_app.mixins.hardware_config_mixin import HardwareConfigSyncMixin
    from src.core.control_id_config.infra.control_id_config_django_app.mixins.security_config_mixin import SecurityConfigSyncMixin
    from src.core.control_id_config.infra.control_id_config_django_app.mixins.ui_config_mixin import UIConfigSyncMixin
    
    class MockViewSet(
        SystemConfigSyncMixin,
        HardwareConfigSyncMixin,
        SecurityConfigSyncMixin,
        UIConfigSyncMixin,
        ModelViewSet
    ):
        queryset = Device.objects.all()
        
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._device = None
        
        @property
        def device(self):
            return self._device
    
    viewset = MockViewSet()
    viewset._device = device
    
    # TESTE 1: SystemConfig
    print("\n" + "-"*80)
    print("1. SystemConfig (general)")
    print("-"*80)
    response = viewset.sync_system_config_from_catraca()
    if response.status_code == 200:
        config = SystemConfig.objects.filter(device=device).first()
        if config:
            print(f"✅ SystemConfig sincronizado")
            print(f"   online: {config.online} (type: {type(config.online).__name__})")
            print(f"   catra_timeout: {config.catra_timeout}")
            print(f"   local_identification: {config.local_identification}")
            print(f"   language: {config.language}")
        else:
            print(f"❌ SystemConfig não encontrado no banco")
    else:
        print(f"❌ Erro ao sincronizar: {response.status_code}")
        print(f"   {response.data}")
    
    # TESTE 2: HardwareConfig
    print("\n" + "-"*80)
    print("2. HardwareConfig (general + alarm)")
    print("-"*80)
    response = viewset.sync_hardware_config_from_catraca()
    if response.status_code == 200:
        config = HardwareConfig.objects.filter(device=device).first()
        if config:
            print(f"✅ HardwareConfig sincronizado")
            print(f"   beep_enabled: {config.beep_enabled} (type: {type(config.beep_enabled).__name__})")
            print(f"   bell_enabled: {config.bell_enabled}")
            print(f"   bell_relay: {config.bell_relay}")
            print(f"   exception_mode: {config.exception_mode}")
        else:
            print(f"❌ HardwareConfig não encontrado no banco")
    else:
        print(f"❌ Erro ao sincronizar: {response.status_code}")
        print(f"   {response.data}")
    
    # TESTE 3: SecurityConfig
    print("\n" + "-"*80)
    print("3. SecurityConfig (identifier)")
    print("-"*80)
    response = viewset.sync_security_config_from_catraca()
    if response.status_code == 200:
        config = SecurityConfig.objects.filter(device=device).first()
        if config:
            print(f"✅ SecurityConfig sincronizado")
            print(f"   (IDBLOCK não tem password_only/hide_password_only - usando defaults)")
        else:
            print(f"❌ SecurityConfig não encontrado no banco")
    else:
        print(f"❌ Erro ao sincronizar: {response.status_code}")
        print(f"   {response.data}")
    
    # TESTE 4: UIConfig
    print("\n" + "-"*80)
    print("4. UIConfig")
    print("-"*80)
    response = viewset.sync_ui_config_from_catraca()
    if response.status_code == 200:
        config = UIConfig.objects.filter(device=device).first()
        if config:
            print(f"✅ UIConfig sincronizado")
            print(f"   (IDBLOCK não tem screen_always_on - usando default)")
        else:
            print(f"❌ UIConfig não encontrado no banco")
    else:
        print(f"❌ Erro ao sincronizar: {response.status_code}")
        print(f"   {response.data}")
    
    # RESUMO FINAL
    print("\n" + "="*80)
    print("RESUMO - CAMPOS DISPONÍVEIS NA IDBLOCK")
    print("="*80)
    print("""
SEÇÕES DISPONÍVEIS:
✅ general: online, beep_enabled, bell_enabled, bell_relay, catra_timeout,
           local_identification, exception_mode, language, 
           daylight_savings_time_start, daylight_savings_time_end, auto_reboot
✅ alarm: siren_enabled, siren_relay  
✅ identifier: verbose_logging, log_type, multi_factor_authentication
✅ bio_id: similarity_threshold_1ton
✅ online_client: server_id, extract_template, max_request_attempts
✅ catra: anti_passback, daily_reset, gateway, operation_mode
✅ bio_module: var_min
✅ monitor: path, hostname, port, request_timeout
✅ push_server: push_request_timeout, push_request_period, push_remote_address
✅ w_in0/w_in1: byte_order

CAMPOS NÃO DISPONÍVEIS (não existem na IDBLOCK):
❌ auto_reboot_hour, auto_reboot_minute
❌ clear_expired_users, url_reboot_enabled
❌ keep_user_image, web_server_enabled
❌ ssh_enabled, relayN_*, door_sensorN_*, doorN_*
❌ password_only, hide_password_only, password_only_tip
❌ hide_name_on_identification
❌ denied_transaction_code, send_code_when_not_identified, send_code_when_not_authorized
❌ screen_always_on
""")
    print("="*80)

if __name__ == "__main__":
    test_idblock_sync()
