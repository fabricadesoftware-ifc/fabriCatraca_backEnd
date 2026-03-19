# FabriCatraca

Sistema de controle de acesso do IFC das catracas ControlID

## Instalação Local

Primeiro deve-se atentar em componentes crusciais para o funcionamente desse sistema:

- Catracas ao mínimo pré-instaladas com acesso a rede e ip definido(sem isso nenhuma catraca obdecera oque o sistema mandar)
- Id interno de cada catraca, obtido via interface web da mesma

Após isso é necessario tambem variaveis de ambiente

```env

CELERY_BROKER_URL=     seu-broker-url
DATABASE_URL=          seu-database-url
DEBUG=                 True
GIT_REV=               83f648f738721e4862fcc2260d0bd41af8f1d763
MODE=                  development
SECRET_KEY=            django-insecure-sua-secret-key

```

Com isso o sistema já pode ser feito deploy no servidor local.

