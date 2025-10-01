# 🧪 Guia de Testes - FabriCatraca

## 📋 Estrutura de Testes

```
tests/
├── conftest.py                    # Fixtures globais e configurações
├── unit/                          # Testes unitários (rápidos)
│   ├── test_models.py            # Testes dos models Django
│   └── test_serializers.py       # Testes dos serializers DRF
├── integration/                   # Testes de integração (com mocks)
│   ├── test_sync_mocked.py       # Sync com API mockada
│   └── test_viewsets.py          # Testes das ViewSets REST
└── e2e/                           # Testes end-to-end (API real)
    └── test_real_catraca.py      # Testes com catraca real
```

## 🚀 Como Executar os Testes

### Instalar Dependências

```bash
pdm install
```

### Executar TODOS os testes

```bash
pdm test-all
```

### Executar apenas testes unitários (rápidos)

```bash
pdm test-unit
```

### Executar apenas testes de integração

```bash
pdm test-integration
```

### Executar apenas testes E2E (com catraca real)

```bash
# Configurar variáveis de ambiente primeiro
set TEST_CATRACA_IP=192.168.1.100
set TEST_CATRACA_PORT=80
set RUN_E2E_TESTS=1

pdm test-e2e
```

### Executar com cobertura de código

```bash
pdm test-cov
```

Isso vai gerar um relatório HTML em `htmlcov/index.html`.

### Executar testes específicos

```bash
# Apenas um arquivo
pdm test tests/unit/test_models.py

# Apenas uma classe
pdm test tests/unit/test_models.py::TestCatraConfigModel

# Apenas um teste
pdm test tests/unit/test_models.py::TestCatraConfigModel::test_create_catra_config
```

### Pular testes lentos

```bash
pdm test -m "not slow"
```

### Pular testes E2E

```bash
pdm test -m "not e2e"
```

## 📊 Tipos de Testes

### 🟢 Testes Unitários (`@pytest.mark.unit`)

- **Objetivo**: Testar componentes isolados (models, serializers)
- **Características**:
  - Muito rápidos (< 1s cada)
  - Não fazem chamadas HTTP
  - Usam banco de dados em memória (SQLite)
- **Exemplos**:
  - Validação de campos do model
  - Serialização/deserialização de dados
  - Validação de choices e constraints

```python
@pytest.mark.unit
@pytest.mark.django_db
def test_create_catra_config(catra_config_factory):
    config = catra_config_factory(gateway='clockwise')
    assert config.gateway == 'clockwise'
```

### 🟡 Testes de Integração (`@pytest.mark.integration`)

- **Objetivo**: Testar integração entre componentes
- **Características**:
  - Rápidos (< 5s cada)
  - Usam mocks para APIs externas
  - Testam banco de dados real
- **Exemplos**:
  - Sync com API mockada
  - ViewSets REST com banco de dados
  - Validação de payloads

```python
@pytest.mark.integration
@pytest.mark.django_db
@patch('requests.post')
def test_sync_from_catraca(mock_post, device_factory):
    mock_post.return_value.json.return_value = {'catra': {...}}
    # ... test code
```

### 🔴 Testes E2E (`@pytest.mark.e2e`)

- **Objetivo**: Testar com catraca real
- **Características**:
  - Lentos (> 10s cada)
  - Fazem chamadas HTTP reais
  - Requerem catraca disponível na rede
- **Exemplos**:
  - Sync real com catraca
  - Roundtrip (enviar e receber)
  - Validação completa do fluxo

```python
@pytest.mark.e2e
@pytest.mark.slow
@skip_if_no_test_device
def test_real_sync(device_factory):
    device = device_factory(ip='192.168.1.100')
    # ... test code with real API
```

## 🔧 Configuração de Testes E2E

Para executar testes E2E com uma catraca real:

### Windows (PowerShell)

```powershell
$env:TEST_CATRACA_IP = "192.168.1.100"
$env:TEST_CATRACA_PORT = "80"
$env:RUN_E2E_TESTS = "1"
pdm test-e2e
```

### Linux/Mac

```bash
export TEST_CATRACA_IP="192.168.1.100"
export TEST_CATRACA_PORT="80"
export RUN_E2E_TESTS="1"
pdm test-e2e
```

### Arquivo .env (recomendado)

Crie um arquivo `.env.test`:

```env
TEST_CATRACA_IP=192.168.1.100
TEST_CATRACA_PORT=80
RUN_E2E_TESTS=1
```

## 🎯 Fixtures Disponíveis

### Factories (criar objetos para testes)

```python
def test_example(device_factory, catra_config_factory):
    # Criar device
    device = device_factory(ip='192.168.1.100')
    
    # Criar config
    config = catra_config_factory(
        device=device,
        gateway='clockwise'
    )
```

### Fixtures Disponíveis:

