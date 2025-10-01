"""
MAPEAMENTO COMPLETO DOS CAMPOS DA API CONTROL ID (IDBLOCK)
Baseado na documentação oficial e resposta real da API

=============================================================================
CAMPOS DISPONÍVEIS POR SEÇÃO:
=============================================================================

GENERAL (Configurações Gerais):
✅ online                         - "0"/"1" → bool
✅ beep_enabled                   - "0"/"1" → bool  
✅ bell_enabled                   - "0"/"1" → bool
✅ bell_relay                     - "1" → int
✅ catra_timeout                  - "30" → int (ms)
✅ local_identification           - "1" → bool ("0"/"1")
✅ exception_mode                 - "none"/"emergency"/"lock_down" → string/bool
✅ language                       - "pt"/"pt_BR"/"en_US"/"spa_SPA" → string
✅ daylight_savings_time_start    - "" → timestamp or null
✅ daylight_savings_time_end      - "" → timestamp or null
✅ auto_reboot                    - "1" → bool ("0"/"1")

❌ NÃO DISPONÍVEIS na IDBLOCK:
   - auto_reboot_hour
   - auto_reboot_minute  
   - clear_expired_users
   - url_reboot_enabled
   - keep_user_image
   - ssh_enabled
   - relayN_enabled
   - relayN_timeout
   - relayN_auto_close
   - door_sensorN_enabled
   - door_sensorN_idle
   - doorN_interlock
   - doorN_exception_mode
   - password_only
   - hide_password_only
   - password_only_tip
   - hide_name_on_identification
   - denied_transaction_code
   - send_code_when_not_identified
   - send_code_when_not_authorized
   - screen_always_on
   - web_server_enabled

ALARM (Alarme/Sirene):
✅ siren_enabled                  - "0"/"1" → bool
✅ siren_relay                    - "1" → int

IDENTIFIER (Identificador):
✅ verbose_logging                - "1" → bool ("0"/"1")
✅ log_type                       - "0" → string/int
✅ multi_factor_authentication    - "0" → bool ("0"/"1")

BIO_ID (Biometria):
✅ similarity_threshold_1ton      - "0" → int

ONLINE_CLIENT (Modo Enterprise):
✅ server_id                      - "5" → int
✅ extract_template               - "1" → bool ("0"/"1")
✅ max_request_attempts           - "5" → int

CATRA (Catraca):
✅ anti_passback                  - "0" → bool ("0"/"1")
✅ daily_reset                    - "0" → bool ("0"/"1")
✅ gateway                        - "clockwise"/"anticlockwise" → string
✅ operation_mode                 - "blocked"/"entrance_open"/"exit_open"/"both_open" → string

BIO_MODULE:
✅ var_min                        - "1000" → int

MONITOR:
✅ path                           - "api/notifications" → string
✅ hostname                       - "catracaapi.dev..." → string
✅ port                           - "" → string/int
✅ request_timeout                - "1000" → int (ms)

PUSH_SERVER:
✅ push_request_timeout           - "15000" → int (ms)
✅ push_request_period            - "60" → int (segundos)
✅ push_remote_address            - "" → string

W_IN0/W_IN1 (Wiegand In):
✅ byte_order                     - "" → string

=============================================================================
CONVERSÕES NECESSÁRIAS:
=============================================================================

1. BOOLEANOS SIMPLES ("0"/"1"):
   - online, beep_enabled, bell_enabled, local_identification
   - auto_reboot, siren_enabled, verbose_logging
   - multi_factor_authentication, extract_template
   - anti_passback, daily_reset

2. VALORES ESPECIAIS:
   - exception_mode: "none" = False, "emergency"/"lock_down" = True
   - gateway: "clockwise"/"anticlockwise" (string)
   - operation_mode: "blocked"/"entrance_open"/"exit_open"/"both_open" (string)

3. INTEIROS:
   - bell_relay, catra_timeout, siren_relay
   - log_type, similarity_threshold_1ton
   - server_id, max_request_attempts
   - var_min, request_timeout
   - push_request_timeout, push_request_period

4. STRINGS:
   - language, byte_order, path, hostname, port, push_remote_address

5. TIMESTAMPS/NULL:
   - daylight_savings_time_start, daylight_savings_time_end

=============================================================================
MAPEAMENTO PARA MODELS DJANGO:
=============================================================================

SystemConfig:
  ✅ auto_reboot_hour           → FIXO: 3 (não existe na API)
  ✅ auto_reboot_minute         → FIXO: 0 (não existe na API)
  ❌ clear_expired_users        → FIXO: False (não existe na API)
  ❌ url_reboot_enabled         → FIXO: True (não existe na API)
  ❌ keep_user_image            → FIXO: True (não existe na API)
  ✅ catra_timeout              → general.catra_timeout
  ✅ online                     → general.online
  ✅ local_identification       → general.local_identification
  ✅ language                   → general.language
  ✅ daylight_savings_time_start → general.daylight_savings_time_start
  ✅ daylight_savings_time_end  → general.daylight_savings_time_end
  ❌ web_server_enabled         → FIXO: True (não existe na API)

HardwareConfig:
  ✅ beep_enabled               → general.beep_enabled
  ✅ bell_enabled               → general.bell_enabled
  ✅ bell_relay                 → general.bell_relay
  ❌ ssh_enabled                → FIXO: False (não existe na API)
  ❌ relayN_enabled             → FIXO: False (não existe na API)
  ❌ relayN_timeout             → FIXO: 5 (não existe na API)
  ❌ relayN_auto_close          → FIXO: True (não existe na API)
  ❌ door_sensorN_enabled       → FIXO: False (não existe na API)
  ❌ door_sensorN_idle          → FIXO: 10 (não existe na API)
  ❌ doorN_interlock            → FIXO: False (não existe na API)
  ✅ exception_mode             → general.exception_mode (none=False)
  ❌ doorN_exception_mode       → FIXO: False (não existe na API)

SecurityConfig:
  ❌ password_only              → FIXO: False (não existe na API)
  ❌ hide_password_only         → FIXO: False (não existe na API)
  ❌ password_only_tip          → FIXO: "" (não existe na API)
  ❌ hide_name_on_identification → FIXO: False (não existe na API)
  ❌ denied_transaction_code    → FIXO: "" (não existe na API)
  ❌ send_code_when_not_identified → FIXO: False (não existe na API)
  ❌ send_code_when_not_authorized → FIXO: False (não existe na API)

UIConfig:
  ❌ screen_always_on           → FIXO: False (não existe na API)

MonitorConfig:
  ✅ request_timeout            → monitor.request_timeout
  ✅ hostname                   → monitor.hostname
  ✅ port                       → monitor.port
  ✅ path                       → monitor.path
  ❌ inform_access_event_id     → Não retornado na resposta
  ❌ alive_interval             → Não retornado na resposta

=============================================================================
"""
