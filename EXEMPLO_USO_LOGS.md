# Exemplos Práticos - Logs por Dias

## Como Testar a Nova Funcionalidade

### 1. Teste Básico - Logs dos últimos 15 dias

```bash
curl -X GET "http://localhost:8000/api/access-logs/logs_by_days/?days=15" \
  -H "Content-Type: application/json"
```

### 2. Teste com Filtro por Tipo de Evento

```bash
# Logs dos últimos 7 dias apenas com acessos concedidos
curl -X GET "http://localhost:8000/api/access-logs/logs_by_days/?days=7&event_type=7" \
  -H "Content-Type: application/json"

# Logs dos últimos 30 dias apenas com acessos negados
curl -X GET "http://localhost:8000/api/access-logs/logs_by_days/?days=30&event_type=6" \
  -H "Content-Type: application/json"
```

### 3. Teste com Paginação

```bash
# Primeira página
curl -X GET "http://localhost:8000/api/access-logs/logs_by_days/?days=15&page=1" \
  -H "Content-Type: application/json"

# Segunda página
curl -X GET "http://localhost:8000/api/access-logs/logs_by_days/?days=15&page=2" \
  -H "Content-Type: application/json"
```

### 4. Teste de Validação de Erros

```bash
# Teste com dias inválidos (deve retornar erro 400)
curl -X GET "http://localhost:8000/api/access-logs/logs_by_days/?days=-5" \
  -H "Content-Type: application/json"

# Teste com dias como string (deve retornar erro 400)
curl -X GET "http://localhost:8000/api/access-logs/logs_by_days/?days=abc" \
  -H "Content-Type: application/json"

# Teste com event_type inválido (deve retornar erro 400)
curl -X GET "http://localhost:8000/api/access-logs/logs_by_days/?days=15&event_type=999" \
  -H "Content-Type: application/json"
```

### 5. Exemplos com JavaScript/Fetch

```javascript
// Logs dos últimos 30 dias
fetch('/api/access-logs/logs_by_days/?days=30')
  .then(response => response.json())
  .then(data => {
    console.log('Total de logs:', data.count);
    console.log('Logs:', data.results);
  });

// Logs dos últimos 7 dias com acessos concedidos
fetch('/api/access-logs/logs_by_days/?days=7&event_type=7')
  .then(response => response.json())
  .then(data => {
    console.log('Acessos concedidos nos últimos 7 dias:', data.results);
  });
```

### 6. Exemplos com Python/Requests

```python
import requests

# Logs dos últimos 15 dias
response = requests.get('http://localhost:8000/api/access-logs/logs_by_days/', 
                       params={'days': 15})
logs = response.json()
print(f"Total de logs: {logs['count']}")

# Logs dos últimos 30 dias com acessos negados
response = requests.get('http://localhost:8000/api/access-logs/logs_by_days/', 
                       params={'days': 30, 'event_type': 6})
accessos_negados = response.json()
print(f"Acessos negados: {len(accessos_negados['results'])}")
```

### 7. Casos de Uso Comuns

#### Relatório Semanal
```bash
# Logs da última semana
curl -X GET "http://localhost:8000/api/access-logs/logs_by_days/?days=7"
```

#### Relatório Mensal
```bash
# Logs do último mês
curl -X GET "http://localhost:8000/api/access-logs/logs_by_days/?days=30"
```

#### Análise de Acessos Concedidos
```bash
# Acessos concedidos nos últimos 15 dias
curl -X GET "http://localhost:8000/api/access-logs/logs_by_days/?days=15&event_type=7"
```

#### Análise de Tentativas de Acesso Negado
```bash
# Acessos negados nos últimos 30 dias
curl -X GET "http://localhost:8000/api/access-logs/logs_by_days/?days=30&event_type=6"
```

### 8. Verificação da Documentação da API

Após implementar, você pode verificar a documentação automática em:

```
http://localhost:8000/api/schema/swagger-ui/
```

A nova action `logs_by_days` aparecerá na documentação com todos os parâmetros e exemplos.

### 9. Teste de Performance

Para testar com grandes volumes de dados:

```bash
# Logs dos últimos 90 dias (teste de performance)
curl -X GET "http://localhost:8000/api/access-logs/logs_by_days/?days=90" \
  -H "Content-Type: application/json"
```

### 10. Integração com Frontend

```javascript
// Função para buscar logs por período
async function getLogsByDays(days, eventType = null) {
  const params = new URLSearchParams({ days: days.toString() });
  if (eventType) {
    params.append('event_type', eventType.toString());
  }
  
  const response = await fetch(`/api/access-logs/logs_by_days/?${params}`);
  return response.json();
}

// Uso
const logs = await getLogsByDays(15); // últimos 15 dias
const acessosConcedidos = await getLogsByDays(7, 7); // últimos 7 dias, apenas acessos concedidos
```

