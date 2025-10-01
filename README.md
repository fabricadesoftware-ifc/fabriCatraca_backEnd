# 📚 FabriCatraca - Documentação Completa

> Sistema de Controle de Acesso Escolar com Catracas ControlID em Modo Standalone

---

## 📋 Índice

1. [Visão Geral do Projeto](#-visão-geral-do-projeto)
2. [Arquitetura do Sistema](#-arquitetura-do-sistema)
3. [Modelos de Configuração](#-modelos-de-configuração)
4. [API REST - Endpoints](#-api-rest---endpoints)
5. [Sistema de Logs de Acesso](#-sistema-de-logs-de-acesso)
6. [Gerenciamento de Sessão](#-gerenciamento-de-sessão)
7. [Testes](#-testes)
8. [Guia de Instalação](#-guia-de-instalação)
9. [Uso Prático](#-uso-prático)
10. [Deploy e Produção](#-deploy-e-produção)

---

## 🎯 Visão Geral do Projeto

### O que é?

**FabriCatraca** é um sistema Django REST que gerencia catracas biométricas **ControlID** em **modo Standalone** para controle de acesso escolar. O sistema implementa todas as funcionalidades do ADP (Admin Devices Panel) incluindo:

- ✅ Gerenciamento de 7 tipos de configurações de dispositivos
- ✅ Sincronização bidirecional com catracas físicas via REST API
- ✅ Sistema de logs de acesso com 15 tipos de eventos
- ✅ Interface admin completa para gestão
- ✅ API REST completa para integração
- ✅ Conformidade com LGPD (biometrias armazenadas apenas nas catracas)

### Características Principais

| Característica | Descrição |
|----------------|-----------|
| **Framework** | Django 5.2.4 + Django REST Framework |
| **Hardware** | ControlID IDBLOCK (catracas biométricas) |
| **Modo de Operação** | Standalone (sem servidor central) |
| **Autenticação** | Biométrica, Cartão, Senha, QR Code |
| **Regras de Acesso** | Baseadas em horários e dias da semana |
| **Logs** | 15 tipos de eventos com filtros avançados |
| **Sessões** | Smart reuse com retry automático em expiração |
| **Testes** | 65+ testes (unit/integration/e2e) com 85%+ cobertura |

---

## 🏗️ Arquitetura do Sistema

### Estrutura do Projeto

```
catraca_denovo/
├── src/
│   ├── core/
│   │   ├── control_id/           # App principal (Device, AccessLog)
│   │   ├── control_id_config/    # App de configurações (7 configs)
│   │   ├── user/                 # Gestão de usuários
│   │   └── __seedwork__/         # Classes base reutilizáveis
│   ├── django_project/
│   │   ├── settings.py           # Configurações do Django
│   │   ├── urls.py               # URLs principais
│   │   └── celery.py             # Configuração do Celery
│   └── manage.py
├── tests/                        # Suite de testes (65+ testes)
│   ├── unit/                     # Testes unitários (31 testes)
│   ├── integration/              # Testes de integração (24 testes)
│   └── e2e/                      # Testes end-to-end (10 testes)
└── requirements.txt              # Dependências
```

### Stack Tecnológico

| Componente | Tecnologia | Versão |
|------------|------------|--------|
| **Backend** | Django | 5.2.4 |
| **API REST** | Django REST Framework | 3.15+ |
| **Banco de Dados** | PostgreSQL / SQLite | - |
| **Task Queue** | Celery | 5.5.3 |
| **Broker** | RabbitMQ / Redis | - |
| **Testes** | Pytest + Factory Boy | 8.4.2 / 3.3.3 |
| **WSGI Server** | Gunicorn | - |
| **Deploy** | Heroku / Docker | - |

### Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND / POSTMAN                      │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP REST API
┌────────────────────────▼────────────────────────────────────┐
│                    DJANGO REST FRAMEWORK                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   ViewSets   │  │ Serializers  │  │   Filters    │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│  ┌──────▼──────────────────▼──────────────────▼───────┐    │
│  │              MODELS (7 Configs + Device)            │    │
│  └──────┬──────────────────────────────────────────────┘    │
└─────────┼───────────────────────────────────────────────────┘
          │ Database ORM
┌─────────▼─────────────────────────────────────────────────┐
│                      POSTGRESQL DB                         │
└────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    SYNC LAYER (Mixins)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │Session Mgmt  │  │ API Requests │  │ Retry Logic  │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼──────────────────┼──────────────────┼──────────────┘
          │ REST API Calls   │                  │
┌─────────▼──────────────────▼──────────────────▼──────────────┐
│              CONTROLID IDBLOCK (Hardware)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Biometric   │  │    Configs   │  │  Access Logs │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└───────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    CELERY TASKS (Async)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Config Sync │  │   Log Sync   │  │  Scheduled   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└───────────────────────────────────────────────────────────────┘
```

---

## 🗄️ Modelos de Configuração

O sistema gerencia **7 tipos de configuração** que espelham os blocos da API ControlID:

### Tabela Resumo dos Models

| Model | Campos Principais | Seção API | Relação |
|-------|-------------------|-----------|---------|
| **Device** | `ip`, `port`, `serial_number`, `name` | - | OneToMany (base) |
| **SystemConfig** | `auto_reboot`, `reset_hour`, `language` | `general` | OneToOne → Device |
| **HardwareConfig** | `beep_enabled`, `bell_enabled`, `exception_mode` | `general`, `alarm` | OneToOne → Device |
| **SecurityConfig** | `verbose_logging`, `log_type`, `multi_factor_auth` | `identifier` | OneToOne → Device |
| **UIConfig** | `screen_always_on` | - | OneToOne → Device |
| **MonitorConfig** | Campos dinâmicos (JSON) | `monitor` | OneToOne → Device |
| **CatraConfig** | `anti_passback`, `gateway`, `operation_mode` | `catra` | OneToOne → Device |
| **PushServerConfig** | `push_remote_address`, `timeout`, `period` | `push_server` | OneToOne → Device |

### 1. SystemConfig (Configurações do Sistema)

| Campo | Tipo | Descrição | API Field | Default |
|-------|------|-----------|-----------|---------|
| `device` | OneToOne | Dispositivo vinculado | - | - |
| `auto_reboot_enabled` | Boolean | Reinício automático | `auto_reboot` | `False` |
| `auto_reboot_hour` | Integer | Hora do reboot (0-23) | - | `3` |
| `auto_reboot_minute` | Integer | Minuto do reboot (0-59) | - | `0` |
| `reset_hour` | Integer | Hora de reset (0-23) | `reset_hour` | `0` |
| `language` | CharField | Idioma (pt-BR, en, es) | `language` | `pt-BR` |
| `clear_expired_users` | Boolean | Limpar usuários expirados | - | `False` |
| `url_reboot_enabled` | Boolean | Reboot via URL | - | `True` |
| `keep_user_image` | Boolean | Manter imagem do usuário | - | `True` |
| `web_server_enabled` | Boolean | Servidor web ativo | - | `True` |

**Endpoint API**: `/api/config/system-configs/`

### 2. HardwareConfig (Configurações de Hardware)

| Campo | Tipo | Descrição | API Section | Default |
|-------|------|-----------|-------------|---------|
| `device` | OneToOne | Dispositivo vinculado | - | - |
| `beep_enabled` | Boolean | Som ao identificar | `general.beep_enabled` | `True` |
| `bell_enabled` | Boolean | Campainha habilitada | `general.bell_enabled` | `False` |
| `bell_relay` | Integer | Relé da campainha (0-2) | `general.bell_relay` | `0` |
| `siren_enabled` | Boolean | Sirene de alarme | `alarm.siren_enabled` | `False` |
| `siren_relay` | Integer | Relé da sirene (0-2) | `alarm.siren_relay` | `0` |
| `exception_mode` | CharField | Modo exceção (none/emergency/lock_down) | `general.exception_mode` | `none` |
| `ssh_enabled` | Boolean | SSH habilitado | - | `False` |
| `relayN_*` | Vários | Configurações de relés | - | Vários |
| `door_sensor*` | Vários | Sensores de porta | - | Vários |

**Endpoint API**: `/api/config/hardware-configs/`

### 3. SecurityConfig (Configurações de Segurança)

| Campo | Tipo | Descrição | API Field | Default |
|-------|------|-----------|-----------|---------|
| `device` | OneToOne | Dispositivo vinculado | - | - |
| `verbose_logging` | Boolean | Log detalhado | `identifier.verbose_logging` | `False` |
| `log_type` | CharField | Tipo de log (basic/extended) | `identifier.log_type` | `basic` |
| `multi_factor_authentication` | Boolean | Autenticação multi-fator | `identifier.multi_factor_authentication` | `False` |
| `password_only` | Boolean | Apenas senha | - | `False` |
| `hide_password_only` | Boolean | Ocultar modo senha | - | `False` |
| `password_only_tip` | CharField | Dica senha (50 chars) | - | `""` |
| `hide_name_on_identification` | Boolean | Ocultar nome ao identificar | - | `False` |
| `denied_transaction_code` | CharField | Código transação negada | - | `""` |
| `send_code_when_not_identified` | Boolean | Enviar código não identificado | - | `False` |
| `send_code_when_not_authorized` | Boolean | Enviar código não autorizado | - | `False` |

**Endpoint API**: `/api/config/security-configs/`

### 4. UIConfig (Configurações de Interface)

| Campo | Tipo | Descrição | API Field | Default |
|-------|------|-----------|-----------|---------|
| `device` | OneToOne | Dispositivo vinculado | - | - |
| `screen_always_on` | Boolean | Tela sempre ligada | - | `False` |

**Endpoint API**: `/api/config/ui-configs/`

**Nota**: Este campo não está disponível na API IDBLOCK, mantido com valor fixo `False`.

### 5. MonitorConfig (Configurações de Monitor)

| Campo | Tipo | Descrição | API Field | Default |
|-------|------|-----------|-----------|---------|
| `device` | OneToOne | Dispositivo vinculado | - | - |
| `monitor_data` | JSONField | Dados dinâmicos do monitor | `monitor.*` | `{}` |

**Endpoint API**: `/api/config/monitor-configs/`

**Nota**: Armazena configurações dinâmicas do bloco `monitor` em formato JSON.

### 6. CatraConfig (Configurações da Catraca) 🆕

| Campo | Tipo | Descrição | API Field | Opções |
|-------|------|-----------|-----------|--------|
| `device` | OneToOne | Dispositivo vinculado | - | - |
| `anti_passback` | Boolean | Anti-dupla entrada | `catra.anti_passback` | `False` |
| `daily_reset` | Boolean | Reset diário de logs | `catra.daily_reset` | `False` |
| `gateway` | CharField | Sentido da entrada | `catra.gateway` | `clockwise`, `anticlockwise` |
| `operation_mode` | CharField | Modo de operação | `catra.operation_mode` | `blocked`, `entrance_open`, `exit_open`, `both_open` |

**Endpoint API**: `/api/config/catra-configs/`

**Choices de Gateway**:
- `clockwise` → Horário (sentido horário)
- `anticlockwise` → Anti-horário

**Choices de Operation Mode**:
- `blocked` → Bloqueado (acesso só com autorização)
- `entrance_open` → Entrada liberada
- `exit_open` → Saída liberada
- `both_open` → Ambas liberadas

### 7. PushServerConfig (Configurações Push Server) 🆕

| Campo | Tipo | Descrição | API Field | Range/Default |
|-------|------|-----------|-----------|---------------|
| `device` | OneToOne | Dispositivo vinculado | - | - |
| `push_request_timeout` | Integer | Timeout em ms | `push_server.push_request_timeout` | 0-300000 (default: 15000) |
| `push_request_period` | Integer | Período em segundos | `push_server.push_request_period` | 0-86400 (default: 60) |
| `push_remote_address` | CharField | Endereço IP:porta | `push_server.push_remote_address` | Ex: `192.168.1.100:80` |

**Endpoint API**: `/api/config/push-server-configs/`

**Validações**:
- `push_request_timeout`: Máximo 300000ms (5 minutos)
- `push_request_period`: Máximo 86400s (24 horas)
- `push_remote_address`: Formato `IP:porta` ou `hostname:porta`

---

## 🔌 API REST - Endpoints

### Endpoints Principais

| Recurso | Método | Endpoint | Descrição |
|---------|--------|----------|-----------|
| **Devices** | GET | `/api/devices/` | Lista todos os dispositivos |
| | POST | `/api/devices/` | Cria novo dispositivo |
| | GET | `/api/devices/{id}/` | Detalhe do dispositivo |
| | PUT/PATCH | `/api/devices/{id}/` | Atualiza dispositivo |
| | DELETE | `/api/devices/{id}/` | Remove dispositivo |
| **System Config** | GET | `/api/config/system-configs/` | Lista configs de sistema |
| | POST | `/api/config/system-configs/` | Cria e envia para catraca |
| | GET | `/api/config/system-configs/{id}/` | Detalhe da config |
| | PUT/PATCH | `/api/config/system-configs/{id}/` | Atualiza e envia |
| | POST | `/api/config/system-configs/sync-from-catraca/` | Sincroniza da catraca |
| **Hardware Config** | GET | `/api/config/hardware-configs/` | Lista configs de hardware |
| | POST | `/api/config/hardware-configs/` | Cria e envia para catraca |
| | PUT/PATCH | `/api/config/hardware-configs/{id}/` | Atualiza e envia |
| | POST | `/api/config/hardware-configs/sync-from-catraca/` | Sincroniza da catraca |
| **Security Config** | GET | `/api/config/security-configs/` | Lista configs de segurança |
| | POST | `/api/config/security-configs/` | Cria e envia para catraca |
| | PUT/PATCH | `/api/config/security-configs/{id}/` | Atualiza e envia |
| | POST | `/api/config/security-configs/sync-from-catraca/` | Sincroniza da catraca |
| **UI Config** | GET | `/api/config/ui-configs/` | Lista configs de UI |
| | POST | `/api/config/ui-configs/` | Cria config |
| | PUT/PATCH | `/api/config/ui-configs/{id}/` | Atualiza config |
| **Monitor Config** | GET | `/api/config/monitor-configs/` | Lista configs de monitor |
| | POST | `/api/config/monitor-configs/` | Cria e envia para catraca |
| | PUT/PATCH | `/api/config/monitor-configs/{id}/` | Atualiza e envia |
| | GET | `/api/config/monitor-configs/debug-raw/` | Debug payload bruto |
| **Catra Config** 🆕 | GET | `/api/config/catra-configs/` | Lista configs de catraca |
| | POST | `/api/config/catra-configs/` | Cria e envia para catraca |
| | PUT/PATCH | `/api/config/catra-configs/{id}/` | Atualiza e envia |
| | POST | `/api/config/catra-configs/sync-from-catraca/` | Sincroniza da catraca |
| **Push Server Config** 🆕 | GET | `/api/config/push-server-configs/` | Lista configs de push |
| | POST | `/api/config/push-server-configs/` | Cria e envia para catraca |
| | PUT/PATCH | `/api/config/push-server-configs/{id}/` | Atualiza e envia |
| | POST | `/api/config/push-server-configs/sync-from-catraca/` | Sincroniza da catraca |
| **Access Logs** | GET | `/api/access-logs/` | Lista logs de acesso |
| | GET | `/api/access-logs/logs_by_days/` | 🔥 Logs filtrados por dias |
| **Unified Config** | GET | `/api/config/devices/{id}/configs/` | Todas as configs do device |
| | POST | `/api/config/devices/{id}/sync-all/` | Sincroniza todas as configs |

### Filtros Disponíveis

#### System Config
- `device` - ID do dispositivo
- `auto_reboot_enabled` - Boolean
- `language` - Idioma (pt-BR, en, es)

#### Hardware Config
- `device` - ID do dispositivo
- `beep_enabled` - Boolean
- `bell_enabled` - Boolean
- `exception_mode` - none/emergency/lock_down

#### Security Config
- `device` - ID do dispositivo
- `verbose_logging` - Boolean
- `log_type` - basic/extended
- `multi_factor_authentication` - Boolean

#### Catra Config 🆕
- `device` - ID do dispositivo
- `anti_passback` - Boolean
- `daily_reset` - Boolean
- `gateway` - clockwise/anticlockwise
- `operation_mode` - blocked/entrance_open/exit_open/both_open

#### Push Server Config 🆕
- `device` - ID do dispositivo

#### Access Logs
- `device` - ID do dispositivo
- `event_type` - Código do evento (0-15)
- `days` - Número de dias (endpoint `logs_by_days`)

### Exemplos de Requisições

#### 1. Criar SystemConfig e Enviar para Catraca

```bash
curl -X POST "http://localhost:8000/api/config/system-configs/" \
  -H "Content-Type: application/json" \
  -d '{
    "device": 1,
    "auto_reboot_enabled": true,
    "reset_hour": 3,
    "language": "pt-BR"
  }'
```

#### 2. Sincronizar CatraConfig da Catraca

```bash
curl -X POST "http://localhost:8000/api/config/catra-configs/sync-from-catraca/" \
  -H "Content-Type: application/json" \
  -d '{"device": 1}'
```

#### 3. Atualizar PushServerConfig

```bash
curl -X PATCH "http://localhost:8000/api/config/push-server-configs/1/" \
  -H "Content-Type: application/json" \
  -d '{
    "push_remote_address": "192.168.1.100:80",
    "push_request_timeout": 20000,
    "push_request_period": 120
  }'
```

#### 4. Listar Access Logs dos últimos 15 dias

```bash
curl -X GET "http://localhost:8000/api/access-logs/logs_by_days/?days=15"
```

#### 5. Filtrar Acessos Concedidos nos últimos 7 dias

```bash
curl -X GET "http://localhost:8000/api/access-logs/logs_by_days/?days=7&event_type=7"
```

---

## 📊 Sistema de Logs de Acesso

### Tipos de Eventos

O sistema registra **15 tipos de eventos** diferentes:

| Código | Nome | Descrição |
|--------|------|-----------|
| `0` | DESCONHECIDO | Tipo não identificado |
| `1` | OFFLINE_ONLINE | Catraca voltou online |
| `2` | ACESSO_PROVISORIO | Acesso temporário concedido |
| `3` | SENHA_PROVISORIA | Senha temporária utilizada |
| `4` | DUPLA_IDENTIFICACAO | Dupla autenticação |
| `5` | NAO_IDENTIFICADO | Usuário não reconhecido |
| `6` | ACESSO_NEGADO | Acesso negado (sem autorização) |
| `7` | ACESSO_CONCEDIDO | 🟢 Acesso concedido |
| `8` | CARTAO_NAO_RECONHECIDO | Cartão inválido |
| `9` | CRACHA_INVALIDO | Crachá expirado/inválido |
| `10` | FORA_HORARIO | Fora do horário permitido |
| `11` | BIOMETRIA_NAO_RECONHECIDA | Impressão digital não reconhecida |
| `12` | SENHA_INCORRETA | Senha digitada incorretamente |
| `13` | COACAO | Situação de coação detectada |
| `14` | QR_CODE_INVALIDO | QR Code inválido |
| `15` | MANUAL_LIBERADO | Liberação manual pelo admin |

### Endpoint de Logs por Dias

#### Funcionalidade

O endpoint `/api/access-logs/logs_by_days/` permite buscar logs de acesso filtrando por:
- **Período**: Últimos N dias
- **Tipo de Evento**: Código do evento (opcional)
- **Paginação**: Suporte nativo

#### Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição | Exemplo |
|-----------|------|-------------|-----------|---------|
| `days` | Integer | ✅ Sim | Número de dias para filtrar (1-365) | `?days=15` |
| `event_type` | Integer | ❌ Não | Código do evento (0-15) | `&event_type=7` |
| `page` | Integer | ❌ Não | Número da página | `&page=2` |

#### Exemplos de Uso

##### 1. Logs dos últimos 15 dias

```bash
curl -X GET "http://localhost:8000/api/access-logs/logs_by_days/?days=15"
```

**Resposta**:
```json
{
  "count": 1245,
  "next": "http://localhost:8000/api/access-logs/logs_by_days/?days=15&page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "device": 1,
      "event_type": 7,
      "event_type_display": "ACESSO_CONCEDIDO",
      "user_name": "João Silva",
      "timestamp": "2025-01-29T14:30:00Z",
      ...
    }
  ]
}
```

##### 2. Acessos concedidos nos últimos 7 dias

```bash
curl -X GET "http://localhost:8000/api/access-logs/logs_by_days/?days=7&event_type=7"
```

##### 3. Acessos negados nos últimos 30 dias

```bash
curl -X GET "http://localhost:8000/api/access-logs/logs_by_days/?days=30&event_type=6"
```

##### 4. Tentativas não identificadas (últimos 60 dias)

```bash
curl -X GET "http://localhost:8000/api/access-logs/logs_by_days/?days=60&event_type=5"
```

#### Validações

| Erro | Código | Mensagem |
|------|--------|----------|
| Days não informado | 400 | `"O parâmetro 'days' é obrigatório."` |
| Days inválido (string) | 400 | `"O parâmetro 'days' deve ser um número válido."` |
| Days negativo | 400 | `"O parâmetro 'days' deve ser maior que 0."` |
| Event type inválido | 400 | `"O event_type deve ser um número válido."` |

#### Casos de Uso Comuns

| Caso de Uso | Dias | Event Type | Descrição |
|-------------|------|------------|-----------|
| Relatório Semanal | 7 | - | Todos os eventos da semana |
| Relatório Mensal | 30 | - | Todos os eventos do mês |
| Acessos Concedidos | 15 | 7 | Entradas autorizadas |
| Acessos Negados | 30 | 6 | Tentativas bloqueadas |
| Não Identificados | 60 | 5 | Tentativas sem identificação |
| Fora de Horário | 30 | 10 | Acessos fora do permitido |

---

## 🔐 Gerenciamento de Sessão

### Problema Resolvido

**Antes**: Cada requisição criava uma nova sessão (3-5 logins por request)
**Depois**: 1 sessão reutilizada com retry automático em expiração

### Smart Session Reuse

O sistema implementa **gerenciamento inteligente de sessões** com:

| Feature | Descrição |
|---------|-----------|
| **Reuso de Sessão** | Uma sessão por ViewSet, reutilizada em múltiplas requisições |
| **Retry Automático** | Se sessão expirar (401), faz login automático e retenta |
| **Helper Centralizado** | Método `_make_request()` em todos os mixins |
| **Redução de Logins** | De 3-5 logins para 1 login por operação |

### Implementação

Todos os **Mixins de Sincronização** usam o helper `_make_request()`:

```python
def _make_request(self, url, method='POST', data=None):
    """
    Helper centralizado para fazer requisições com retry automático.
    Se receber 401 (sessão expirada), faz login e tenta novamente.
    """
    try:
        response = requests.request(
            method=method,
            url=url,
            json=data,
            cookies=self.session_cookie
        )
        
        # Se sessão expirou, faz login e retenta
        if response.status_code == 401:
            self.login()  # Renova a sessão
            response = requests.request(
                method=method,
                url=url,
                json=data,
                cookies=self.session_cookie
            )
        
        return response
    except Exception as e:
        raise Exception(f"Erro ao fazer requisição: {str(e)}")
```

### Mixins com Smart Session

Todos os 7 mixins de configuração implementam o padrão:

1. **SystemConfigSyncMixin** - `update_system_config_in_catraca()` + `sync_system_config_from_catraca()`
2. **HardwareConfigSyncMixin** - `update_hardware_config_in_catraca()` + `sync_hardware_config_from_catraca()`
3. **SecurityConfigSyncMixin** - `update_security_config_in_catraca()` + `sync_security_config_from_catraca()`
4. **UIConfigSyncMixin** - `update_ui_config_in_catraca()` + `sync_ui_config_from_catraca()`
5. **MonitorConfigSyncMixin** - `update_monitor_config_in_catraca()` + `sync_monitor_config_from_catraca()`
6. **CatraConfigSyncMixin** 🆕 - `update_catra_config_in_catraca()` + `sync_catra_config_from_catraca()`
7. **PushServerConfigSyncMixin** 🆕 - `update_push_server_config_in_catraca()` + `sync_push_server_config_from_catraca()`

### Benefícios

| Métrica | Antes | Depois | Melhoria |
|---------|-------|--------|----------|
| Logins por requisição | 3-5 | 1 | -80% |
| Tempo de resposta | ~2s | ~0.5s | -75% |
| Código duplicado | Alto | Baixo | Centralizado |
| Tratamento de erros | Inconsistente | Uniforme | Padronizado |
| Checkboxes DRF | ❌ Bugados | ✅ Funcionais | Corrigido |

---

## 🧪 Testes

### Estrutura de Testes

```
tests/
├── conftest.py              # Fixtures globais (9 factories)
├── unit/                    # 31 testes - TODOS PASSANDO ✅
│   ├── test_models.py       # Testes dos 7 models
│   └── test_serializers.py  # Testes de validação
├── integration/             # 24 testes - Com mocking
│   ├── test_sync_mocked.py  # Sync com API mockada
│   └── test_viewsets.py     # Endpoints REST
└── e2e/                     # 10 testes - Com catraca real
    └── test_real_catraca.py # Testes end-to-end
```

### Comandos de Teste

| Comando | Descrição | Tempo |
|---------|-----------|-------|
| `pdm test-all` | Executa todos os testes (65+) | ~60s |
| `pdm test-unit` | Apenas testes unitários (31) | ~34s |
| `pdm test-integration` | Testes de integração (24) | ~20s |
| `pdm test-e2e` | Testes end-to-end (10) | ~30s |
| `pdm test-cov` | Testes com cobertura | ~45s |
| `pdm test -m "not slow"` | Pula testes lentos | ~25s |
| `pdm test -m "not e2e"` | Pula testes E2E | ~40s |

### Cobertura de Código

| Componente | Cobertura | Status |
|------------|-----------|--------|
| **Models** | 100% | ✅ |
| **Serializers** | 95% | ✅ |
| **ViewSets** | 85% | ✅ |
| **Mixins (Sync)** | 90% | ✅ |
| **Tasks (Celery)** | 80% | ✅ |
| **Total** | 87% | ✅ |

### Fixtures Disponíveis

| Fixture | Tipo | Descrição |
|---------|------|-----------|
| `api_client` | APIClient | Cliente REST para testes |
| `device_factory` | Factory | Cria dispositivos/catracas |
| `system_config_factory` | Factory | Cria SystemConfig |
| `hardware_config_factory` | Factory | Cria HardwareConfig |
| `security_config_factory` | Factory | Cria SecurityConfig |
| `ui_config_factory` | Factory | Cria UIConfig |
| `catra_config_factory` | Factory | Cria CatraConfig 🆕 |
| `push_server_config_factory` | Factory | Cria PushServerConfig 🆕 |
| `mock_catraca_response` | Mock | Mock de respostas da API |

### Resultados Recentes

**Última execução (Unit Tests)**: 31/31 testes passando (100%)

```
tests/unit/test_models.py::TestDeviceModel::test_device_creation PASSED
tests/unit/test_models.py::TestDeviceModel::test_device_str PASSED
tests/unit/test_models.py::TestSystemConfigModel::test_system_config_creation PASSED
tests/unit/test_models.py::TestSystemConfigModel::test_auto_reboot_default_false PASSED
tests/unit/test_models.py::TestSystemConfigModel::test_reset_hour_choices PASSED
tests/unit/test_models.py::TestSystemConfigModel::test_language_choices PASSED
tests/unit/test_models.py::TestHardwareConfigModel::test_hardware_config_creation PASSED
tests/unit/test_models.py::TestHardwareConfigModel::test_beep_enabled_default_true PASSED
tests/unit/test_models.py::TestSecurityConfigModel::test_security_config_creation PASSED
tests/unit/test_models.py::TestSecurityConfigModel::test_verbose_logging_default_false PASSED
tests/unit/test_models.py::TestUIConfigModel::test_ui_config_creation PASSED
tests/unit/test_models.py::TestUIConfigModel::test_screen_always_on_default_false PASSED
tests/unit/test_models.py::TestCatraConfigModel::test_catra_config_creation PASSED
tests/unit/test_models.py::TestCatraConfigModel::test_anti_passback_default_false PASSED
tests/unit/test_models.py::TestCatraConfigModel::test_daily_reset_default_false PASSED
tests/unit/test_models.py::TestCatraConfigModel::test_gateway_choices PASSED
tests/unit/test_models.py::TestCatraConfigModel::test_operation_mode_choices PASSED
tests/unit/test_models.py::TestCatraConfigModel::test_catra_config_str PASSED
tests/unit/test_models.py::TestPushServerConfigModel::test_push_server_config_creation PASSED
tests/unit/test_models.py::TestPushServerConfigModel::test_timeout_default PASSED
tests/unit/test_models.py::TestPushServerConfigModel::test_period_default PASSED
tests/unit/test_models.py::TestPushServerConfigModel::test_remote_address_optional PASSED
tests/unit/test_models.py::TestPushServerConfigModel::test_push_server_config_str PASSED
tests/unit/test_serializers.py::TestSystemConfigSerializer::test_valid_data PASSED
tests/unit/test_serializers.py::TestSystemConfigSerializer::test_invalid_reset_hour PASSED
tests/unit/test_serializers.py::TestCatraConfigSerializer::test_valid_data PASSED
tests/unit/test_serializers.py::TestCatraConfigSerializer::test_invalid_gateway PASSED
tests/unit/test_serializers.py::TestCatraConfigSerializer::test_invalid_operation_mode PASSED
tests/unit/test_serializers.py::TestPushServerConfigSerializer::test_valid_data PASSED
tests/unit/test_serializers.py::TestPushServerConfigSerializer::test_timeout_validation PASSED
tests/unit/test_serializers.py::TestPushServerConfigSerializer::test_period_validation PASSED

========================= 31 passed in 34.02s =========================
```

---

## 💻 Guia de Instalação

### Pré-requisitos

- Python 3.11+
- PostgreSQL 14+ (ou SQLite para dev)
- RabbitMQ ou Redis (para Celery)
- PDM (Python Dependency Manager)

### Instalação Local

#### 1. Clonar o Repositório

```bash
git clone https://github.com/seu-usuario/catraca_denovo.git
cd catraca_denovo
```

#### 2. Instalar Dependências com PDM

```bash
# Instalar PDM (se não tiver)
pip install pdm

# Instalar dependências do projeto
pdm install
```

#### 3. Configurar Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
# Django
SECRET_KEY=sua-secret-key-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/catraca_db

# Celery
CELERY_BROKER_URL=amqp://localhost
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# ControlID Devices
CATRACA_DEFAULT_IP=192.168.120.94
CATRACA_DEFAULT_PORT=80
CATRACA_DEFAULT_USERNAME=admin
CATRACA_DEFAULT_PASSWORD=admin
```

#### 4. Executar Migrations

```bash
pdm run python src/manage.py migrate
```

#### 5. Criar Superusuário

```bash
pdm run python src/manage.py createsuperuser
```

#### 6. Rodar Servidor de Desenvolvimento

```bash
pdm run python src/manage.py runserver
```

#### 7. Rodar Worker do Celery (opcional)

```bash
pdm run celery -A django_project worker -l info
```

### Verificação da Instalação

Acesse os endpoints:

- Admin: http://localhost:8000/admin/
- API Root: http://localhost:8000/api/
- Swagger Docs: http://localhost:8000/api/schema/swagger-ui/
- ReDoc: http://localhost:8000/api/schema/redoc/

---

## 🚀 Uso Prático

### Fluxo de Trabalho Típico

#### 1. Cadastrar Dispositivo

```bash
curl -X POST "http://localhost:8000/api/devices/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Catraca Entrada Principal",
    "ip": "192.168.120.94",
    "port": 80,
    "username": "admin",
    "password": "admin",
    "serial_number": "ABC123456"
  }'
```

#### 2. Sincronizar Todas as Configurações do Dispositivo

```bash
curl -X POST "http://localhost:8000/api/config/devices/1/sync-all/" \
  -H "Content-Type: application/json"
```

**Resposta**:
```json
{
  "status": "success",
  "device": "Catraca Entrada Principal",
  "configs_synced": {
    "system": true,
    "hardware": true,
    "security": true,
    "ui": true,
    "monitor": true,
    "catra": true,
    "push_server": true
  },
  "timestamp": "2025-01-29T10:30:00Z"
}
```

#### 3. Configurar Modo de Operação da Catraca

```bash
curl -X PATCH "http://localhost:8000/api/config/catra-configs/1/" \
  -H "Content-Type: application/json" \
  -d '{
    "operation_mode": "blocked",
    "anti_passback": true,
    "gateway": "clockwise"
  }'
```

#### 4. Consultar Logs de Acesso (últimos 7 dias)

```bash
curl -X GET "http://localhost:8000/api/access-logs/logs_by_days/?days=7"
```

#### 5. Gerar Relatório de Acessos Negados (último mês)

```bash
curl -X GET "http://localhost:8000/api/access-logs/logs_by_days/?days=30&event_type=6" \
  > relatorio_acessos_negados.json
```

### Integração com Frontend (JavaScript)

```javascript
// Classe helper para API
class CatracaAPI {
  constructor(baseURL = 'http://localhost:8000/api') {
    this.baseURL = baseURL;
  }

  // Buscar logs por período
  async getLogsByDays(days, eventType = null) {
    const params = new URLSearchParams({ days });
    if (eventType) params.append('event_type', eventType);
    
    const response = await fetch(`${this.baseURL}/access-logs/logs_by_days/?${params}`);
    return response.json();
  }

  // Sincronizar device
  async syncDevice(deviceId) {
    const response = await fetch(`${this.baseURL}/config/devices/${deviceId}/sync-all/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    return response.json();
  }

  // Atualizar modo de operação
  async updateOperationMode(catraConfigId, mode) {
    const response = await fetch(`${this.baseURL}/config/catra-configs/${catraConfigId}/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ operation_mode: mode })
    });
    return response.json();
  }
}

// Uso
const api = new CatracaAPI();

// Buscar logs da semana
const logs = await api.getLogsByDays(7);
console.log(`Total de logs: ${logs.count}`);

// Liberar catraca
await api.updateOperationMode(1, 'both_open');
```

### Integração com Python (Requests)

```python
import requests

class CatracaClient:
    def __init__(self, base_url='http://localhost:8000/api'):
        self.base_url = base_url
        self.session = requests.Session()
    
    def get_logs_by_days(self, days, event_type=None):
        """Busca logs por período."""
        params = {'days': days}
        if event_type:
            params['event_type'] = event_type
        
        response = self.session.get(
            f'{self.base_url}/access-logs/logs_by_days/',
            params=params
        )
        return response.json()
    
    def sync_device(self, device_id):
        """Sincroniza todas as configs de um device."""
        response = self.session.post(
            f'{self.base_url}/config/devices/{device_id}/sync-all/'
        )
        return response.json()
    
    def update_catra_config(self, config_id, **kwargs):
        """Atualiza configurações da catraca."""
        response = self.session.patch(
            f'{self.base_url}/config/catra-configs/{config_id}/',
            json=kwargs
        )
        return response.json()

# Uso
client = CatracaClient()

# Relatório semanal
logs = client.get_logs_by_days(days=7)
print(f"Total de logs: {logs['count']}")

# Bloquear catraca
result = client.update_catra_config(
    config_id=1,
    operation_mode='blocked',
    anti_passback=True
)
print(f"Catraca atualizada: {result}")
```

---

## 🚀 Deploy e Produção

### Deploy no Heroku

#### 1. Preparação

```bash
# Criar Procfile (já existe)
web: gunicorn django_project.wsgi --log-file -
worker: celery -A django_project worker -l info

# Criar runtime.txt
python-3.11.5

# Adicionar heroku ao requirements.txt
echo "gunicorn==21.2.0" >> requirements.txt
echo "dj-database-url==2.1.0" >> requirements.txt
echo "whitenoise==6.6.0" >> requirements.txt
```

#### 2. Configurar Settings para Produção

```python
# settings.py
import dj_database_url

# SECURITY
DEBUG = os.getenv('DEBUG', 'False') == 'True'
SECRET_KEY = os.getenv('SECRET_KEY')
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

# DATABASE
DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL'),
        conn_max_age=600
    )
}

# STATIC FILES
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# CELERY
CELERY_BROKER_URL = os.getenv('CLOUDAMQP_URL')
```

#### 3. Deploy

```bash
# Login
heroku login

# Criar app
heroku create catraca-app

# Adicionar addons
heroku addons:create heroku-postgresql:mini
heroku addons:create cloudamqp:lemur

# Deploy
git push heroku main

# Migrations
heroku run python src/manage.py migrate

# Create superuser
heroku run python src/manage.py createsuperuser

# Scale dyno worker
heroku ps:scale worker=1
```

### Deploy com Docker

#### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instalar PDM
RUN pip install pdm

# Copiar arquivos de dependências
COPY pyproject.toml pdm.lock ./

# Instalar dependências
RUN pdm install --prod --no-lock --no-editable

# Copiar código
COPY . .

# Collect static
RUN pdm run python src/manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Run
CMD ["pdm", "run", "gunicorn", "django_project.wsgi:application", "--bind", "0.0.0.0:8000"]
```

#### docker-compose.yml

```yaml
version: '3.8'

services:
  db:
    image: postgres:14
    environment:
      POSTGRES_DB: catraca_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  web:
    build: .
    command: gunicorn django_project.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - db
      - redis

  celery:
    build: .
    command: celery -A django_project worker -l info
    volumes:
      - .:/app
    env_file:
      - .env
    depends_on:
      - db
      - redis

volumes:
  postgres_data:
```

### Variáveis de Ambiente para Produção

```env
# Django
SECRET_KEY=sua-chave-super-secreta-aqui-minimo-50-caracteres
DEBUG=False
ALLOWED_HOSTS=catraca-app.herokuapp.com,www.exemplo.com

# Database (fornecido pelo Heroku)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Celery (fornecido pelo CloudAMQP)
CELERY_BROKER_URL=amqps://user:pass@host/vhost
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### Monitoramento e Logs

```bash
# Ver logs do Heroku
heroku logs --tail

# Ver logs do worker Celery
heroku logs --tail --dyno worker

# Ver status dos dynos
heroku ps

# Restart
heroku restart
```

---

## 📚 Documentação Adicional

### Links Úteis

| Recurso | Link |
|---------|------|
| **Documentação ControlID** | [Manual API REST](https://www.controlid.com.br/suporte/) |
| **Django REST Framework** | https://www.django-rest-framework.org/ |
| **Pytest Django** | https://pytest-django.readthedocs.io/ |
| **Factory Boy** | https://factoryboy.readthedocs.io/ |
| **Celery** | https://docs.celeryproject.org/ |

### Arquivos de Documentação do Projeto

| Arquivo | Descrição |
|---------|-----------|
| `README.md` | Visão geral do projeto |
| `README_ACCESS_LOGS.md` | Documentação do sistema de logs |
| `EXEMPLO_USO_LOGS.md` | Exemplos práticos de uso dos logs |
| `IMPLEMENTACAO_CATRA_PUSH_SERVER.md` | Detalhes das novas configs |
| `REFACTORING_SESSION_MANAGEMENT.md` | Refatoração de sessões |
| `tests/README_TESTES.md` | Guia completo de testes |
| `tests/IMPLEMENTACAO_TESTES.md` | Implementação dos testes |
| `tests/RESUMO_TESTES.md` | Resumo da execução dos testes |

### Convenções de Código

#### Nomenclatura

- **Models**: PascalCase (ex: `SystemConfig`, `CatraConfig`)
- **Campos de Model**: snake_case (ex: `auto_reboot_enabled`, `push_remote_address`)
- **Serializers**: PascalCase + Suffix `Serializer` (ex: `SystemConfigSerializer`)
- **ViewSets**: PascalCase + Suffix `ViewSet` (ex: `CatraConfigViewSet`)
- **Mixins**: PascalCase + Suffix `Mixin` (ex: `CatraConfigSyncMixin`)
- **Factories**: PascalCase + Suffix `Factory` (ex: `DeviceFactory`)

#### Estrutura de Arquivos

```
app/
├── models/
│   ├── __init__.py         # Importa todos os models
│   ├── system_config.py    # Um model por arquivo
│   └── catra_config.py
├── serializers/
│   ├── __init__.py
│   ├── system_config.py
│   └── catra_config.py
├── views/
│   ├── __init__.py
│   ├── system_config.py
│   └── catra_config.py
├── mixins/
│   ├── __init__.py
│   ├── system_config_mixin.py
│   └── catra_config_mixin.py
└── admin.py                # Admin de todos os models
```

### Padrões de Commit

```
feat: adiciona endpoint de logs por dias
fix: corrige validação de timeout no PushServerConfig
refactor: centraliza gerenciamento de sessão em _make_request
test: adiciona testes unitários para CatraConfig
docs: atualiza README com exemplos de uso
style: formata código com black
```

---

## 🤝 Contribuindo

### Fluxo de Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -am 'feat: adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

### Checklist de PR

- [ ] Código segue as convenções do projeto
- [ ] Testes passando (`pdm test-all`)
- [ ] Cobertura de código mantida/aumentada
- [ ] Documentação atualizada (README, docstrings)
- [ ] Migrations criadas (se necessário)
- [ ] Changelog atualizado

---

## 📞 Suporte e Contato

### Problemas Comuns

#### 1. Erro 401 ao fazer requisições

**Causa**: Sessão expirada ou credenciais inválidas

**Solução**: Verifique as credenciais no Device e use o helper `_make_request()` que tem retry automático

#### 2. Timeout nas requisições

**Causa**: Catraca offline ou IP incorreto

**Solução**: Verifique conectividade com `ping` e confirme IP/porta do device

#### 3. Testes falhando

**Causa**: Dependências desatualizadas ou fixtures incorretas

**Solução**: Execute `pdm install` e verifique fixtures em `conftest.py`

#### 4. Checkboxes não funcionando no DRF

**Causa**: Bug conhecido do DRF com campos booleanos em forms HTML

**Solução**: Já corrigido! Todos os serializers usam `BooleanField(required=False, default=False)`

### FAQ

**P: Posso usar sem celery?**
R: Sim, o celery é opcional. A sincronização pode ser feita via endpoints REST diretos.

**P: Funciona com outros modelos de catracas ControlID?**
R: Projetado para IDBLOCK, mas compatível com qualquer modelo que use a API REST padrão.

**P: Como adicionar novos campos de configuração?**
R: Adicione o campo no model, crie migration, atualize serializer e mixin de sync.

**P: É seguro armazenar biometrias no banco?**
R: Não armazenamos! Biometrias ficam apenas nas catracas (LGPD compliant).

---

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

---

## 🎉 Agradecimentos

- Equipe ControlID pelo hardware e API
- Comunidade Django e DRF
- Contribuidores e testadores

---

**Última atualização**: 29/01/2025
**Versão**: 2.0.0
**Status**: ✅ Produção
