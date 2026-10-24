# ADR 0010 — Testes de contrato com Pact

**Status:** aceita

## Contexto

Os serviços conversam por REST (Booking e Waitlist leem o Catalog; o Waitlist reserva, confirma e libera
horários no Booking) e por eventos no Kafka, lidos por três consumidores diferentes. Os testes de cada
serviço usam dublês dos outros, então uma mudança num formato passava em todas as suítes e só quebrava com
a stack inteira no ar. O teste de ponta a ponta do CI cobre só parte desses caminhos.

## Decisão

- **Contratos dirigidos pelo consumidor com Pact** (especificação V4, `pact-python`). Cada consumidor
  descreve, num teste, as requisições que faz e os campos que lê das respostas e dos eventos. O teste roda
  o cliente real contra o mock do Pact e grava o contrato em `pacts/`.
- **Contratos de mensagem para o Kafka.** Notification, Analytics e o worker do Waitlist declaram os eventos
  que consomem; o teste valida o exemplo com os mesmos modelos Pydantic que o consumidor usa em produção.
- **Verificação no provedor.** Catalog e Booking sobem a API real num PostgreSQL do Testcontainers, e os
  *provider states* preparam os dados de cada interação. Para os eventos, Booking e Waitlist geram as
  mensagens com as mesmas funções que gravam o outbox.
- **Contratos versionados no repositório**, sem Pact Broker. O CI falha se os testes dos consumidores gerarem
  um contrato diferente do que está em `pacts/`.

## Consequências

- Remover ou renomear um campo que algum consumidor usa quebra a suíte do provedor, com a interação e o
  campo apontados na mensagem de erro.
- Os contratos pedem só o que cada consumidor lê. O provedor continua livre para adicionar campos.
- Sem broker, não há verificação entre versões implantadas (`can-i-deploy`); como tudo vive num repositório
  e é publicado junto, a verificação no mesmo commit basta por enquanto.
