# CORREÇÃO COMPLETA - Sincronização de Configurações IDBLOCK

## 📋 Problema Original
**Sintoma**: Valores boolean persistindo como `True` quando setados para `False` via API.

**Exemplo**: 
```python
# Setar online = False via API
POST /api/system-config/
{"online": false}

# Ao ler do banco após sincronização Celery
GET /api/system-config/
{"online": true}  # ❌ Reverteu para True!
```

## 🔍 Causa Raiz
A catraca **IDBLOCK** possui um conjunto **diferente** de campos disponíveis comparada à documentação genérica da Control iD. Estávamos solicitando campos que não existem neste modelo específico, resultando em:

1. **API retornando `{}`** (vazio) quando campos inexistentes eram solicitados
2. **Código usando valores padrão** em vez dos valores reais da catraca
3. **Boolean conversion incorreta**: `bool("0") = True` (Python converte string não-vazia para True)

## 📚 Documentação vs Realidade

### Campos Solicitados ANTES (❌ Incorreto)
```python
payload = {
    "general": [
        "auto_reboot_hour",         # ❌ Não existe na IDBLOCK
        "auto_reboot_minute",       # ❌ Não existe na IDBLOCK
        "clear_expired_users",      # ❌ Não existe na IDBLOCK
        "url_reboot_enabled",       # ❌ Não existe na IDBLOCK
        "ssh_enabled",              # ❌ Não existe na IDBLOCK
        ...
    ]
}
```

### Campos Disponíveis AGORA (✅ Correto)
```python
payload = {
    "general": [
        "online",                    # ✅ Existe
        "beep_enabled",              # ✅ Existe
        "bell_enabled",              # ✅ Existe
        "bell_relay",                # ✅ Existe
        "catra_timeout",             # ✅ Existe
        "local_identification",      # ✅ Existe
        "exception_mode",            # ✅ Existe
        "language",                  # ✅ Existe
        "daylight_savings_time_start",  # ✅ Existe
        "daylight_savings_time_end",    # ✅ Existe
        "auto_reboot"                # ✅ Existe
    ],
    "alarm": [
        "siren_enabled",             # ✅ Existe
        "siren_relay"                # ✅ Existe
    ],
    "identifier": [
        "verbose_logging",           # ✅ Existe
        "log_type",                  # ✅ Existe
        "multi_factor_authentication" # ✅ Existe
    ]
}
```

## 🔧 Correções Implementadas

### 1. SystemConfigSyncMixin
**Arquivo**: `src/core/control_id_config/infra/control_id_config_django_app/mixins/system_config_mixin.py`

**Mudanças**:
- ✅ Solicita apenas campos disponíveis em `general`
- ✅ Define valores padrão fixos para campos inexistentes
- ✅ Conversão correta: `"0"` → `False`, `"1"` → `True`

**Antes**:
```python
payload = {"general": ["auto_reboot_hour", "clear_expired_users", ...]}  # ❌ Campos inexistentes
```

**Depois**:
```python
payload = {
    "general": [
        "online", "auto_reboot", "catra_timeout",
        "local_identification", "exception_mode", "language",
        "daylight_savings_time_start", "daylight_savings_time_end"
    ]
}

defaults={
    # Campos DISPONÍVEIS
    'online': to_bool(config_data.get('online'), True),
    'catra_timeout': int(str(config_data.get('catra_timeout', 30)) or 30),
    # Campos NÃO DISPONÍVEIS (valores fixos)
    'auto_reboot_hour': 3,
    'auto_reboot_minute': 0,
    'clear_expired_users': False,
    'url_reboot_enabled': True,
    'keep_user_image': True,
    'web_server_enabled': True
}
```

### 2. HardwareConfigSyncMixin
**Arquivo**: `src/core/control_id_config/infra/control_id_config_django_app/mixins/hardware_config_mixin.py`

**Mudanças**:
- ✅ Solicita campos de `general` + `alarm`
- ✅ Trata `exception_mode`: `"none"` = False, outros = True
- ✅ Define defaults para relays/doors inexistentes

**Antes**:
```python
payload = {"general": ["ssh_enabled", "relayN_enabled", ...]}  # ❌ Campos inexistentes
```

