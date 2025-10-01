"""
Teste manual para verificar conversão de strings booleanas da API Control iD
Simula o comportamento real de leitura da API e conversão para boolean
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


def test_api_response_simulation():
    """Simula respostas da API Control iD"""
    
    # Simulando resposta da API como ela realmente vem
    api_response = {
        "general": {
            "online": "0",  # String "0" = False
            "beep_enabled": "1",  # String "1" = True
            "clear_expired_users": "0",
            "url_reboot_enabled": "1",
            "keep_user_image": "1",
            "local_identification": "1",
            "web_server_enabled": "0",
            "ssh_enabled": "0",
            "relayN_enabled": "1",
            "password_only": "0",
            "screen_always_on": "0"
        }
    }
    
    config_data = api_response.get('general', {})
    
    print("=" * 80)
    print("TESTE DE CONVERSÃO DE BOOLEANOS DA API CONTROL iD")
    print("=" * 80)
    print()
    
    # Teste 1: Conversão SEM to_bool() (BUG)
    print("❌ PROBLEMA: Conversão DIRETA (como estava antes)")
    print("-" * 80)
    
    online_direto = config_data.get('online', True)
    beep_direto = config_data.get('beep_enabled', True)
    ssh_direto = config_data.get('ssh_enabled', False)
    
    print(f"online = config_data.get('online', True)")
    print(f"  Valor da API: '{config_data.get('online')}' (string)")
    print(f"  Resultado: {online_direto} (type: {type(online_direto).__name__})")
    print(f"  Python avalia string '0' como: {bool('0')} ⚠️  ERRADO!")
    print()
    
    print(f"beep_enabled = config_data.get('beep_enabled', True)")
    print(f"  Valor da API: '{config_data.get('beep_enabled')}' (string)")
    print(f"  Resultado: {beep_direto} (type: {type(beep_direto).__name__})")
    print(f"  Python avalia string '1' como: {bool('1')} ✓")
    print()
    
    print(f"ssh_enabled = config_data.get('ssh_enabled', False)")
    print(f"  Valor da API: '{config_data.get('ssh_enabled')}' (string)")
    print(f"  Resultado: {ssh_direto} (type: {type(ssh_direto).__name__})")
    print(f"  Python avalia string '0' como: {bool('0')} ⚠️  ERRADO!")
    print()
    print()
    
    # Teste 2: Conversão COM to_bool() (CORRETO)
    print("✅ SOLUÇÃO: Conversão com to_bool()")
    print("-" * 80)
    
    online_correto = to_bool(config_data.get('online'), True)
    beep_correto = to_bool(config_data.get('beep_enabled'), True)
    ssh_correto = to_bool(config_data.get('ssh_enabled'), False)
    screen_correto = to_bool(config_data.get('screen_always_on'), False)
    
    print(f"online = to_bool(config_data.get('online'), True)")
    print(f"  Valor da API: '{config_data.get('online')}' (string)")
    print(f"  Resultado: {online_correto} (type: {type(online_correto).__name__})")
    print(f"  to_bool() converte '0' para: {online_correto} ✓ CORRETO!")
    print()
    
    print(f"beep_enabled = to_bool(config_data.get('beep_enabled'), True)")
    print(f"  Valor da API: '{config_data.get('beep_enabled')}' (string)")
    print(f"  Resultado: {beep_correto} (type: {type(beep_correto).__name__})")
    print(f"  to_bool() converte '1' para: {beep_correto} ✓ CORRETO!")
    print()
    
    print(f"ssh_enabled = to_bool(config_data.get('ssh_enabled'), False)")
    print(f"  Valor da API: '{config_data.get('ssh_enabled')}' (string)")
    print(f"  Resultado: {ssh_correto} (type: {type(ssh_correto).__name__})")
    print(f"  to_bool() converte '0' para: {ssh_correto} ✓ CORRETO!")
    print()
    
    print(f"screen_always_on = to_bool(config_data.get('screen_always_on'), False)")
    print(f"  Valor da API: '{config_data.get('screen_always_on')}' (string)")
    print(f"  Resultado: {screen_correto} (type: {type(screen_correto).__name__})")
    print(f"  to_bool() converte '0' para: {screen_correto} ✓ CORRETO!")
    print()
    print()
    
    # Teste 3: Casos especiais
    print("🔬 CASOS ESPECIAIS")
    print("-" * 80)
    
    test_cases = [
        ("String '0'", "0", False),
        ("String '1'", "1", True),
        ("String 'true'", "true", True),
        ("String 'True'", "True", True),
        ("String 'false'", "false", False),
        ("String 'False'", "False", False),
        ("String vazia", "", False),
        ("None", None, False),
        ("Boolean True", True, True),
        ("Boolean False", False, False),
        ("Integer 0", 0, False),
        ("Integer 1", 1, True),
    ]
    
    for desc, value, expected in test_cases:
        result = to_bool(value, False)
        status = "✓" if result == expected else "✗"
        print(f"{status} {desc:20} -> to_bool({repr(value):10}) = {result:5} (esperado: {expected})")
    
    print()
    print()
    
    # Teste 4: Comparação antes x depois
    print("📊 COMPARAÇÃO: ANTES vs DEPOIS")
    print("-" * 80)
    
    campos_teste = [
        ('online', True),
        ('beep_enabled', True),
        ('ssh_enabled', False),
        ('clear_expired_users', False),
        ('url_reboot_enabled', True),
        ('password_only', False),
        ('screen_always_on', False),
    ]
    
    print(f"{'Campo':<25} {'API':<8} {'SEM to_bool':<15} {'COM to_bool':<15} {'Status'}")
    print("-" * 80)
    
    for campo, default in campos_teste:
        api_value = config_data.get(campo, '')
        sem_conversao = config_data.get(campo, default)
        com_conversao = to_bool(config_data.get(campo), default)
        
        # Determina se está correto
        valor_esperado = (api_value == "1")
        correto_sem = (sem_conversao == valor_esperado)
        correto_com = (com_conversao == valor_esperado)
        
        status = "✓ CORRIGIDO!" if (not correto_sem and correto_com) else ("✓ OK" if correto_com else "✗ ERRO")
        
        print(f"{campo:<25} {api_value!r:<8} {str(sem_conversao):<15} {str(com_conversao):<15} {status}")
    
    print()
    print("=" * 80)
    print("CONCLUSÃO:")
    print("  • API Control iD retorna strings: '0' = False, '1' = True")
    print("  • Python bool('0') = True (PROBLEMA!)")
    print("  • Solução: usar to_bool() que verifica se string é '1'")
    print("=" * 80)


if __name__ == "__main__":
    test_api_response_simulation()