- `api_client` - Cliente DRF para testar APIs
- `authenticated_client` - Cliente autenticado
- `device_factory` - Criar dispositivos (catracas)
- `user_factory` - Criar usuários
- `system_config_factory` - Criar SystemConfig
- `hardware_config_factory` - Criar HardwareConfig
- `security_config_factory` - Criar SecurityConfig
- `ui_config_factory` - Criar UIConfig
- `monitor_config_factory` - Criar MonitorConfig
- `catra_config_factory` - Criar CatraConfig
- `push_server_config_factory` - Criar PushServerConfig
- `mock_catraca_response` - Mock de resposta da API

## 📈 Cobertura de Código

### Ver cobertura no terminal

```bash
pdm test-cov
```

### Ver relatório HTML

```bash
pdm test-cov
# Abrir htmlcov/index.html no navegador
```

### Objetivo de Cobertura

- **Mínimo**: 70%
- **Ideal**: 85%+
- **Crítico**: 100% nos mixins de sync

## ✅ Checklist de Testes

### Para cada novo Model:
- [ ] Teste de criação
- [ ] Teste de validação de campos
- [ ] Teste de relacionamentos
- [ ] Teste de métodos customizados
- [ ] Teste de `__str__` e `__repr__`

### Para cada novo Serializer:
- [ ] Teste de serialização (model → JSON)
- [ ] Teste de deserialização (JSON → model)
- [ ] Teste de validações customizadas
- [ ] Teste de campos computados

### Para cada novo Mixin de Sync:
- [ ] Teste de sync_from_catraca (GET)
- [ ] Teste de update_in_catraca (SET)
- [ ] Teste de tratamento de erros
- [ ] Teste de conversão de dados (bool → string)

### Para cada nova ViewSet:
- [ ] Teste de LIST
- [ ] Teste de CREATE
- [ ] Teste de RETRIEVE
- [ ] Teste de UPDATE
- [ ] Teste de DELETE
- [ ] Teste de filtros
- [ ] Teste de validações

## 🐛 Debugging Testes

### Ver prints durante os testes

```bash
pdm test -s
```

### Ver logs detalhados

```bash
pdm test -vv
```

### Parar no primeiro erro

```bash
pdm test -x
```

### Rodar apenas testes que falharam

```bash
pdm test --lf
```

## 📝 Escrevendo Novos Testes

### Exemplo de Teste Unitário

```python
import pytest

@pytest.mark.unit
@pytest.mark.django_db
class TestMyModel:
    def test_create(self, my_model_factory):
        """Deve criar MyModel com sucesso."""
        obj = my_model_factory(field='value')
        assert obj.field == 'value'
```

### Exemplo de Teste de Integração

```python
import pytest
from unittest.mock import patch

@pytest.mark.integration
@pytest.mark.django_db
class TestMySync:
    @patch('requests.post')
    def test_sync(self, mock_post, device_factory):
        """Deve sincronizar com API mockada."""
        mock_post.return_value.json.return_value = {...}
        # ... test code
```

### Exemplo de Teste E2E

```python
import pytest

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.skipif(not os.getenv('RUN_E2E_TESTS'), reason="...")
@pytest.mark.django_db
class TestMyE2E:
    def test_real_api(self, device_factory):
        """Deve testar com API real."""
        device = device_factory(ip='192.168.1.100')
        # ... test code with real API
```

## 🔄 Integração Contínua (CI)

Para rodar no CI/CD (GitHub Actions, GitLab CI, etc.):

```yaml
- name: Run tests
  run: |
    pdm install
    pdm test -m "not e2e"  # Pular testes E2E no CI
    pdm test-cov
```

## 📚 Recursos

- [Pytest Documentation](https://docs.pytest.org/)
- [Django Testing](https://docs.djangoproject.com/en/5.0/topics/testing/)
- [DRF Testing](https://www.django-rest-framework.org/api-guide/testing/)
- [Factory Boy](https://factoryboy.readthedocs.io/)

## 🎓 Boas Práticas

1. **Use factories** em vez de criar objetos manualmente
2. **Mock APIs externas** em testes de integração
3. **Marque testes lentos** com `@pytest.mark.slow`
4. **Use nomes descritivos** para funções de teste
5. **Um assert por conceito** (não muitos asserts diferentes)
6. **Teste casos de erro** (não só happy path)
7. **Mantenha testes isolados** (não dependam um do outro)
8. **Limpe dados** após cada teste (pytest-django faz automaticamente)

## 🚨 Troubleshooting

### Erro: "No module named pytest"

```bash
pdm install
```

### Erro: "Database is locked"

Use `@pytest.mark.django_db(transaction=True)` se precisar de transações.

### Testes E2E falhando

1. Verifique se a catraca está ligada e acessível
2. Confirme o IP e porta corretos
3. Teste conexão: `ping 192.168.1.100`
4. Verifique firewall

### Cobertura baixa

```bash
pdm test-cov --cov-report=term-missing
```

Isso mostra quais linhas não estão cobertas.
