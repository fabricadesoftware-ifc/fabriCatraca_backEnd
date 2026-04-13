<div id="top" class="">

<div align="center" class="text-center">
<h1>FABRICATRACA_BACKEND</h1>

<img alt="last-commit" src="https://img.shields.io/github/last-commit/fabricadesoftware-ifc/fabriCatraca_backEnd?style=flat&amp;logo=git&amp;logoColor=white&amp;color=0080ff" class="inline-block mx-1" style="margin: 0px 2px;">
<img alt="repo-top-language" src="https://img.shields.io/github/languages/top/fabricadesoftware-ifc/fabriCatraca_backEnd?style=flat&amp;color=0080ff" class="inline-block mx-1" style="margin: 0px 2px;">
<img alt="repo-language-count" src="https://img.shields.io/github/languages/count/fabricadesoftware-ifc/fabriCatraca_backEnd?style=flat&amp;color=0080ff" class="inline-block mx-1" style="margin: 0px 2px;">
<p><em>Built with the tools and technologies:</em></p>
<img alt="PDM" src="https://img.shields.io/badge/PDM-000000.svg?style=flat&amp;logo=PDM&amp;logoColor=#AC75D7" class="inline-block mx-1" style="margin: 0px 2px;">
<img alt="Markdown" src="https://img.shields.io/badge/Markdown-000000.svg?style=flat&amp;logo=Markdown&amp;logoColor=white" class="inline-block mx-1" style="margin: 0px 2px;">
<img alt="Celery" src="https://img.shields.io/badge/Celery-A9CC54.svg?style=flat&amp;logo=Celery&amp;logoColor=#DDF4A4" class="inline-block mx-1" style="margin: 0px 2px;">
<img alt="JavaScript" src="https://img.shields.io/badge/Python-3776AB.svg?style=flat&amp;logo=Python&amp;logoColor=white" class="inline-block mx-1" style="margin: 0px 2px;">
<img alt="Vue.js" src="https://img.shields.io/badge/Django-4FC08D.svg?style=flat&amp;logo=Django&amp;logoColor=white" class="inline-block mx-1" style="margin: 0px 2px;">
<br>
<img alt="TypeScript" src="https://img.shields.io/badge/RabbitMQ-FFFFFF.svg?style=flat&amp;logo=RabbitMQ&amp;logoColor=#FF6600" class="inline-block mx-1" style="margin: 0px 2px;">
<img alt="Vuetify" src="https://img.shields.io/badge/PostgreSQL-1867C0.svg?style=flat&amp;logo=PostgreSQL&amp;logoColor=white" class="inline-block mx-1" style="margin: 0px 2px;">
</div>
<br>
<hr>

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

### Problemas conhecidos
- O sistema salva o horario em UTC, porem na hora correta. Resumindo no banco ficara 09:59:51+00 e no admin iria mostrar 06:59:51, isso é um problema conhecido e não tem solução, oque fizemos foi na hora de exibir no admin convertemos para UTC de volta, ou seja, o horário mostrado no admin é o horário correto, porem com o timezone errado, isso não afeta em nada o funcionamento do sistema, apenas é um problema de exibição. Não podemos mudar o timezone do sistema para UTC porque isso afetaria outras partes do sistema, como por exemplo o horário de expiração dos tokens, que é calculado com base no horário atual do sistema.

- O sistema apenas ira indicar entrada ou saida de um usuário se o dispositivo estiver no modo de operação bloqueado/controlado, caso o mesmo se encotnre em sempre liberado o dispositivo/catraca não envia entradas e saidas, apenas envia o status de liberado ou bloqueado, isso é um comportamento esperado, porem pode ser confuso para quem não conhece o sistema, por isso é importante deixar claro que o sistema só irá indicar entradas e saídas se o dispositivo estiver no modo de operação bloqueado/controlado, caso contrário ele apenas irá indicar o status de liberado ou bloqueado.
