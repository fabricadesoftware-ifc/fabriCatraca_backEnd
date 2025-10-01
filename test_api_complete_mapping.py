"""
Script para verificar TODOS os campos retornados pela API vs campos esperados nos models
"""

import os
import sys
import django

# Configura Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from src.core.control_Id.infra.control_id_django_app.models import Device
from src.core.__seedwork__.infra import ControlIDSyncMixin
import requests

# Pega o primeiro device ativo
device = Device.objects.filter(is_active=True).first()

if not device:
    print("❌ Nenhum device ativo encontrado!")
    sys.exit(1)

print("=" * 100)
print(f"🔍 DIAGNÓSTICO COMPLETO - Device: {device.name}")
print("=" * 100)
print()

# Cria mixin e faz login
mixin = ControlIDSyncMixin()
mixin.set_device(device)

# Testa diferentes payloads para ver o que a API retorna
payloads_to_test = [
    ("Payload vazio", {"general": []}),
    ("Payload com campos específicos do SystemConfig", {
        "general": [
            "online", "auto_reboot_hour", "auto_reboot_minute", 
            "clear_expired_users", "url_reboot_enabled", "catra_timeout",
            "local_identification", "language", "daylight_savings_time_start",
            "daylight_savings_time_end", "web_server_enabled"
        ]
    }),
    ("Payload com auto_reboot (composto)", {
        "general": ["auto_reboot"]
    }),
]

print("📡 TESTANDO DIFERENTES PAYLOADS:")
print("-" * 100)

for desc, payload in payloads_to_test:
    print(f"\n🔹 {desc}")
    print(f"   Payload: {payload}")
    
    try:
        sess = mixin.login()
        response = requests.post(
            mixin.get_url(f"get_configuration.fcgi?session={sess}"),
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            general = data.get('general', {})
            print(f"   ✅ Status 200")
            print(f"   Campos retornados: {list(general.keys())}")
            if general:
                print(f"   Valores:")
                for key, value in general.items():
                    print(f"      {key}: {repr(value)} (type: {type(value).__name__})")
        else:
            print(f"   ❌ Status {response.status_code}")
            print(f"   Erro: {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Exceção: {str(e)}")

print()
print("=" * 100)
print("📋 MAPEAMENTO DE CAMPOS DO DJANGO MODEL:")
print("=" * 100)

from src.core.control_id_config.infra.control_id_config_django_app.models import (
    SystemConfig, HardwareConfig, SecurityConfig, UIConfig
)

print("\n🔹 SystemConfig - Campos esperados:")
system_fields = [f.name for f in SystemConfig._meta.get_fields() if f.name not in ['id', 'device', 'device_name']]
print(f"   {system_fields}")

print("\n🔹 HardwareConfig - Campos esperados:")
hardware_fields = [f.name for f in HardwareConfig._meta.get_fields() if f.name not in ['id', 'device', 'device_name']]
print(f"   {hardware_fields}")

print("\n🔹 SecurityConfig - Campos esperados:")
security_fields = [f.name for f in SecurityConfig._meta.get_fields() if f.name not in ['id', 'device', 'device_name']]
print(f"   {security_fields}")

print("\n🔹 UIConfig - Campos esperados:")
ui_fields = [f.name for f in UIConfig._meta.get_fields() if f.name not in ['id', 'device', 'device_name']]
print(f"   {ui_fields}")

print()
print("=" * 100)
print("🔍 ANÁLISE: Tentando obter TODOS os campos conhecidos da API Control iD")
print("=" * 100)

# Lista completa de campos conhecidos da API Control iD
all_known_fields = [
    # System
    "online", "auto_reboot", "auto_reboot_hour", "auto_reboot_minute",
    "clear_expired_users", "url_reboot_enabled", "keep_user_image",
    "catra_timeout", "local_identification", "language",
    "daylight_savings_time_start", "daylight_savings_time_end",
    "web_server_enabled",
    # Hardware
    "beep_enabled", "ssh_enabled", "relayN_enabled", "relayN_timeout",
    "relayN_auto_close", "door_sensorN_enabled", "door_sensorN_idle",
    "doorN_interlock", "bell_enabled", "bell_relay",
    "exception_mode", "doorN_exception_mode",
    # Security
    "password_only", "hide_password_only", "password_only_tip",
    "hide_name_on_identification", "denied_transaction_code",
    "send_code_when_not_identified", "send_code_when_not_authorized",
    # UI
    "screen_always_on",
]

print(f"\n📝 Tentando obter {len(all_known_fields)} campos conhecidos...")

try:
    sess = mixin.login()
    response = requests.post(
        mixin.get_url(f"get_configuration.fcgi?session={sess}"),
        json={"general": all_known_fields}
    )
    
    if response.status_code == 200:
        data = response.json()
        general = data.get('general', {})
        print(f"\n✅ Sucesso! API retornou {len(general)} campos:")
        print()
        
        # Organizar por categoria
        system_returned = {}
        hardware_returned = {}
        security_returned = {}
        ui_returned = {}
        unknown_returned = {}
        
        for key, value in general.items():
            if key in ['online', 'auto_reboot', 'auto_reboot_hour', 'auto_reboot_minute',
                      'clear_expired_users', 'url_reboot_enabled', 'keep_user_image',
                      'catra_timeout', 'local_identification', 'language',
                      'daylight_savings_time_start', 'daylight_savings_time_end',
                      'web_server_enabled']:
                system_returned[key] = value
            elif key in ['beep_enabled', 'ssh_enabled', 'relayN_enabled', 'relayN_timeout',
                        'relayN_auto_close', 'door_sensorN_enabled', 'door_sensorN_idle',
                        'doorN_interlock', 'bell_enabled', 'bell_relay',
                        'exception_mode', 'doorN_exception_mode']:
                hardware_returned[key] = value
            elif key in ['password_only', 'hide_password_only', 'password_only_tip',
                        'hide_name_on_identification', 'denied_transaction_code',
                        'send_code_when_not_identified', 'send_code_when_not_authorized']:
                security_returned[key] = value
            elif key in ['screen_always_on']:
                ui_returned[key] = value
            else:
                unknown_returned[key] = value
        
        print("🔹 SYSTEM CONFIG:")
        for k, v in system_returned.items():
            print(f"   ✓ {k}: {repr(v)}")
        
        print("\n🔹 HARDWARE CONFIG:")
        for k, v in hardware_returned.items():
            print(f"   ✓ {k}: {repr(v)}")
        
        print("\n🔹 SECURITY CONFIG:")
        for k, v in security_returned.items():
            print(f"   ✓ {k}: {repr(v)}")
        
        print("\n🔹 UI CONFIG:")
        for k, v in ui_returned.items():
            print(f"   ✓ {k}: {repr(v)}")
        
        if unknown_returned:
            print("\n🔹 CAMPOS DESCONHECIDOS:")
            for k, v in unknown_returned.items():
                print(f"   ? {k}: {repr(v)}")
        
        # Campos que pedimos mas não vieram
        print("\n⚠️  CAMPOS SOLICITADOS MAS NÃO RETORNADOS:")
        returned_keys = set(general.keys())
        requested_keys = set(all_known_fields)
        missing = requested_keys - returned_keys
        for key in sorted(missing):
            print(f"   ✗ {key}")
    else:
        print(f"❌ Status {response.status_code}")
        print(f"Erro: {response.text}")
except Exception as e:
    print(f"❌ Exceção: {str(e)}")
    import traceback
    traceback.print_exc()

print()
print("=" * 100)
