# ADR 0002: ViewSets como Adaptadores HTTP

## Status

Aceito

## Contexto

Alguns ViewSets acumulavam validacao HTTP, transacao de banco, regras de negocio,
sincronizacao com catracas e tratamento de erro. Isso tornava mudancas pequenas
mais arriscadas e dificultava testes focados.

## Decisao

ViewSets devem atuar principalmente como adaptadores HTTP:

- validar entrada com serializers;
- chamar use cases ou services;
- converter resultados e erros em respostas HTTP.

Regras de negocio, transacao e sincronizacao devem migrar gradualmente para
use cases e services explicitos.

## Consequencias

- Novos fluxos devem evitar herdar mixins de sincronizacao diretamente nas views.
- Testes podem focar use cases/services sem precisar passar por HTTP.
- Refatoracoes devem ser incrementais para preservar comportamento existente.
