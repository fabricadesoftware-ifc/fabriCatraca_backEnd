"""
Teste simplificado para verificar se to_bool() retorna bool correto
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


# Simulando API response
config_data = {
    "online": "0",
    "beep_enabled": "1"
}

print("="*60)
print("TESTE: Verificar tipo de retorno de to_bool()")
print("="*60)

online_value = config_data.get("online")
online_result = to_bool(online_value, True)

print(f"\n1. config_data.get('online') = {repr(online_value)}")
print(f"   type: {type(online_value)}")
print(f"   to_bool('{online_value}', True) = {online_result}")
print(f"   type: {type(online_result)}")
print(f"   É bool? {isinstance(online_result, bool)}")
print(f"   Valor: {'False' if online_result is False else 'True' if online_result is True else online_result}")

beep_value = config_data.get("beep_enabled")
beep_result = to_bool(beep_value, True)

print(f"\n2. config_data.get('beep_enabled') = {repr(beep_value)}")
print(f"   type: {type(beep_value)}")
print(f"   to_bool('{beep_value}', True) = {beep_result}")
print(f"   type: {type(beep_result)}")
print(f"   É bool? {isinstance(beep_result, bool)}")
print(f"   Valor: {'False' if beep_result is False else 'True' if beep_result is True else beep_result}")

print("\n" + "="*60)
print("VERIFICAÇÃO FINAL:")
print("="*60)

# Teste direto
assert to_bool("0", True) == False, "String '0' deve retornar False"
assert to_bool("1", True) == True, "String '1' deve retornar True"
assert isinstance(to_bool("0", True), bool), "Deve retornar tipo bool"
assert isinstance(to_bool("1", True), bool), "Deve retornar tipo bool"

print("✓ to_bool('0') retorna False (bool)")
print("✓ to_bool('1') retorna True (bool)")
print("✓ Todos os retornos são do tipo bool")
print("\n✅ SUCESSO! A função to_bool() funciona corretamente!")
