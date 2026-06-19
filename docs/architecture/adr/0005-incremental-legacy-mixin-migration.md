# ADR 0005: Migracao Incremental dos Mixins Legados

## Status

Aceito

## Contexto

O projeto ainda possui varios mixins legados para sincronizacao com catracas.
Eles funcionam como compatibilidade, mas deixam as fronteiras de responsabilidade
pouco claras quando usados diretamente por views.

## Decisao

Migrar por fluxo, nao por reescrita global.

Cada recorte deve:

- preservar o contrato HTTP existente sempre que possivel;
- criar service/use case explicito;
- adicionar testes focados;
- manter rollback forte em falha de catraca por enquanto;
- deixar o mixin legado disponivel ate que todos os consumidores relevantes sejam migrados.

## Consequencias

- A arquitetura melhora de forma gradual e verificavel.
- O codigo pode conviver temporariamente com padroes antigo e novo.
- Novas features devem seguir o padrao explicito, nao o mixin legado.
