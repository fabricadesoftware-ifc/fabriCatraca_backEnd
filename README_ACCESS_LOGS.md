# Documentação - Logs de Acesso por Dias

## Nova Funcionalidade: Filtro por Dias

Foi adicionada uma nova action `logs_by_days` no ViewSet de AccessLogs que permite filtrar os logs de acesso pelos últimos N dias.

### Endpoint

```
GET /api/access-logs/logs_by_days/
```

### Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição | Exemplo |
|-----------|------|-------------|-----------|---------|
| `days` | integer | Sim | Número de dias para filtrar (deve ser > 0) | 15, 30, 60 |
| `event_type` | integer | Não | Tipo de evento para filtrar adicionalmente | 7 (ACESSO_CONCEDIDO) |

### Exemplos de Uso

#### 1. Logs dos últimos 15 dias
```bash
GET /api/access-logs/logs_by_days/?days=15
```

#### 2. Logs dos últimos 30 dias
```bash
GET /api/access-logs/logs_by_days/?days=30
```

#### 3. Logs dos últimos 7 dias com filtro por tipo de evento
```bash
GET /api/access-logs/logs_by_days/?days=7&event_type=7
```

#### 4. Logs dos últimos 60 dias
```bash
GET /api/access-logs/logs_by_days/?days=60
```

### Tipos de Evento Disponíveis

| Código | Descrição |
|--------|-----------|
| 1 | EQUIPAMENTO_INVALIDO |
| 2 | PARAMETRO_DE_IDENTIFICACAO_INVALIDO |
| 3 | NÃO_IDENTIFICADO |
| 4 | IDENTIFICACAO_PENDENTE |
| 5 | TEMPO_DE_IDENTIFICACAO_ESGOTADO |
| 6 | ACESSO_NEGADO |
| 7 | ACESSO_CONCEDIDO |
| 8 | ACESSO_PENDENTE |
| 9 | USUARIO_NAO_E_ADM |
| 10 | ACESSO_NAO_IDENTIFICADO |
| 11 | ACESSO_POR_BOTOEIRA |
| 12 | ACESSO_PELA_INTERFACE_WEB |
| 13 | DESISTENCIA_DE_ENTRADA |
| 14 | SEM_RESPOSTA |
| 15 | ACESSO_PELA_INTERFONIA |

### Resposta

A resposta inclui:
- **Paginação**: Aplicada automaticamente conforme configuração do DRF
- **Filtros**: Logs filtrados pela data e opcionalmente por tipo de evento
- **Ordenação**: Por padrão, ordenados por data decrescente (mais recentes primeiro)

### Exemplo de Resposta

```json
{
    "count": 150,
    "next": "http://localhost:8000/api/access-logs/logs_by_days/?days=15&page=2",
    "previous": null,
    "results": [
        {
            "id": 1234,
            "time": "2024-01-15T10:30:00Z",
            "event_type": 7,
            "device": {
                "id": 1,
                "name": "Catraca Principal"
            },
            "identifier_id": "user123",
            "user": {
                "id": 1,
                "username": "joao.silva"
            },
            "portal": {
                "id": 1,
                "name": "Entrada Principal"
            },
            "access_rule": {
                "id": 1,
                "name": "Acesso Padrão"
            },
            "qr_code": "",
            "uhf_value": "",
            "pin_value": "",
            "card_value": "",
            "confidence": 0,
            "mask": ""
        }
    ]
}
```

### Tratamento de Erros

- **400 Bad Request**: Se o parâmetro `days` for inválido ou negativo
- **400 Bad Request**: Se o parâmetro `event_type` for inválido
- **500 Internal Server Error**: Para erros internos do servidor

### Benefícios

1. **Performance**: Filtra apenas os logs relevantes, reduzindo o volume de dados
2. **Flexibilidade**: Permite especificar qualquer número de dias
3. **Filtros Combinados**: Pode combinar filtro por dias com filtro por tipo de evento
4. **Paginação**: Mantém a paginação padrão do DRF para grandes volumes de dados

