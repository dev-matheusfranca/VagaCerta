# Changelog

Todas as mudanças relevantes do projeto ficam registradas neste arquivo.

O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/), e o projeto usa
[Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [0.2.1] - 2026-10-23

### Adicionado

- O pipeline de CI pode ser executado manualmente pela aba Actions.

## [0.2.0] - 2026-10-23

### Adicionado

- Eventos de agendamento (`booking.created`, `booking.cancelled`) gravados num outbox transacional e
  publicados no Kafka por um outbox relay.
- Serviço Notification com e-mails de confirmação, cancelamento e lembrete, em templates HTML com a
  identidade visual do app.
- Envio de e-mails pelo RabbitMQ com novas tentativas após 5 s, 30 s e 2 min, e dead-letter queue.
- Consumo idempotente de eventos e projeção local dos agendamentos no Notification.
- Kafka, Kafka UI, RabbitMQ e Mailpit no Docker Compose.
- A página do agendamento mostra para qual e-mail a confirmação foi enviada.
- ADR 0003 (outbox transacional) e ADR 0004 (Kafka para eventos, RabbitMQ para tarefas).

### Alterado

- Cancelar um agendamento já cancelado não faz nada e não emite evento.
- Os testes de integração rodam contra Kafka e RabbitMQ reais e usam os módulos `community` do
  Testcontainers.

## [0.1.0] - 2026-10-23

### Adicionado

- Serviço Catalog com estabelecimentos, profissionais, serviços e expediente, com dados de exemplo.
- Serviço Booking com disponibilidade em tempo real e prevenção de conflito de horário por exclusion
  constraint do PostgreSQL.
- Front-end em Vue 3 com o fluxo completo de agendamento.
- Testes unitários, baseados em propriedades, de integração, de concorrência e de arquitetura.
- Docker Compose, pipeline no GitHub Actions, README e ADRs 0001 e 0002.

[0.2.1]: https://github.com/dev-matheusfranca/VagaCerta/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/dev-matheusfranca/VagaCerta/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/dev-matheusfranca/VagaCerta/releases/tag/v0.1.0
