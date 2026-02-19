# Contexto Completo do Problema: Easy Setup Catraca Control iD

## Objetivo

- Eliminar o erro "Invalid op type: 0" no firmware da catraca após o Easy Setup.
- Garantir que a entrada de PIN funcione corretamente e que o Easy Setup faça um reset e reconfiguração total do dispositivo.

## Infraestrutura Técnica

- Backend Django 5.2.4, DRF, PostgreSQL, Celery, RabbitMQ, Python 3.13.10, PDM.
- Firmware Control iD V5.18.3, modelo IDBLOCK, IP da catraca: 191.52.62.21.
- Easy Setup orquestrado pelo arquivo `easy_setup.py`.

## Histórico de Debugging

### Tentativa 1: Reordenar disable_identifier (Commit 0f06afb)

- **Hipótese:** `disable_identifier` era chamado cedo demais, firmware sobrescrevia.
- **Correção:** Mover `disable_identifier` para depois do `push_data`.
- **Resultado:** Erro persistiu. Logs mostraram que o firmware tem init atrasada (~30-40s).

### Tentativa 2: Aguardar firmware init + verificação final (ATUAL)

- **Causa Raiz Real:** O firmware V5.18.3 tem init em múltiplas fases:
  - **Fase Rápida (~6s):** Core, networking, API — login funciona.
  - **Fase Atrasada (~30-40s):** Cria defaults (access_rules type=0), habilita biometry/card, seta language/locale.
- **Evidência:** Logs da catraca mostram config changes em 14:47:49-54 que NÃO vieram do nosso servidor (language=pt_BR, country_code=BR, biometry=1, card=1).
- **Correção:**
  1. Delay de 35s após factory reset (antes do push) para aguardar init completa
  2. Método `verify_access_rules` que carrega regras da catraca e corrige type=0
- **Status:** Implementado, aguardando teste real.

## Fluxo Easy Setup (v3 — atual)

1. Login
2. Factory reset (keep_network)
3. Aguardar reboot + re-login
4. Acertar data/hora
5. Configurar monitor
6. **Aguardar firmware init completa (~35s)** ← NOVO
7. Push data (destroy + create, access_rules type≥1)
8. Disable identifier (pin=0, card=0)
9. Configure device settings (pin=1, card=1 — transição 0→1 força reload)
10. **Verificação final de access_rules** ← NOVO

## Referências

- Código: src/core/control_id_config/infra/control_id_config_django_app/views/easy_setup.py
- Commit 0f06afb: primeira tentativa (reordenar disable_identifier)

---

Este arquivo resume todo o contexto técnico, histórico de debugging, decisões e evidências do problema e solução do Easy Setup da catraca Control iD.
