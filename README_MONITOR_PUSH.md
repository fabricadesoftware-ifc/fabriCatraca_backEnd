# Sistema de Monitor Push - Notificações em Tempo Real

## 📚 Introdução

O **Monitor** é um sistema PUSH da ControlID onde a catraca envia automaticamente notificações para um servidor quando ocorrem eventos, ao invés de termos que ficar fazendo requisições (polling/sync) para buscar os dados.

### Vantagens do Sistema PUSH:
- ⚡ **Tempo Real**: Recebe logs instantaneamente quando alguém passa
- 💰 **Eficiente**: Sem necessidade de ficar fazendo sync periódico
- 📊 **Escalável**: Reduz tráfego de rede significativamente
- 🎯 **Preciso**: Não perde nenhum evento

---

## 🏗️ Arquitetura

```
┌─────────────┐         ┌──────────────────┐         ┌────────────────┐
│   CATRACA   │─────────▶│  NOSSO SERVIDOR  │─────────▶│  BANCO DADOS   │
│             │  POST    │                  │  INSERT  │                │
│  ControlID  │  JSON    │  Django API      │          │  PostgreSQL    │
└─────────────┘         └──────────────────┘         └────────────────┘
                              ▲
                              │
                    Endpoint configurado:
                hostname:port/api/notifications/dao
```

### Fluxo de Dados:

1. **Configuração**: Admin configura o MonitorConfig com hostname, porta e path
2. **Ativação**: Sistema envia config para a catraca via `set_configuration.fcgi`
3. **Eventos**: Quando alguém passa na catraca, ela automaticamente faz POST para nosso servidor
4. **Processamento**: Servidor recebe JSON, valida e salva no banco
5. **Disponibilização**: Dados ficam disponíveis via API REST

---

## 🚀 Como Usar

### 1️⃣ Configurar o Monitor na Catraca

**Endpoint**: `POST /api/control_id_monitor/monitor-configs/`

```json
{
    "device": 1,
    "hostname": "meuservidor.com.br",  // ou IP: "192.168.0.20"
    "port": "8000",
    "path": "api/control_id_monitor/notifications/dao",  // path padrão
    "request_timeout": 5000  // timeout em ms (padrão: 5000)
}
```

**Resposta**:
```json
{
    "id": 1,
    "device": 1,
    "device_name": "Catraca Principal",
    "hostname": "meuservidor.com.br",
    "port": "8000",
    "path": "api/control_id_monitor/notifications/dao",
    "request_timeout": 5000,
    "is_configured": true,
    "full_url": "http://meuservidor.com.br:8000/api/control_id_monitor/notifications/dao",
    "notification_url": "http://meuservidor.com.br:8000/api/control_id_monitor/notifications/dao",
    "status": "✓ Ativo"
}
```

### 2️⃣ Ativar o Monitor

Depois de criar o config, use o endpoint de ativação para enviar para a catraca:

**Endpoint**: `POST /api/control_id_monitor/monitor-configs/{id}/activate/`

```bash
curl -X POST http://localhost:8000/api/control_id_monitor/monitor-configs/1/activate/
```

**Resposta**:
```json
{
    "success": true,
    "message": "Monitor ativado com sucesso",
    "config": { ... }
}
```

### 3️⃣ Receber Notificações

A catraca vai começar a enviar notificações automaticamente para:

**Endpoint**: `POST /api/control_id_monitor/notifications/dao/`

**Não precisa fazer nada!** O endpoint está configurado para receber automaticamente.

---

## 📥 Formato das Notificações

### Estrutura Geral

```json
{
    "object_changes": [
        {
            "object": "access_logs",
            "type": "inserted",
            "values": {
                "id": "519",
                "time": "1532977090",
                "event": "12",
                "device_id": "478435",
                "identifier_id": "0",
                "user_id": "0",
                "portal_id": "1",
                "card_value": "0",
                "log_type_id": "-1"
            }
        }
    ],
    "device_id": 478435
}
```

### Tipos de Objetos (`object`)

| Objeto | Descrição |
|--------|-----------|
| `access_logs` | Logs de acesso (entrada/saída) |
| `templates` | Templates biométricos |
| `cards` | Cartões RFID |
| `alarm_logs` | Logs de alarme |

### Tipos de Mudança (`type`)

| Tipo | Descrição |
|------|-----------|
| `inserted` | Novo registro criado |
| `updated` | Registro atualizado |
| `deleted` | Registro deletado |

### Campos de `access_logs`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | string | ID único do log |
| `time` | string | Timestamp Unix (segundos desde 1970) |
| `event` | string | Código do evento (veja tabela abaixo) |
| `device_id` | string | ID do dispositivo |
| `user_id` | string | ID do usuário (se identificado) |
| `portal_id` | string | ID do portal (lado da catraca) |
| `card_value` | string | Valor do cartão RFID |
| `identifier_id` | string | ID do identificador usado |

### Códigos de Eventos

