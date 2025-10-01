"""
Teste individual de cada campo para ver quais existem na API
"""

import os
import sys
import django

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from src.core.control_Id.infra.control_id_django_app.models import Device
from src.core.__seedwork__.infra import ControlIDSyncMixin
import requests

device = Device.objects.filter(is_active=True).first()
mixin = ControlIDSyncMixin()
mixin.set_device(device)

print("=" * 100)
print(f"🔍 TESTE INDIVIDUAL DE CAMPOS - Device: {device.name}")
print("=" * 100)

# Lista completa para testar
fields_to_test = {
    "System Config": [
        "online", "auto_reboot", "auto_reboot_hour", "auto_reboot_minute",
        "clear_expired_users", "url_reboot_enabled", "keep_user_image",
        "catra_timeout", "local_identification", "language",
        "daylight_savings_time_start", "daylight_savings_time_end",
        "web_server_enabled",
    ],
    "Hardware Config": [
        "beep_enabled", "ssh_enabled", "relayN_enabled", "relayN_timeout",
        "relayN_auto_close", "door_sensorN_enabled", "door_sensorN_idle",
        "doorN_interlock", "bell_enabled", "bell_relay",
        "exception_mode", "doorN_exception_mode",
    ],
    "Security Config": [
        "password_only", "hide_password_only", "password_only_tip",
        "hide_name_on_identification", "denied_transaction_code",
        "send_code_when_not_identified", "send_code_when_not_authorized",
    ],
    "UI Config": [
        "screen_always_on",
    ],
}

results = {
    "available": [],
    "not_available": []
}

for category, fields in fields_to_test.items():
    print(f"\n📦 {category}:")
    print("-" * 100)
    
    for field in fields:
        try:
            sess = mixin.login()
            response = requests.post(
                mixin.get_url(f"get_configuration.fcgi?session={sess}"),
                json={"general": [field]}
            )
            
            if response.status_code == 200:
                data = response.json()
                general = data.get('general', {})
                if field in general:
                    value = general[field]
                    print(f"   ✅ {field:35} = {repr(value):20} (type: {type(value).__name__})")
                    results["available"].append((field, value, type(value).__name__))
                else:
                    print(f"   ⚠️  {field:35} - Retornou 200 mas campo não veio no response")
                    results["not_available"].append(field)
            else:
                error_msg = response.text[:80] if len(response.text) > 80 else response.text
                print(f"   ❌ {field:35} - Status {response.status_code}: {error_msg}")
                results["not_available"].append(field)
        except Exception as e:
            print(f"   ❌ {field:35} - Exceção: {str(e)[:60]}")
            results["not_available"].append(field)

print()
print("=" * 100)
print("📊 RESUMO:")
print("=" * 100)
print(f"\n✅ Campos DISPONÍVEIS na API ({len(results['available'])}):")
for field, value, vtype in results['available']:
    is_bool = value in ('0', '1') if isinstance(value, str) else False
    needs_to_bool = "🔧 PRECISA to_bool()" if is_bool else ""
    print(f"   • {field:35} = {repr(value):20} ({vtype}) {needs_to_bool}")

print(f"\n❌ Campos NÃO DISPONÍVEIS na API ({len(results['not_available'])}):")
for field in results['not_available']:
    print(f"   • {field}")

print()
print("=" * 100)
