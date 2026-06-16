# User Sync Refactor

## Decisao

O banco da aplicacao e a fonte de verdade para usuarios. As catracas ControlID sao destinos sincronizados.

O endpoint antigo `GET /api/users/users/sync/`, que tentava puxar usuarios da catraca para o banco, foi desativado com `410 Gone`. Ele permanece exposto apenas para retornar uma resposta explicita de funcao indisponivel, evitando execucao acidental de um fluxo legado.

## Fronteiras

- `UserViewSet`: adaptador HTTP. Valida request, aplica permissao e transforma resultado em `Response`.
- `CreateUserUseCase`, `UpdateUserUseCase`, `DeleteUserUseCase`: orquestram transacao de banco e sincronizacao.
- `UserModificationPolicy`: centraliza a regra de quem pode criar/modificar usuarios nao visitantes.
- `VisitorService`: resolve visitante existente e cria registro de visita.
- `UserDeviceSyncService`: decide quais catracas receberao create/update/delete de usuario.
- `UserControlIDMapper`: transforma `User` em payload da API ControlID.
- `ControlIDGateway`: contrato explicito para falar com ControlID, ainda delegando para o mixin legado.
- `CardEnrollmentService`: captura cartao via `remote_enroll` sem expor o mixin HTTP para as views.
- `CardDeviceSyncService`: cria, atualiza e remove cartoes nas catracas alvo.
- `UserGroupDeviceSyncService`: garante grupo/usuario pai e sincroniza o vinculo usuario-grupo nas catracas alvo.
- `BiometricEnrollmentService`: captura template biometrico via `remote_enroll`.
- `BiometricTemplateExtractionService`: extrai template a partir da captura local do sensor.
- `TemplateDeviceSyncService`: replica, atualiza e remove biometrias nas catracas alvo.

## Regra de alvo

Servicos que iteram uma catraca especifica devem chamar o gateway com
`device_ids=[device.id]`. O estado interno de `set_device()` nao deve ser usado
como criterio implicito de alvo para `create_objects`, `update_objects`,
`destroy_objects` ou `create_or_update_objects`.

## Fora desta etapa

- Separar internamente transporte, sessao e retry do `catraca_sync.py`.
- Alterar o comportamento de rollback forte em falha de catraca.