| Código | Evento |
|--------|--------|
| 1 | Equipamento inválido |
| 2 | Parâmetro de identificação inválido |
| 3 | Não identificado |
| 4 | Identificação pendente |
| 5 | Tempo de identificação esgotado |
| 6 | Acesso negado |
| 7 | Acesso concedido |
| 8 | Acesso pendente |
| 9 | Usuário não é admin |
| 10 | Acesso não identificado |
| 11 | Acesso por botoeira |
| 12 | Acesso pela interface web |
| 13 | Desistência de entrada |
| 14 | Sem resposta |
| 15 | Acesso pela interfonia |

---

## 🔍 Endpoints Disponíveis

### Gestão de Configurações

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/control_id_monitor/` | API root com informações |
| GET | `/api/control_id_monitor/monitor-configs/` | Listar todas as configs |
| POST | `/api/control_id_monitor/monitor-configs/` | Criar nova config |
| GET | `/api/control_id_monitor/monitor-configs/{id}/` | Detalhes de uma config |
| PATCH | `/api/control_id_monitor/monitor-configs/{id}/` | Atualizar config |
| DELETE | `/api/control_id_monitor/monitor-configs/{id}/` | Deletar config |

### Ações Especiais

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/control_id_monitor/monitor-configs/{id}/activate/` | Ativar monitor (envia config para catraca) |
| POST | `/api/control_id_monitor/monitor-configs/{id}/deactivate/` | Desativar monitor (limpa config da catraca) |
| POST | `/api/control_id_monitor/monitor-configs/{id}/sync-from-catraca/` | Sincronizar config da catraca |
| GET | `/api/control_id_monitor/monitor-configs/{id}/probe/` | Debug: ver config raw da catraca |
| GET | `/api/control_id_monitor/monitor-configs/probe-by-device/{device_id}/` | Debug: probe por device ID |

### Webhook (Recebe Notificações)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/control_id_monitor/notifications/dao/` | **Endpoint para catraca enviar logs** |

---

## 🧪 Testando o Sistema

### 1. Criar Configuração

```bash
curl -X POST http://localhost:8000/api/control_id_monitor/monitor-configs/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -d '{
    "device": 1,
    "hostname": "192.168.0.100",
    "port": "8000",
    "path": "api/control_id_monitor/notifications/dao",
    "request_timeout": 5000
  }'
```

### 2. Ativar Monitor

```bash
curl -X POST http://localhost:8000/api/control_id_monitor/monitor-configs/1/activate/ \
  -H "Authorization: Bearer SEU_TOKEN"
```

### 3. Simular Notificação da Catraca (Debug)

```bash
curl -X POST http://localhost:8000/api/control_id_monitor/notifications/dao/ \
  -H "Content-Type: application/json" \
  -d '{
    "object_changes": [
      {
        "object": "access_logs",
        "type": "inserted",
        "values": {
          "id": "999",
          "time": "1609459200",
          "event": "7",
          "device_id": "1",
          "user_id": "123",
          "portal_id": "1",
          "card_value": "987654321"
        }
      }
    ],
    "device_id": 1
  }'
```

### 4. Verificar Logs Recebidos

```bash
curl http://localhost:8000/api/control_id/access-logs/ \
  -H "Authorization: Bearer SEU_TOKEN"
```

---

## 🐛 Debug e Troubleshooting

### Verificar Configuração na Catraca

```bash
curl -X GET "http://localhost:8000/api/control_id_monitor/monitor-configs/1/probe/" \
  -H "Authorization: Bearer SEU_TOKEN"
```

**Resposta**:
```json
{
    "success": true,
    "monitor": {
        "request_timeout": 5000,
        "hostname": "192.168.0.100",
        "port": "8000",
        "path": "api/control_id_monitor/notifications/dao"
    },
    "full_url": "http://192.168.0.100:8000/api/control_id_monitor/notifications/dao"
}
```

### Logs do Sistema

Os logs do monitor aparecem com prefixo `[MONITOR]`:

```
📥 [MONITOR] Recebendo 1 mudanças do device 478435
✅ [ACCESS_LOG] Criado log 519 do device Catraca Principal
✅ [MONITOR] Processados 1/1 do device 478435
```

### Problemas Comuns

#### 1. Catraca não está enviando notificações

**Causas possíveis**:
- Monitor não foi ativado (use `/activate/`)
- Hostname/porta incorretos
- Firewall bloqueando conexão
- Servidor não acessível pela catraca

**Solução**:
```bash
# 1. Verificar se monitor está configurado
curl http://localhost:8000/api/control_id_monitor/monitor-configs/1/probe/

# 2. Re-ativar se necessário
curl -X POST http://localhost:8000/api/control_id_monitor/monitor-configs/1/activate/

# 3. Testar conectividade da catraca
ping HOSTNAME_CONFIGURADO
telnet HOSTNAME_CONFIGURADO PORTA_CONFIGURADA
```

#### 2. Notificações sendo recebidas mas não salvando

**Causas possíveis**:
- Device não existe no banco
- Campos obrigatórios faltando

**Solução**:
- Verificar logs do Django
- Confirmar que device_id existe no banco
- Validar estrutura do JSON

