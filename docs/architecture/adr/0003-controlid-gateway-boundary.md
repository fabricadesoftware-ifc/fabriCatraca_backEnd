# ADR 0003: Gateway Explicito para ControlID

## Status

Aceito

## Contexto

A integracao com a ControlID ainda concentra transporte HTTP, sessao, retry e
formatacao de objetos em estruturas legadas. Reescrever tudo de uma vez seria
arriscado.

## Decisao

Introduzir `ControlIDGateway` como contrato pequeno e explicito para novas
camadas de dominio/aplicacao.

Por enquanto, o gateway delega para o mixin legado. O objetivo e reduzir o
acoplamento das views e services ao mixin inteiro, sem exigir uma reescrita
completa imediata de `catraca_sync.py`.

## Consequencias

- Novos services devem depender do gateway, nao diretamente de `ControlIDSyncMixin`.
- O mixin legado pode continuar existindo enquanto os fluxos sao migrados.
- Futuramente, transporte, sessao e retry podem ser separados por baixo do gateway.
