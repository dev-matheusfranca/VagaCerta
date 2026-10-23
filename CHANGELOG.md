# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.1] - 2026-10-23

### Added

- The CI pipeline can be started manually from the Actions tab.

## [0.2.0] - 2026-10-23

### Added

- Booking events (`booking.created`, `booking.cancelled`) written to a transactional outbox and published
  to Kafka by an outbox relay.
- Notification service with confirmation, cancellation and reminder e-mails using branded HTML templates.
- E-mail delivery through RabbitMQ with retries after 5 s, 30 s and 2 min, and a dead-letter queue.
- Idempotent event consumption and a local bookings projection in the Notification service.
- Kafka, Kafka UI, RabbitMQ and Mailpit in Docker Compose.
- The booking confirmation page shows where the e-mail was sent.
- ADR 0003 (transactional outbox) and ADR 0004 (Kafka for events, RabbitMQ for jobs).

### Changed

- Cancelling an already cancelled booking is a no-op and emits no event.
- Integration tests run against real Kafka and RabbitMQ containers and use the Testcontainers community
  modules.

## [0.1.0] - 2026-10-23

### Added

- Catalog service for businesses, professionals, services and working hours, with sample data.
- Booking service with real-time availability and double-booking prevention through a PostgreSQL
  exclusion constraint.
- Vue 3 web app covering the full booking flow.
- Unit, property-based, integration, concurrency and architecture tests.
- Docker Compose setup, GitHub Actions pipeline, README and ADRs 0001 and 0002.

[0.2.1]: https://github.com/dev-matheusfranca/VagaCerta/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/dev-matheusfranca/VagaCerta/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/dev-matheusfranca/VagaCerta/releases/tag/v0.1.0