#### 3. Timeout nas requisições

**Causas possíveis**:
- `request_timeout` muito baixo
- Servidor lento

**Solução**:
```bash
# Aumentar timeout para 10 segundos
curl -X PATCH http://localhost:8000/api/control_id_monitor/monitor-configs/1/ \
  -H "Content-Type: application/json" \
  -d '{"request_timeout": 10000}'

# Re-enviar para catraca
curl -X POST http://localhost:8000/api/control_id_monitor/monitor-configs/1/activate/
```

---

## 📊 Monitoramento

### Estatísticas de Processamento

Cada notificação retorna estatísticas:

```json
{
    "success": true,
    "device_id": 478435,
    "total_changes": 3,
    "processed": 3,
    "errors": null,
    "results": [
        {
            "success": true,
            "object": "access_logs",
            "action": "created",
            "log_id": "519"
        },
        {
            "success": true,
            "object": "access_logs",
            "action": "created",
            "log_id": "520"
        },
        {
            "success": true,
            "object": "access_logs",
            "action": "created",
            "log_id": "521"
        }
    ]
}
```

### Logs no Console

```
📥 [MONITOR] Recebendo notificação da catraca
📥 [MONITOR] Recebendo 3 mudanças do device 478435
🔄 [MONITOR] Processando access_logs - inserted
✅ [ACCESS_LOG] Criado log 519 do device Catraca Principal
🔄 [MONITOR] Processando access_logs - inserted
✅ [ACCESS_LOG] Criado log 520 do device Catraca Principal
🔄 [MONITOR] Processando access_logs - inserted
✅ [ACCESS_LOG] Criado log 521 do device Catraca Principal
✅ [MONITOR] Processados 3/3 do device 478435
```

---

## 🔐 Segurança

### Autenticação

O endpoint `/notifications/dao/` **não requer autenticação** porque a catraca não envia tokens JWT.

**Recomendações de segurança**:

1. **Firewall**: Aceitar requisições apenas do IP da catraca
2. **Validação**: Sistema valida device_id automaticamente
3. **HTTPS**: Use HTTPS em produção
4. **Rate Limiting**: Configure rate limiting no nginx/proxy

### Exemplo de Configuração Nginx

```nginx
location /api/control_id_monitor/notifications/dao/ {
    # Apenas catraca pode acessar
    allow 192.168.0.50;  # IP da catraca
    deny all;
    
    # Rate limiting
    limit_req zone=monitor burst=100;
    
    proxy_pass http://django:8000;
}
```

---

## 🔄 Diferenças: Monitor PUSH vs Sync PULL

| Aspecto | Monitor (PUSH) | Sync (PULL) |
|---------|----------------|-------------|
| **Iniciativa** | Catraca envia | Servidor busca |
| **Latência** | Tempo real (~ms) | Periódica (minutos) |
| **Tráfego** | Sob demanda | Constante |
| **Eficiência** | Alta | Baixa |
| **Complexidade** | Requer webhook | Mais simples |
| **Confiabilidade** | Depende de rede | Controlada |
| **Uso** | Logs em tempo real | Configurações |

### Quando Usar Cada Um?

**Use Monitor (PUSH)** para:
- ✅ Logs de acesso (access_logs)
- ✅ Eventos em tempo real
- ✅ Alarmes
- ✅ Templates biométricos

**Use Sync (PULL)** para:
- ✅ Configurações (system, hardware, security, UI)
- ✅ Sincronização inicial
- ✅ Recovery após falha
- ✅ Debug

---

## 📝 Notas Importantes

1. **Port e Path**:
   - Port deve ser acessível pela catraca
   - Path padrão: `api/control_id_monitor/notifications/dao`
   - Não inclua http:// ou https:// no hostname

2. **Timeout**:
   - Padrão: 5000ms (5 segundos)
   - Máximo recomendado: 30000ms (30 segundos)
   - Catraca espera por este tempo

3. **Device ID**:
   - Deve existir no banco antes de configurar
   - Validado automaticamente

4. **URL Final**:
   - Construída automaticamente: `http://hostname:port/path`
   - Exemplo: `http://192.168.0.100:8000/api/control_id_monitor/notifications/dao`

5. **Múltiplas Mudanças**:
   - Uma notificação pode conter vários `object_changes`
   - Todas são processadas na mesma transação
   - Se uma falhar, todas falham (atomic)

---

## 🎯 Próximos Passos

1. ✅ Sistema de Monitor implementado e funcionando
2. ✅ Endpoint de notificações criado
3. ✅ Handler de access_logs implementado
4. 📝 Implementar handlers de templates, cards, alarm_logs
5. 📊 Dashboard de monitoramento em tempo real
6. 🔔 Sistema de alertas para eventos específicos
7. 📈 Métricas e estatísticas de uso

---

## 📚 Referências

- [Documentação ControlID - Monitor](https://www.controlid.com.br/docs/)
- [API REST - Access Logs](README_ACCESS_LOGS.md)
- [README Completo](README_COMPLETO.md)
