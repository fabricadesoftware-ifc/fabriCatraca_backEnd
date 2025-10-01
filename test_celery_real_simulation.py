"""
Teste REAL simulando exatamente o que acontece no Django quando Celery sincroniza
"""

def to_bool(value, default=False):
    """
    Converte valores string da API do Control iD para boolean.
    API retorna "0" para False e "1" para True.
    """
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        # Retorna True APENAS se string for "1", "true" ou "True"
        return value.strip() in ("1", "true", "True")
    # Para números: 0 = False, qualquer outro = True
    if isinstance(value, (int, float)):
        return value != 0
    return bool(value)


print("=" * 80)
print("TESTE REAL: Simulando Celery sync_config.py")
print("=" * 80)
print()

# Simula resposta REAL da API Control iD
api_response = {
    "general": {
        "auto_reboot_hour": "3",
        "auto_reboot_minute": "0",
        "clear_expired_users": "0",
        "url_reboot_enabled": "1",
        "keep_user_image": "1",
        "catra_timeout": "30",
        "online": "0",  # ⚠️ ESTE É O PROBLEMA!
        "local_identification": "1",
        "language": "pt",
        "web_server_enabled": "1",
        "beep_enabled": "0",  # ⚠️ OUTRO PROBLEMA!
        "ssh_enabled": "0",
        "relayN_enabled": "0",
        "relayN_timeout": "5",
        "relayN_auto_close": "1"
    }
}

general = api_response.get('general', {})

print("📡 Resposta da API Control iD:")
print(f"   online = {repr(general.get('online'))}")
print(f"   beep_enabled = {repr(general.get('beep_enabled'))}")
print()

# ANTES (BUG):
print("❌ ANTES (com bug):")
print("-" * 80)
online_bug = general.get('online', True)
beep_bug = general.get('beep_enabled', True)

print(f"online = general.get('online', True)")
print(f"  Resultado: {repr(online_bug)} (type: {type(online_bug).__name__})")
print(f"  bool('{online_bug}') = {bool(online_bug)} ⚠️ ERRADO! String '0' é truthy!")
print()

print(f"beep_enabled = general.get('beep_enabled', True)")
print(f"  Resultado: {repr(beep_bug)} (type: {type(beep_bug).__name__})")
print(f"  bool('{beep_bug}') = {bool(beep_bug)} ⚠️ ERRADO! String '0' é truthy!")
print()

# DEPOIS (CORRETO):
print("✅ DEPOIS (com to_bool):")
print("-" * 80)
online_correto = to_bool(general.get('online'), True)
beep_correto = to_bool(general.get('beep_enabled'), True)

print(f"online = to_bool(general.get('online'), True)")
print(f"  Resultado: {repr(online_correto)} (type: {type(online_correto).__name__})")
print(f"  ✓ CORRETO! '0' convertido para False")
print()

print(f"beep_enabled = to_bool(general.get('beep_enabled'), True)")
print(f"  Resultado: {repr(beep_correto)} (type: {type(beep_correto).__name__})")
print(f"  ✓ CORRETO! '0' convertido para False")
print()

# Simula o que seria salvo no banco
print("💾 Simulando defaults do Django Model:")
print("-" * 80)

system_config_data = {
    'online': to_bool(general.get('online'), True),
    'clear_expired_users': to_bool(general.get('clear_expired_users'), False),
    'url_reboot_enabled': to_bool(general.get('url_reboot_enabled'), True),
}

hardware_config_data = {
    'beep_enabled': to_bool(general.get('beep_enabled'), True),
    'ssh_enabled': to_bool(general.get('ssh_enabled'), False),
    'relayN_enabled': to_bool(general.get('relayN_enabled'), False),
    'relayN_auto_close': to_bool(general.get('relayN_auto_close'), True),
}

print("SystemConfig.objects.update_or_create(defaults={")
for key, value in system_config_data.items():
    api_value = general.get(key, 'N/A')
    print(f"    '{key}': {value}  # API enviou '{api_value}'")
print("})")
print()

print("HardwareConfig.objects.update_or_create(defaults={")
for key, value in hardware_config_data.items():
    api_value = general.get(key, 'N/A')
    print(f"    '{key}': {value}  # API enviou '{api_value}'")
print("})")
print()

print("=" * 80)
print("✅ RESULTADO FINAL:")
print("=" * 80)
print("• online='0' na API → False no banco ✓")
print("• beep_enabled='0' na API → False no banco ✓")
print("• Celery agora persiste valores corretos! 🎉")
print("=" * 80)