**Depois**:
```python
payload = {
    "general": ["beep_enabled", "bell_enabled", "bell_relay", "exception_mode"],
    "alarm": ["siren_enabled", "siren_relay"]
}

exception_mode_enabled = exception_mode_value not in ['', 'none', '0', 0, False]

defaults={
    # Campos DISPONÍVEIS
    'beep_enabled': to_bool(config_data.get('beep_enabled'), True),
    'bell_enabled': to_bool(config_data.get('bell_enabled'), False),
    'exception_mode': exception_mode_enabled,
    # Campos NÃO DISPONÍVEIS (valores fixos)
    'ssh_enabled': False,
    'relayN_enabled': False,
    'door_sensorN_enabled': False,
    ...
}
```

### 3. SecurityConfigSyncMixin
**Arquivo**: `src/core/control_id_config/infra/control_id_config_django_app/mixins/security_config_mixin.py`

**Mudanças**:
- ✅ Solicita campos de `identifier` (não `general`)
- ✅ Define todos os campos como valores fixos (IDBLOCK não tem password_only, etc)

**Antes**:
```python
payload = {"general": ["password_only", "hide_password_only", ...]}  # ❌ Campos inexistentes
config_data = full_response.get('general', {})  # ❌ Seção errada
```

**Depois**:
```python
payload = {
    "identifier": [
        "verbose_logging",
        "log_type",
        "multi_factor_authentication"
    ]
}

# Todos os campos do SecurityConfig não existem na IDBLOCK - usar defaults fixos
defaults={
    'password_only': False,
    'hide_password_only': False,
    'password_only_tip': '',
    'hide_name_on_identification': False,
    'denied_transaction_code': '',
    'send_code_when_not_identified': False,
    'send_code_when_not_authorized': False
}
```

### 4. UIConfigSyncMixin
**Arquivo**: `src/core/control_id_config/infra/control_id_config_django_app/mixins/ui_config_mixin.py`

**Status**: Já estava correto - IDBLOCK não tem campos de UI.

## 📊 Resultado Final

### Teste de Sincronização Completa
```bash
$ python test_idblock_complete.py

================================================================================
TESTE DE SINCRONIZAÇÃO COMPLETA - IDBLOCK
================================================================================

📡 Device: Fabrica (localhost:8080)

--------------------------------------------------------------------------------
1. SystemConfig (general)
--------------------------------------------------------------------------------
✅ SystemConfig sincronizado
   online: False (type: bool)  ✅ CORRETO! Agora respeita valor real da catraca
   catra_timeout: 30
   local_identification: True
   language: pt

--------------------------------------------------------------------------------
2. HardwareConfig (general + alarm)
--------------------------------------------------------------------------------
✅ HardwareConfig sincronizado
   beep_enabled: False (type: bool)  ✅ CORRETO!
   bell_enabled: False
   bell_relay: 1
   exception_mode: False

--------------------------------------------------------------------------------
3. SecurityConfig (identifier)
--------------------------------------------------------------------------------
✅ SecurityConfig sincronizado
   (IDBLOCK não tem password_only/hide_password_only - usando defaults)

--------------------------------------------------------------------------------
4. UIConfig
--------------------------------------------------------------------------------
✅ UIConfig sincronizado
   (IDBLOCK não tem screen_always_on - usando default)
```

## 📝 Mapeamento Completo IDBLOCK

### ✅ Campos Disponíveis (22 campos em 10 seções)

#### general (11 campos)
- `online` → "0"/"1"
- `beep_enabled` → "0"/"1"
- `bell_enabled` → "0"/"1"
- `bell_relay` → "1"
- `catra_timeout` → "30"
- `local_identification` → "1"
- `exception_mode` → "none"/"emergency"/"lock_down"
- `language` → "pt"/"pt_BR"/"en_US"/"spa_SPA"
- `daylight_savings_time_start` → timestamp ou ""
- `daylight_savings_time_end` → timestamp ou ""
- `auto_reboot` → "1"

#### alarm (2 campos)
- `siren_enabled` → "0"/"1"
- `siren_relay` → "1"

#### identifier (3 campos)
- `verbose_logging` → "1"
- `log_type` → "0"
- `multi_factor_authentication` → "0"

#### bio_id (1 campo)
- `similarity_threshold_1ton` → "0"

#### online_client (3 campos)
- `server_id` → "5"
- `extract_template` → "1"
- `max_request_attempts` → "5"

#### catra (4 campos)
- `anti_passback` → "0"
- `daily_reset` → "0"
- `gateway` → "clockwise"/"anticlockwise"
- `operation_mode` → "blocked"/"entrance_open"/"exit_open"/"both_open"

#### bio_module (1 campo)
- `var_min` → "1000"

#### monitor (4 campos)
- `path` → "api/notifications"
- `hostname` → "catracaapi.dev..."
- `port` → ""
- `request_timeout` → "1000"

