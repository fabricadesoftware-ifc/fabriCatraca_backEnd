# API de Configuração da Catraca - Documentação Completa

## 📚 Índice

1. [Visão Geral](#visão-geral)
2. [Autenticação](#autenticação)
3. [System Config](#system-config)
4. [Hardware Config](#hardware-config)
5. [Security Config](#security-config)
6. [UI Config](#ui-config)
7. [Catra Config](#catra-config)
8. [Push Server Config](#push-server-config)
9. [Monitor Config](#monitor-config)
10. [Sincronização](#sincronização)
11. [Exemplos Práticos](#exemplos-práticos)

---

## 🎯 Visão Geral

A API de Configuração permite gerenciar **7 tipos diferentes de configurações** da catraca ControlID:

| Config | Descrição | Endpoint Base |
|--------|-----------|---------------|
| **SystemConfig** | Configurações gerais do sistema | `/api/control_id_config/system-configs/` |
| **HardwareConfig** | Configurações de hardware (beep, sino, alarme) | `/api/control_id_config/hardware-configs/` |
| **SecurityConfig** | Configurações de segurança e logs | `/api/control_id_config/security-configs/` |
| **UIConfig** | Configurações de interface do usuário | `/api/control_id_config/ui-configs/` |
| **CatraConfig** | Configurações específicas da catraca | `/api/control_id_config/catra-configs/` |
| **PushServerConfig** | Configurações de servidor push | `/api/control_id_config/push-server-configs/` |
| **MonitorConfig** | Configurações de monitor (push logs) | `/api/control_id_monitor/monitor-configs/` |

### Operações Disponíveis

Cada configuração suporta operações CRUD padrão:

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| **GET** | `/configs/` | Lista todas as configurações |
| **POST** | `/configs/` | Cria nova configuração |
| **GET** | `/configs/{id}/` | Detalhes de uma configuração |
| **PUT** | `/configs/{id}/` | Atualiza configuração completa |
| **PATCH** | `/configs/{id}/` | Atualiza campos específicos |
| **DELETE** | `/configs/{id}/` | Remove configuração |

### Operações Especiais

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| **POST** | `/sync/` | Sincroniza todas as configs de todos os devices |
| **GET** | `/sync/status/` | Status da última sincronização |

---

## 🔐 Autenticação

Todas as requisições requerem autenticação JWT:

```bash
# 1. Obter token
POST /api/token/
{
    "username": "seu_usuario",
    "password": "sua_senha"
}

# Resposta
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}

# 2. Usar token nas requisições
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

---

## 1️⃣ System Config

**Endpoint Base**: `/api/control_id_config/system-configs/`

Configurações gerais do sistema da catraca.

### Campos

| Campo | Tipo | Obrigatório | Descrição | Impacto |
|-------|------|-------------|-----------|---------|
| `device` | integer | ✅ Sim | ID do dispositivo | Define qual catraca será configurada |
| `online` | boolean | ❌ Não | Modo online/offline | Modo de operação da catraca se true ela pergunta para o servidor se pode liberar ou não |
| `auto_reboot` | boolean | ❌ Não | Reinicialização automática | Se `true`, catraca reinicia automaticamente em caso de problemas |
| `catra_timeout` | integer | ❌ Não | Timeout da catraca (segundos) | Tempo máximo de espera para rotação. Padrão: 30s |
| `local_identification` | boolean | ❌ Não | Identificação local | Se `true`, permite identificação sem servidor |
| `exception_mode` | string | ❌ Não | Modo de exceção | Valores: `none`, `free`, `blocked` |
| `language` | string | ❌ Não | Idioma da interface | Valores: `pt_BR`, `en_US`, `es_ES` |
| `daylight_savings_time_start` | string | ❌ Não | Início horário de verão | Formato: `MM-DD HH:MM` |
| `daylight_savings_time_end` | string | ❌ Não | Fim horário de verão | Formato: `MM-DD HH:MM` |

### Valores de `exception_mode`

| Valor | Descrição | Uso |
|-------|-----------|-----|
| `none` | Modo normal | Operação padrão, requer identificação |
| `free` | Modo liberado | **ATENÇÃO**: Libera passagem sem identificação |
| `blocked` | Modo bloqueado | **ATENÇÃO**: Bloqueia toda passagem |

### Exemplos

#### Listar Configurações

```bash
GET /api/control_id_config/system-configs/
Authorization: Bearer {token}
```

**Resposta**:
```json
[
    {
        "id": 1,
        "device": 1,
        "device_name": "Catraca Principal",
        "online": true,
        "auto_reboot": true,
        "catra_timeout": 30,
        "local_identification": true,
        "exception_mode": "none",
        "language": "pt_BR",
        "daylight_savings_time_start": "",
        "daylight_savings_time_end": "",
        "created_at": "2025-01-01T10:00:00Z",
        "updated_at": "2025-01-01T10:00:00Z"
    }
]
```

#### Criar Configuração

```bash
POST /api/control_id_config/system-configs/
Authorization: Bearer {token}
Content-Type: application/json

{
    "device": 1,
    "online": true,
    "auto_reboot": true,
    "catra_timeout": 30,
    "local_identification": true,
    "exception_mode": "none",
    "language": "pt_BR"
}
```

#### Atualizar Configuração

```bash
PATCH /api/control_id_config/system-configs/1/
Authorization: Bearer {token}
Content-Type: application/json

{
    "online": false,
    "exception_mode": "free"
}
```


#### Sincronizar da Catraca

```bash
POST /api/control_id_config/system-configs/1/sync-from-catraca/
Authorization: Bearer {token}
```

Busca as configurações atuais da catraca e atualiza no sistema.

---

## 2️⃣ Hardware Config

**Endpoint Base**: `/api/control_id_config/hardware-configs/`

Configurações de hardware da catraca (sons, sino, alarme).

### Campos

| Campo | Tipo | Obrigatório | Descrição | Impacto |
|-------|------|-------------|-----------|---------|
| `device` | integer | ✅ Sim | ID do dispositivo | Define qual catraca será configurada |
| `beep_enabled` | boolean | ❌ Não | Habilita beep | Se `true`, emite beep sonoro em eventos |
| `bell_enabled` | boolean | ❌ Não | Habilita sino | Se `true`, ativa sino em eventos |
| `bell_relay` | integer | ❌ Não | Relé do sino | Número do relé (1-4) que controla o sino |
| `exception_mode` | boolean | ❌ Não | Modo exceção hardware | Configuração específica de exceção |
| `siren_enabled` | boolean | ❌ Não | Habilita sirene | Se `true`, ativa sirene de alarme |
| `siren_relay` | integer | ❌ Não | Relé da sirene | Número do relé (1-4) que controla a sirene |

### Impacto dos Relés

| Relé | Uso Comum | Nota |
|------|-----------|------|
| 1 | Sino/campainha | Acionado em acessos válidos |
| 2 | Sirene/alarme | Acionado em violações |
| 3 | Porta/trava | Libera trava magnética |
| 4 | Custom | Uso personalizado |

### Exemplos

#### Criar Configuração de Hardware

```bash
POST /api/control_id_config/hardware-configs/
Authorization: Bearer {token}
Content-Type: application/json

{
    "device": 1,
    "beep_enabled": true,
    "bell_enabled": true,
    "bell_relay": 1,
    "exception_mode": false,
    "siren_enabled": true,
    "siren_relay": 2
}
```

**Resposta**:
```json
{
    "id": 1,
    "device": 1,
    "device_name": "Catraca Principal",
    "beep_enabled": true,
    "bell_enabled": true,
    "bell_relay": 1,
    "exception_mode": false,
    "siren_enabled": true,
    "siren_relay": 2
}
```

#### Desabilitar Todos os Sons

```bash
PATCH /api/control_id_config/hardware-configs/1/
Authorization: Bearer {token}
Content-Type: application/json

{
    "beep_enabled": false,
    "bell_enabled": false,
    "siren_enabled": false
}
```

💡 **Dica**: Útil para ambientes que precisam de silêncio absoluto.

---

## 3️⃣ Security Config

**Endpoint Base**: `/api/control_id_config/security-configs/`

Configurações de segurança e logs.

### Campos

| Campo | Tipo | Obrigatório | Descrição | Impacto |
|-------|------|-------------|-----------|---------|
| `device` | integer | ✅ Sim | ID do dispositivo | Define qual catraca será configurada |
| `verbose_logging` | boolean | ❌ Não | Logs detalhados | Se `true`, gera logs muito verbosos. **ATENÇÃO**: Pode encher storage |
| `log_type` | integer | ❌ Não | Tipo de log | `0`: Normal, `1`: Detalhado, `2`: Debug |
| `multi_factor_authentication` | boolean | ❌ Não | Autenticação multifator | Se `true`, requer múltiplos fatores de identificação |

### Valores de `log_type`

| Valor | Descrição | Uso |
|-------|-----------|-----|
| `0` | Normal | Logs básicos de acesso |
| `1` | Detalhado | Inclui tentativas e falhas |
| `2` | Debug | **CUIDADO**: Gera MUITOS logs, só para debug |

### Exemplos

#### Criar Configuração de Segurança

```bash
POST /api/control_id_config/security-configs/
Authorization: Bearer {token}
Content-Type: application/json

{
    "device": 1,
    "verbose_logging": false,
    "log_type": 0,
    "multi_factor_authentication": false
}
```

#### Ativar Logs Detalhados (Debug)

```bash
PATCH /api/control_id_config/security-configs/1/
Authorization: Bearer {token}
Content-Type: application/json

{
    "verbose_logging": true,
    "log_type": 2
}
```

⚠️ **ATENÇÃO**: Só use `log_type: 2` temporariamente para debug! Pode encher o storage da catraca.

---

## 4️⃣ UI Config

**Endpoint Base**: `/api/control_id_config/ui-configs/`

Configurações de interface do usuário (display, teclado, etc).

### Campos

| Campo | Tipo | Obrigatório | Descrição | Impacto |
|-------|------|-------------|-----------|---------|
| `device` | integer | ✅ Sim | ID do dispositivo | Define qual catraca será configurada |
| `display_brightness` | integer | ❌ Não | Brilho do display | Valor: 0-100. Controla brilho da tela |
| `display_timeout` | integer | ❌ Não | Timeout do display (seg) | Tempo até apagar tela. 0 = sempre ligado |
| `keyboard_backlight` | boolean | ❌ Não | Luz de fundo teclado | Se `true`, ilumina teclado |
| `welcome_message` | string | ❌ Não | Mensagem de boas-vindas | Texto exibido na tela inicial |
| `access_denied_message` | string | ❌ Não | Mensagem de acesso negado | Texto quando acesso é negado |

### Exemplos

#### Criar Configuração de UI

```bash
POST /api/control_id_config/ui-configs/
Authorization: Bearer {token}
Content-Type: application/json

{
    "device": 1,
    "display_brightness": 80,
    "display_timeout": 30,
    "keyboard_backlight": true,
    "welcome_message": "Bem-vindo ao Campus",
    "access_denied_message": "Acesso Negado"
}
```

#### Ajustar Brilho e Timeout

```bash
PATCH /api/control_id_config/ui-configs/1/
Authorization: Bearer {token}
Content-Type: application/json

{
    "display_brightness": 50,
    "display_timeout": 60
}
```

💡 **Dica**: Reduza `display_brightness` para economizar energia e aumentar vida útil da tela.

---

## 5️⃣ Catra Config

**Endpoint Base**: `/api/control_id_config/catra-configs/`

Configurações específicas da catraca (giro, anti-passback, etc).

### Campos

| Campo | Tipo | Obrigatório | Descrição | Impacto |
|-------|------|-------------|-----------|---------|
| `device` | integer | ✅ Sim | ID do dispositivo | Define qual catraca será configurada |
| `anti_passback` | boolean | ❌ Não | Anti-passback | Se `true`, impede entradas/saídas duplicadas |
| `daily_reset` | boolean | ❌ Não | Reset diário | Se `true`, reseta contadores à meia-noite |
| `gateway` | string | ❌ Não | Sentido do giro | `clockwise` (horário) ou `anticlockwise` (anti-horário) |
| `operation_mode` | string | ❌ Não | Modo de operação | `normal`, `free`, `blocked`, `controlled` |

### Valores de `gateway`

| Valor | Descrição | Uso |
|-------|-----------|-----|
| `clockwise` | Horário | Giro no sentido horário para liberar |
| `anticlockwise` | Anti-horário | Giro no sentido anti-horário para liberar |

### Valores de `operation_mode`

| Valor | Descrição | Impacto |
|-------|-----------|---------|
| `normal` | Modo normal | Requer identificação válida |
| `free` | Modo liberado | **ATENÇÃO**: Libera giro sem identificação |
| `blocked` | Modo bloqueado | **ATENÇÃO**: Bloqueia toda passagem |
| `controlled` | Modo controlado | Giro controlado por servidor |

### Exemplos

#### Criar Configuração de Catraca

```bash
POST /api/control_id_config/catra-configs/
Authorization: Bearer {token}
Content-Type: application/json

{
    "device": 1,
    "anti_passback": true,
    "daily_reset": true,
    "gateway": "clockwise",
    "operation_mode": "normal"
}
```

**Resposta**:
```json
{
    "id": 1,
    "device": 1,
    "device_name": "Catraca Principal",
    "anti_passback": true,
    "daily_reset": true,
    "gateway": "clockwise",
    "operation_mode": "normal"
}
```

#### Colocar em Modo Liberado (Temporário)

```bash
PATCH /api/control_id_config/catra-configs/1/
Authorization: Bearer {token}
Content-Type: application/json

{
    "operation_mode": "free"
}
```

⚠️ **ATENÇÃO**: Em modo `free`, qualquer pessoa pode passar! Use apenas temporariamente.

#### Inverter Sentido do Giro

```bash
PATCH /api/control_id_config/catra-configs/1/
Authorization: Bearer {token}
Content-Type: application/json

{
    "gateway": "anticlockwise"
}
```

---

## 6️⃣ Push Server Config

**Endpoint Base**: `/api/control_id_config/push-server-configs/`

Configurações de servidor push (envio de eventos para servidor externo).

### Campos

| Campo | Tipo | Obrigatório | Descrição | Impacto |
|-------|------|-------------|-----------|---------|
| `device` | integer | ✅ Sim | ID do dispositivo | Define qual catraca será configurada |
| `push_request_timeout` | integer | ❌ Não | Timeout (ms) | Tempo máximo de espera. Padrão: 15000ms |
| `push_request_period` | integer | ❌ Não | Período (segundos) | Intervalo entre envios. Padrão: 60s |
| `push_remote_address` | string | ❌ Não | Endereço do servidor | URL do servidor que recebe os eventos |

### Comportamento

- **Timeout**: Se servidor não responder em `push_request_timeout`, catraca desiste
- **Period**: Catraca envia eventos a cada `push_request_period` segundos
- **Address**: Se vazio, push é desabilitado

### Exemplos

#### Criar Configuração de Push Server

```bash
POST /api/control_id_config/push-server-configs/
Authorization: Bearer {token}
Content-Type: application/json

{
    "device": 1,
    "push_request_timeout": 15000,
    "push_request_period": 60,
    "push_remote_address": "https://meuservidor.com/api/events"
}
```

#### Desabilitar Push

```bash
PATCH /api/control_id_config/push-server-configs/1/
Authorization: Bearer {token}
Content-Type: application/json

{
    "push_remote_address": ""
}
```

#### Ajustar Timeout e Período

```bash
PATCH /api/control_id_config/push-server-configs/1/
Authorization: Bearer {token}
Content-Type: application/json

{
    "push_request_timeout": 30000,
    "push_request_period": 30
}
```

💡 **Dica**: Aumente `push_request_timeout` se servidor for lento. Reduza `push_request_period` para eventos mais frequentes.

---

## 7️⃣ Monitor Config

**Endpoint Base**: `/api/control_id_monitor/monitor-configs/`

Configurações de monitor (push de logs em tempo real).

### Campos

| Campo | Tipo | Obrigatório | Descrição | Impacto |
|-------|------|-------------|-----------|---------|
| `device` | integer | ✅ Sim | ID do dispositivo | Define qual catraca será configurada |
| `hostname` | string | ✅ Sim | Hostname do servidor | IP ou domínio do servidor |
| `port` | string | ✅ Sim | Porta do servidor | Porta HTTP/HTTPS (ex: "8000") |
| `path` | string | ❌ Não | Path do endpoint | Caminho da API. Padrão: "api/notifications/dao" |
| `request_timeout` | integer | ❌ Não | Timeout (ms) | Tempo máximo de espera. Padrão: 5000ms |

### Propriedades Computadas (Read-Only)

| Propriedade | Descrição |
|-------------|-----------|
| `is_configured` | `true` se hostname e port estão preenchidos |
| `full_url` | URL completa: `http://hostname:port/path` |
| `notification_url` | Mesmo que `full_url` |
| `status` | "✓ Ativo" ou "○ Inativo" |

### Diferença: Monitor vs Push Server

| Aspecto | Monitor | Push Server |
|---------|---------|-------------|
| **Tipo** | Push de logs | Push de eventos |
| **Frequência** | Tempo real (imediato) | Periódico |
| **Dados** | Logs de acesso | Eventos gerais |
| **Uso** | Logs em tempo real | Sincronização periódica |

### Exemplos

#### Criar Configuração de Monitor

```bash
POST /api/control_id_monitor/monitor-configs/
Authorization: Bearer {token}
Content-Type: application/json

{
    "device": 1,
    "hostname": "192.168.0.100",
    "port": "8000",
    "path": "api/control_id_monitor/notifications/dao",
    "request_timeout": 5000
}
```

**Resposta**:
```json
{
    "id": 1,
    "device": 1,
    "device_name": "Catraca Principal",
    "hostname": "192.168.0.100",
    "port": "8000",
    "path": "api/control_id_monitor/notifications/dao",
    "request_timeout": 5000,
    "is_configured": true,
    "full_url": "http://192.168.0.100:8000/api/control_id_monitor/notifications/dao",
    "notification_url": "http://192.168.0.100:8000/api/control_id_monitor/notifications/dao",
    "status": "✓ Ativo"
}
```

#### Ativar Monitor (Envia para Catraca)

```bash
POST /api/control_id_monitor/monitor-configs/1/activate/
Authorization: Bearer {token}
```

Este endpoint:
1. Pega a configuração do banco
2. Envia para a catraca via `set_configuration.fcgi`
3. Catraca começa a enviar logs automaticamente

#### Desativar Monitor

```bash
POST /api/control_id_monitor/monitor-configs/1/deactivate/
Authorization: Bearer {token}
```

Limpa as configurações de monitor na catraca (não deleta do banco).

#### Verificar Configuração na Catraca (Debug)

```bash
GET /api/control_id_monitor/monitor-configs/1/probe/
Authorization: Bearer {token}
```

**Resposta**:
```json
{
    "success": true,
    "monitor": {
        "hostname": "192.168.0.100",
        "port": "8000",
        "path": "api/control_id_monitor/notifications/dao",
        "request_timeout": "5000"
    },
    "full_url": "http://192.168.0.100:8000/api/control_id_monitor/notifications/dao"
}
```

---

## 🔄 Sincronização

### Sincronizar Todas as Configurações

```bash
POST /api/control_id_config/sync/
Authorization: Bearer {token}
```

Sincroniza **todas as configurações** de **todos os dispositivos ativos**.

**Resposta**:
```json
{
    "success": true,
    "message": "Sincronização concluída",
    "stats": {
        "devices": 2,
        "system_synced": 2,
        "hardware_synced": 2,
        "security_synced": 2,
        "ui_synced": 2,
        "monitor_synced": 1,
        "catra_synced": 2,
        "push_server_synced": 2,
        "errors": []
    }
}
```

### Status da Sincronização

```bash
GET /api/control_id_config/sync/status/
Authorization: Bearer {token}
```

**Resposta**:
```json
{
    "last_sync": "2025-01-01T14:30:00Z",
    "status": "success",
    "devices_synced": 2,
    "total_configs_synced": 14
}
```

### Sincronizar Config Específica

```bash
POST /api/control_id_config/system-configs/1/sync-from-catraca/
Authorization: Bearer {token}
```

Sincroniza apenas a configuração específica daquele device.

---

## 📋 Exemplos Práticos

### Caso 1: Configurar Nova Catraca

```bash
# 1. System Config
POST /api/control_id_config/system-configs/
{
    "device": 1,
    "online": true,
    "auto_reboot": true,
    "catra_timeout": 30,
    "local_identification": true,
    "exception_mode": "none",
    "language": "pt_BR"
}

# 2. Hardware Config
POST /api/control_id_config/hardware-configs/
{
    "device": 1,
    "beep_enabled": true,
    "bell_enabled": true,
    "bell_relay": 1
}

# 3. Security Config
POST /api/control_id_config/security-configs/
{
    "device": 1,
    "verbose_logging": false,
    "log_type": 0,
    "multi_factor_authentication": false
}

# 4. Catra Config
POST /api/control_id_config/catra-configs/
{
    "device": 1,
    "anti_passback": true,
    "daily_reset": true,
    "gateway": "clockwise",
    "operation_mode": "normal"
}

# 5. Monitor Config (Opcional)
POST /api/control_id_monitor/monitor-configs/
{
    "device": 1,
    "hostname": "192.168.0.100",
    "port": "8000",
    "path": "api/control_id_monitor/notifications/dao"
}

# 6. Ativar Monitor
POST /api/control_id_monitor/monitor-configs/1/activate/
```

### Caso 2: Modo Manutenção (Liberar Catraca)

```bash
# Colocar em modo livre
PATCH /api/control_id_config/catra-configs/1/
{
    "operation_mode": "free"
}

# Desabilitar sons
PATCH /api/control_id_config/hardware-configs/1/
{
    "beep_enabled": false,
    "bell_enabled": false
}
```

### Caso 3: Debug de Problemas

```bash
# 1. Ativar logs detalhados
PATCH /api/control_id_config/security-configs/1/
{
    "verbose_logging": true,
    "log_type": 2
}

# 2. Verificar configs atuais
GET /api/control_id_monitor/monitor-configs/1/probe/

# 3. Sincronizar tudo
POST /api/control_id_config/sync/

# 4. Desativar logs detalhados
PATCH /api/control_id_config/security-configs/1/
{
    "verbose_logging": false,
    "log_type": 0
}
```

### Caso 4: Emergência - Bloquear Tudo

```bash
# Bloquear todas as catracas
PATCH /api/control_id_config/catra-configs/1/
{
    "operation_mode": "blocked"
}

PATCH /api/control_id_config/catra-configs/2/
{
    "operation_mode": "blocked"
}

# Ou via System Config
PATCH /api/control_id_config/system-configs/1/
{
    "exception_mode": "blocked"
}
```

---

## ⚠️ Avisos Importantes

### 1. Modo Online/Offline

```bash
# ❌ CUIDADO: Isso DESCONECTA a catraca da rede!
{
    "online": false
}
```

**Impacto**: Catraca para de se comunicar com o servidor. Só funciona localmente.

### 2. Exception Mode

```bash
# ❌ CUIDADO: Libera TODOS os acessos!
{
    "exception_mode": "free"
}

# ❌ CUIDADO: Bloqueia TODOS os acessos!
{
    "exception_mode": "blocked"
}
```

**Impacto**: Sobrescreve todas as regras de acesso.

### 3. Logs Debug

```bash
# ❌ CUIDADO: Gera MUITOS logs!
{
    "verbose_logging": true,
    "log_type": 2
}
```

**Impacto**: Pode encher o storage da catraca em poucas horas. Use APENAS para debug temporário.

### 4. Timeout e Period

```bash
# ⚠️ Valores muito baixos podem sobrecarregar
{
    "push_request_period": 5,  // Muito frequente
    "push_request_timeout": 1000  // Muito curto
}
```

**Impacto**: Pode sobrecarregar rede e servidor.

### 5. Anti-Passback

```bash
{
    "anti_passback": true
}
```

**Impacto**: Usuário que entrou não pode entrar de novo sem sair primeiro. Se resetar sem registro de saída, fica preso!

---

## 📊 Relação Entre Campos

### System Config vs Catra Config

Ambos têm `exception_mode`/`operation_mode`:

| Config | Campo | Escopo |
|--------|-------|--------|
| System | `exception_mode` | Global da catraca |
| Catra | `operation_mode` | Específico do giro |

**Prioridade**: `system.exception_mode` > `catra.operation_mode`

### Hardware Config: Relés

```
Relé 1 → Sino (bell_relay)
Relé 2 → Sirene (siren_relay)
Relé 3 → Trava da porta
Relé 4 → Custom
```

**Não use o mesmo relé para duas funções!**

---

## 🔗 Links Relacionados

- [README Completo](README_COMPLETO.md)
- [Monitor Push](README_MONITOR_PUSH.md)
- [Access Logs](README_ACCESS_LOGS.md)
- [Formato API](API_GET_CONFIGURATION_FORMATO.md)

---

## 📝 Resumo Rápido

| Ação | Endpoint | Método |
|------|----------|--------|
| Listar configs | `/system-configs/` | GET |
| Criar config | `/system-configs/` | POST |
| Atualizar config | `/system-configs/{id}/` | PATCH |
| Deletar config | `/system-configs/{id}/` | DELETE |
| Sincronizar | `/system-configs/{id}/sync-from-catraca/` | POST |
| Sincronizar tudo | `/sync/` | POST |

**Autenticação**: Todas as requisições precisam de `Authorization: Bearer {token}`

---

**Versão**: 1.0  
**Data**: Outubro 2025  
**Status**: ✅ Completo e Testado
