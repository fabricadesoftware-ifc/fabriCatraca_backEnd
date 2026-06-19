# ADR 0001: Banco como Fonte de Verdade

## Status

Aceito

## Contexto

O sistema precisa manter usuarios, vinculos, credenciais e regras sincronizados
com as catracas ControlID. Historicamente existiam fluxos legados tentando
sincronizar dados de volta da catraca para o banco, o que abria espaco para
duplicidade, dados incompletos e execucoes acidentais.

## Decisao

O banco da aplicacao e a fonte de verdade. As catracas sao destinos de
sincronizacao.

Endpoints legados que tentavam puxar usuarios da catraca para o banco devem
ficar desativados explicitamente quando nao forem seguros.

## Consequencias

- Alteracoes de negocio devem nascer no banco e depois ser enviadas para as catracas.
- Falhas de sincronizacao devem ser tratadas na camada de caso de uso ou servico.
- Fluxos de importacao, cadastro e liberacao temporaria nao devem depender da catraca como origem primaria dos dados.
