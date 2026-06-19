# ADR 0004: Alvo de Catraca Explicito

## Status

Aceito

## Contexto

Alguns codigos chamavam `set_device(device)` e depois usavam metodos como
`create_objects` sem informar `device_ids`. Em partes do legado, esses metodos
podem operar em todas as catracas ativas quando `device_ids` nao e informado.
Isso cria risco de sincronizacao em escopo maior do que o esperado.

## Decisao

Quando um service esta operando sobre uma catraca especifica, ele deve informar
explicitamente `device_ids=[device.id]` nas chamadas ao gateway.

Quando uma regra muda de escopo entre "todas as catracas" e um grupo de
portais, o service deve calcular explicitamente dispositivos removidos,
adicionados e comuns.

## Consequencias

- `set_device()` nao deve ser usado como unico criterio implicito de alvo.
- Services ficam mais verbosos, mas o comportamento fica previsivel.
- Testes devem proteger chamadas criticas com `device_ids` explicito.
