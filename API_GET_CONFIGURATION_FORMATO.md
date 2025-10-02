# Formato Correto da API get_configuration.fcgi

## 📚 Descoberta Importante

O endpoint `get_configuration.fcgi` da ControlID **NÃO** aceita payload vazio ou com `{"fields": [...]}`.

O formato correto é **ARRAY DE STRINGS** para cada bloco de configuração!

## ✅ Formato CORRETO

### Request

```json
{
    "monitor": [
        "path",
        "hostname",
        "port",
        "request_timeout"
    ]
}
```

### Response

```json
{
    "monitor": {
        "path": "api/notifications/dao",
        "hostname": "192.168.0.100",
        "port": "8000",
        "request_timeout": "5000"
    }
}
```

## 📋 Todos os Blocos Disponíveis

Segundo a documentação ControlID, estes são todos os blocos:

```json
{
    "general": [
        "online",
        "beep_enabled",
        "bell_enabled",
        "bell_relay",
        "catra_timeout",
        "local_identification",
        "exception_mode",
        "language",
        "daylight_savings_time_start",
        "daylight_savings_time_end",
        "auto_reboot"
    ],
    
    "w_in0": ["byte_order"],
    "w_in1": ["byte_order"],
    
    "alarm": [
        "siren_enabled",
        "siren_relay"
    ],
    
    "identifier": [
        "verbose_logging",
        "log_type",
        "multi_factor_authentication"
    ],
    
    "bio_id": ["similarity_threshold_1ton"],
    
    "online_client": [
        "server_id", 
        "extract_template",
        "max_request_attempts"
    ],
    
    "catra": [
        "anti_passback",
        "daily_reset",
        "gateway",
        "operation_mode"
    ],
    
    "bio_module": ["var_min"],
    
    "monitor": [
        "path",
        "hostname",
        "port",
        "request_timeout"
    ],
    
    "push_server": [
        "push_request_timeout",
        "push_request_period",
        "push_remote_address"
    ]
}
```

## 🔄 Diferença: GET vs SET

### GET Configuration (Buscar)

**Formato**: Array de strings (campos que quer buscar)

```json
{
    "monitor": [
        "path",
        "hostname",
        "port",
        "request_timeout"
    ]
}
```

**Endpoint**: `POST /get_configuration.fcgi?session=XXX`

### SET Configuration (Salvar)

**Formato**: Objeto com valores (campos que quer atualizar)

```json
{
    "monitor": {
        "path": "api/notifications/dao",
        "hostname": "192.168.0.100",
        "port": "8000",
        "request_timeout": "5000"
    }
}
```

**Endpoint**: `POST /set_configuration.fcgi?session=XXX`

## 💡 Exemplos Práticos

### 1. Buscar Configuração do Monitor

```bash
curl -X POST "http://192.168.0.50/get_configuration.fcgi?session=ABC123" \
  -H "Content-Type: application/json" \
  -d '{
    "monitor": [
      "path",
      "hostname",
      "port",
      "request_timeout"
    ]
  }'
```

**Resposta** (se configurado):
```json
{
    "monitor": {
        "path": "api/notifications/dao",
        "hostname": "192.168.0.100",
        "port": "8000",
        "request_timeout": "5000"
    }
}
```

**Resposta** (se NÃO configurado):
```json
{
    "monitor": {}
}
```
ou
```json
{
    "monitor": {
        "path": "",
        "hostname": "",
        "port": "",
        "request_timeout": ""
    }
}
```

### 2. Configurar Monitor

```bash
curl -X POST "http://192.168.0.50/set_configuration.fcgi?session=ABC123" \
  -H "Content-Type: application/json" \
  -d '{
    "monitor": {
      "path": "api/control_id_monitor/notifications/dao",
      "hostname": "meuservidor.com",
      "port": "8000",
      "request_timeout": "5000"
    }
  }'
```

**Resposta**:
```json
{
    "success": true
}
```

### 3. Buscar Múltiplos Blocos

```bash
curl -X POST "http://192.168.0.50/get_configuration.fcgi?session=ABC123" \
  -H "Content-Type: application/json" \
  -d '{
    "general": ["online", "beep_enabled"],
    "monitor": ["hostname", "port"],
    "catra": ["gateway", "operation_mode"]
  }'
```

**Resposta**:
```json
{
    "general": {
        "online": "1",
        "beep_enabled": "1"
    },
    "monitor": {
        "hostname": "192.168.0.100",
        "port": "8000"
    },
    "catra": {
        "gateway": "clockwise",
        "operation_mode": "0"
    }
}
```

