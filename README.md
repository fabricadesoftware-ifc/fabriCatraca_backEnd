# ADP — Sistema de Controle de Acesso Escolar (ControlID) — Versão Cliente

## 1. Objetivo

O sistema vai controlar a entrada e saída de alunos usando catracas Control iD em modo **Standalone**, com regras de autorização baseadas em horários de turma e autorizações extras.

## 2. Como vai funcionar

1. Recebemos uma base de alunos com **matrícula** e **nome** do SISAE.
2. O aluno cadastra sua biometria no SISAE.
3. O SISAE exporta os **horários das turmas**.
4. Nosso sistema importa esses horários e define quando cada grupo pode entrar ou sair.
5. Sincronizamos com as catracas — que passam a decidir localmente se liberam ou não a passagem.
6. O painel administrativo exibe **acessos recentes** indicando se o aluno entrou ou saiu, com horário e motivo.

## 3. Funcionalidades do Painel

* **Dashboard**: status das catracas e eventos recentes.
* **Alunos**: lista, pesquisa e edição.
* **Turmas e Horários**: grade semanal para definir janelas de acesso.
* **Autorizações Extras**: criar permissões temporárias.
* **Relatórios**: exportar acessos por aluno, turma ou período.

## 4. Regras de Liberação

A catraca libera a passagem se:

* O aluno tiver autorização temporária válida.
* O horário atual estiver dentro do horário permitido para sua turma.
* O aluno estiver ativo e sem bloqueios.

Bloqueios e autorizações manuais têm prioridade.

## 5. Privacidade (LGPD)

* Biometrias ficam nas catracas, não no servidor.
* Coleta de consentimento para uso da biometria.
* Retenção limitada de registros, com opção de anonimização.