#### push_server (3 campos)
- `push_request_timeout` → "15000"
- `push_request_period` → "60"
- `push_remote_address` → ""

#### w_in0/w_in1 (1 campo cada)
- `byte_order` → ""

### ❌ Campos NÃO Disponíveis (11 campos)
Estes campos **não existem** na API da IDBLOCK e devem usar valores fixos padrão:

- `auto_reboot_hour` → fixo: 3
- `auto_reboot_minute` → fixo: 0
- `clear_expired_users` → fixo: False
- `url_reboot_enabled` → fixo: True
- `keep_user_image` → fixo: True
- `web_server_enabled` → fixo: True
- `ssh_enabled` → fixo: False
- `relayN_*` (enabled/timeout/auto_close) → fixos: False/5/True
- `door_sensorN_*` (enabled/idle) → fixos: False/10
- `doorN_*` (interlock/exception_mode) → fixos: False
- `password_only` → fixo: False
- `hide_password_only` → fixo: False
- `password_only_tip` → fixo: ""
- `hide_name_on_identification` → fixo: False
- `denied_transaction_code` → fixo: ""
- `send_code_when_not_identified` → fixo: False
- `send_code_when_not_authorized` → fixo: False
- `screen_always_on` → fixo: False

## 🎯 Conversões de Tipo

### Boolean Simples ("0"/"1")
```python
def to_bool(v, default=False):
    if isinstance(v, str):
        return v.strip() in ("1", "true", "True")
    return bool(v)

# Exemplos:
to_bool("0") → False  ✅
to_bool("1") → True   ✅
to_bool("") → False   ✅
```

### Valores Especiais
```python
# exception_mode
exception_mode = "none"         → False
exception_mode = "emergency"    → True
exception_mode = "lock_down"    → True

# gateway
gateway = "clockwise"           → string (não é boolean)
gateway = "anticlockwise"       → string (não é boolean)

# operation_mode
operation_mode = "blocked"            → string
operation_mode = "entrance_open"      → string
operation_mode = "exit_open"          → string
operation_mode = "both_open"          → string
```

## 📦 Arquivos Modificados

1. ✅ `system_config_mixin.py` - SystemConfigSyncMixin
2. ✅ `hardware_config_mixin.py` - HardwareConfigSyncMixin
3. ✅ `security_config_mixin.py` - SecurityConfigSyncMixin
4. ✅ `ui_config_mixin.py` - UIConfigSyncMixin (sem mudanças necessárias)

## 📄 Arquivos de Referência Criados

1. ✅ `MAPEAMENTO_API_IDBLOCK.md` - Documentação completa dos campos
2. ✅ `test_idblock_complete.py` - Teste de sincronização end-to-end

## ✅ Validação Final

### Antes da Correção
```
❌ online: True (deveria ser False)
❌ clear_expired_users: True (deveria ser False)
❌ API retornando {} (vazio)
```

### Depois da Correção
```
✅ online: False (type: bool) - CORRETO!
✅ beep_enabled: False (type: bool) - CORRETO!
✅ bell_enabled: False (type: bool) - CORRETO!
✅ exception_mode: False - CORRETO! ("none" convertido corretamente)
✅ API retornando dados reais da catraca
✅ Conversão de strings "0"/"1" funcionando perfeitamente
```

## 🚀 Próximos Passos

1. ✅ **COMPLETO**: Atualizar todos os mixins com campos corretos da IDBLOCK
2. ✅ **COMPLETO**: Implementar conversão correta de boolean strings
3. ✅ **COMPLETO**: Definir valores padrão para campos inexistentes
4. ✅ **COMPLETO**: Validar com teste end-to-end
5. ⏭️ **OPCIONAL**: Implementar sync de outras seções (catra, monitor, push_server, etc) se necessário

## 📞 Suporte

Caso encontre novos problemas:
1. Verifique o arquivo `MAPEAMENTO_API_IDBLOCK.md` para confirmar campos disponíveis
2. Execute `python test_idblock_complete.py` para validar sincronização
3. Verifique logs do Celery: `[SYSTEM_CONFIG_SYNC]`, `[HARDWARE_CONFIG_SYNC]`, etc.

---

**Data**: 30/09/2025  
**Status**: ✅ COMPLETO - Todos os mixins atualizados e validados  
**Modelo**: Control iD IDBLOCK  
**Versão API**: HTTP API (get_configuration.fcgi / set_configuration.fcgi)