## 🔧 Implementação no Código

### Antes (ERRADO)

```python
# ❌ ERRADO - Não funciona
payload = {
    "monitor": {}  # Vazio
}

# ❌ ERRADO - Não funciona
payload = {
    "monitor": {
        "fields": ["hostname", "port"]  # Formato incorreto
    }
}
```

### Depois (CORRETO)

```python
# ✅ CORRETO - Funciona!
payload = {
    "monitor": [
        "path",
        "hostname",
        "port",
        "request_timeout"
    ]
}

response = self._make_request("get_configuration.fcgi", json_data=payload)
data = response.json()
monitor_config = data.get("monitor", {})
```

## 🎯 Impacto nas Funcionalidades

### MonitorConfig Sync

**Antes**: Falhava sempre porque usava formato errado

**Depois**: Funciona corretamente!

```python
def sync_monitor_config_from_catraca(self):
    payload = {
        "monitor": [
            "path",
            "hostname", 
            "port",
            "request_timeout"
        ]
    }
    
    response = self._make_request("get_configuration.fcgi", json_data=payload)
    
    if response.status_code == 200:
        data = response.json() or {}
        monitor_data = data.get("monitor", {})
        
        if monitor_data and any(monitor_data.values()):
            # Monitor está configurado!
            return Response({
                "success": True,
                "monitor": monitor_data
            })
        else:
            # Monitor não está configurado (valores vazios)
            return Response({
                "success": False,
                "error": "Monitor não configurado",
                "is_configuration_missing": True
            }, status=404)
```

## 📊 Próximos Logs (Esperados)

### Caso 1: Monitor NÃO Configurado (Normal)

```
[CELERY_SYNC] Sincronizando device: Fabrica
[CELERY_SYNC] ✓ SystemConfig sincronizado
[CELERY_SYNC] ✓ HardwareConfig sincronizado
[CELERY_SYNC] ✓ SecurityConfig sincronizado
[CELERY_SYNC] ✓ UIConfig sincronizado
[CELERY_SYNC] ℹ️ MonitorConfig não configurado no device Fabrica (normal)
[CELERY_SYNC] ✓ CatraConfig sincronizado
[CELERY_SYNC] ✓ PushServerConfig sincronizado
```

```json
{
    "stats": {
        "monitor_synced": 0,
        "errors": []  // ✅ Sem erros!
    }
}
```

### Caso 2: Monitor Configurado

```
[CELERY_SYNC] Sincronizando device: Fabrica
[CELERY_SYNC] ✓ SystemConfig sincronizado
[CELERY_SYNC] ✓ HardwareConfig sincronizado
[CELERY_SYNC] ✓ SecurityConfig sincronizado
[CELERY_SYNC] ✓ UIConfig sincronizado
[CELERY_SYNC] ✓ MonitorConfig sincronizado
[CELERY_SYNC] ✓ CatraConfig sincronizado
[CELERY_SYNC] ✓ PushServerConfig sincronizado
```

```json
{
    "stats": {
        "monitor_synced": 1,  // ✅ Sincronizado!
        "errors": []
    }
}
```

## 🚀 Como Testar

### 1. Via Postman/Insomnia

```http
POST http://192.168.0.50/get_configuration.fcgi?session=SEU_SESSION_ID
Content-Type: application/json

{
    "monitor": [
        "path",
        "hostname",
        "port",
        "request_timeout"
    ]
}
```

### 2. Via Django Shell

```python
from src.core.control_Id.infra.control_id_django_app.models import Device
from src.core.control_id_monitor.infra.control_id_monitor_django_app.mixins import MonitorConfigSyncMixin

device = Device.objects.first()
mixin = MonitorConfigSyncMixin()
mixin.set_device(device)

# Testa sync
result = mixin.sync_monitor_config_from_catraca()
print(result.data)
```

### 3. Via API REST

```bash
GET /api/control_id_monitor/monitor-configs/1/probe/
```

## 📝 Resumo

| Aspecto | Formato |
|---------|---------|
| **Endpoint GET** | `get_configuration.fcgi` |
| **Payload GET** | `{"bloco": ["campo1", "campo2"]}` ← Array |
| **Endpoint SET** | `set_configuration.fcgi` |
| **Payload SET** | `{"bloco": {"campo1": "valor1"}}` ← Object |
| **Resposta** | `{"bloco": {"campo1": "valor1"}}` |

---

**Correção aplicada com sucesso!** Agora o sync do monitor deve funcionar corretamente. 🎉
