<h1 align="center">VagaCerta</h1>

<p align="center">
  <strong>The right time slot, without the back-and-forth of chat messages.</strong><br />
  Online scheduling for small service businesses, built as event-driven microservices.
</p>

<p align="center">
  <a href="https://github.com/dev-matheusfranca/VagaCerta/actions/workflows/ci.yml"><img src="https://github.com/dev-matheusfranca/VagaCerta/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <img src="https://img.shields.io/badge/python-3.13-3776AB?logo=python&logoColor=white" alt="Python 3.13" />
  <img src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Apache%20Kafka-4-231F20?logo=apachekafka&logoColor=white" alt="Apache Kafka 4" />
  <img src="https://img.shields.io/badge/RabbitMQ-4-FF6600?logo=rabbitmq&logoColor=white" alt="RabbitMQ 4" />
  <img src="https://img.shields.io/badge/PostgreSQL-17-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL 17" />
  <img src="https://img.shields.io/badge/Vue-3-4FC08D?logo=vuedotjs&logoColor=white" alt="Vue 3" />
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT license" />
</p>

<p align="center">
  <img src="docs/screenshots/home.png" alt="VagaCerta home page" width="900" />
</p>

## Table of contents

- [About](#about)
- [Features](#features)
- [Screenshots](#screenshots)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [API reference](#api-reference)
- [Events](#events)
- [Testing](#testing)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Author](#author)

## About

Barbershops, beauty studios, clinics and wellness spaces still book most appointments by hand, through chat
apps. That leads to three everyday problems:

1. **Back-and-forth messages** just to find a time that works for both sides.
2. **Double bookings** when two people are promised the same slot.
3. **No-shows and empty chairs** when people forget their appointment or cancel without anyone finding out.

VagaCerta lets customers pick a service, a professional and a free slot in a few clicks, at any hour. The
system **guarantees that a slot is never booked twice**, even when many people try to book it at the same
moment, and keeps customers informed by e-mail: confirmation, cancellation and a reminder before the
appointment.

The project grows in phases toward a full event-driven architecture. See the [roadmap](#roadmap).

## Features

- Browse businesses, their services (duration and price) and their professionals.
- Real-time availability, calculated from each professional's weekly working hours and existing bookings.
- Booking with no double booking under concurrency, enforced by the database.
- Cancellation that immediately returns the slot to the agenda.
- E-mails for confirmation, cancellation and a reminder 24 hours before (or 2 hours, for last-minute
  bookings), with branded HTML templates.
- Reliable delivery: failed e-mails are retried with increasing delays and parked in a dead-letter queue.
- Responsive web app and interactive API documentation (OpenAPI/Swagger) for every service.

## Screenshots

| Choose service, professional and time | Booking confirmation |
|---|---|
| <img src="docs/screenshots/business.png" alt="Business page with services, professionals and free slots" /> | <img src="docs/screenshots/booking.png" alt="Booking confirmation page" /> |

<p align="center">
  <img src="docs/screenshots/email.png" alt="Confirmation e-mail" width="480" /><br />
  <em>Confirmation e-mail, as captured by Mailpit</em>
</p>

## Architecture

```mermaid
flowchart LR
    user((Customer)) --> web["Web app<br/>Vue 3 + nginx"]
    web -->|/api/catalog| catalog["Catalog<br/>FastAPI"]
    web -->|/api/booking| booking["Booking<br/>FastAPI"]
    booking -->|REST| catalog
    catalog --> catalogdb[(PostgreSQL<br/>catalog)]
    booking --> bookingdb[(PostgreSQL<br/>bookings + outbox)]
    bookingdb -.->|polls| relay["Outbox relay"]
    relay -->|booking.events| kafka{{Kafka}}
    kafka --> notification["Notification<br/>consumer + scheduler"]
    notification --> notificationdb[(PostgreSQL<br/>projection)]
    notification -->|e-mail jobs| rabbitmq{{RabbitMQ}}
    rabbitmq --> worker["E-mail worker"]
    worker -->|SMTP| mail["Mailpit"]
```

| Component | Responsibility |
|---|---|
| **catalog** | Businesses, professionals, services and weekly working hours |
| **booking** | Availability calculation, bookings and cancellations; writes domain events to an outbox |
| **booking-relay** | Publishes outbox events to Kafka |
| **notification** | Consumes booking events, schedules reminders and sends e-mails through RabbitMQ |
| **web** | Customer-facing booking flow; nginx also routes `/api/*` to the services |

### How a booking becomes an e-mail

```mermaid
sequenceDiagram
    participant C as Customer
    participant B as Booking
    participant DB as Booking DB
    participant R as Outbox relay
    participant K as Kafka
    participant N as Notification
    participant Q as RabbitMQ
    participant S as SMTP
    C->>B: POST /bookings
    B->>DB: INSERT booking + outbox event (one transaction)
    B-->>C: 201 Created
    R->>DB: SELECT pending events FOR UPDATE SKIP LOCKED
    R->>K: booking.created (key = booking id)
    K->>N: booking.created
    N->>N: ignore if the event id was already processed
    N->>Q: enqueue confirmation e-mail
    Q->>N: e-mail job
    N->>S: send
    Note over N,Q: on failure: retry after 5 s, 30 s and 2 min, then dead-letter queue
```

### Design decisions

- **Database per service.** Each service owns its schema and migrations; they talk only through APIs and
  events.
- **Transactional outbox.** A booking and its event are stored in the same transaction, so an event is
  published if and only if the change was committed. No dual writes.
- **Kafka for facts, RabbitMQ for jobs.** Domain events go to Kafka, where any number of consumers can read
  and replay them. E-mails are jobs that need retries and dead-lettering, which RabbitMQ handles natively.
- **Idempotent consumer.** Kafka delivers at least once; Notification records each event id and ignores
  duplicates.
- **Event-carried state transfer.** `booking.created` carries the names Notification needs, and
  Notification keeps its own projection, so it never calls Booking or Catalog back.
- **Retries without plugins.** One RabbitMQ queue per attempt, each with a fixed TTL that dead-letters back
  to the main queue: increasing delays without head-of-line blocking.
- **Framework-free domain.** Availability and reminder rules are pure functions; an architecture test
  forbids those modules from importing frameworks or brokers.
- **Concurrency handled by PostgreSQL.** An exclusion constraint rejects overlapping bookings, so the API
  returns `409 Conflict` to everyone but the first request.

Each decision is recorded as an ADR:

- [ADR 0001 — Python + FastAPI](docs/adr/0001-python-fastapi.md)
- [ADR 0002 — Double booking is prevented by the database](docs/adr/0002-double-booking-exclusion-constraint.md)
- [ADR 0003 — Transactional outbox for booking events](docs/adr/0003-transactional-outbox.md)
- [ADR 0004 — Kafka for events, RabbitMQ for e-mail jobs](docs/adr/0004-kafka-events-rabbitmq-jobs.md)

## Tech stack

| Layer | Technologies |
|---|---|
| Services | Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2 (async), asyncpg, Alembic |
| Messaging | Apache Kafka 4 (KRaft) with aiokafka, RabbitMQ 4 with aio-pika |
| E-mail | aiosmtplib, HTML templates, Mailpit for local delivery |
| Database | PostgreSQL 17 (`btree_gist` exclusion constraint, JSONB) |
| Web | Vue 3, TypeScript, Vite, Tailwind CSS 4, Vue Router, Lucide icons |
| Testing | pytest, Testcontainers (PostgreSQL, Kafka, RabbitMQ), Hypothesis, import-linter |
| Code quality | ruff (lint + format), mypy (strict), vue-tsc |
| Infrastructure | Docker, Docker Compose, nginx, Kafka UI, GitHub Actions |
| Tooling | uv workspace (one lock file for all Python services) |

## Project structure

```
VagaCerta/
├── services/
│   ├── Dockerfile              # shared image for the Python services
│   ├── catalog/
│   │   ├── migrations/         # Alembic migrations
│   │   ├── src/catalog/        # models, schemas, API routes and seed data
│   │   └── tests/
│   ├── booking/
│   │   ├── migrations/         # bookings, anti-overlap constraint and outbox
│   │   ├── src/booking/        # domain rules, API, events and outbox relay
│   │   └── tests/
│   └── notification/
│       ├── migrations/         # processed events and bookings projection
│       ├── src/notification/   # Kafka consumer, reminder scheduler, e-mails and RabbitMQ worker
│       └── tests/
├── web/                        # Vue 3 front-end, served by nginx in Docker
├── docs/
│   ├── adr/                    # architecture decision records
│   └── screenshots/
├── .github/workflows/ci.yml    # lint, types, tests and builds on every push
├── docker-compose.yml
├── CHANGELOG.md
└── pyproject.toml              # uv workspace and tooling configuration
```

## Getting started

### Prerequisites

| Tool | Version | Needed for |
|---|---|---|
| [Docker](https://docs.docker.com/get-docker/) with Compose | 24+ | Running everything, integration tests |
| [uv](https://docs.astral.sh/uv/) | 0.13+ | Local development of the services |
| [Node.js](https://nodejs.org/) | 24+ | Local development of the web app |

### Run with Docker (recommended)

```bash
git clone git@github.com:dev-matheusfranca/VagaCerta.git
cd VagaCerta
docker compose up --build
```

| URL | What |
|---|---|
| http://localhost:8080 | Web app |
| http://localhost:8025 | Mailpit — every e-mail the system sends |
| http://localhost:8090 | Kafka UI — topics and `booking.events` messages |
| http://localhost:15672 | RabbitMQ management — e-mail, retry and dead-letter queues (`guest` / `guest`) |
| http://localhost:8001/docs | Catalog API docs |
| http://localhost:8002/docs | Booking API docs |

Migrations run automatically, and the catalog is seeded with four sample businesses on first start. Book a
slot in the web app and the confirmation e-mail shows up in Mailpit a moment later.

### Run locally

Start the infrastructure with Docker, then run each part in its own terminal:

```bash
docker compose up -d catalog-db booking-db notification-db kafka rabbitmq mailpit
uv sync

cd services/catalog && uv run alembic upgrade head && uv run python -m catalog.seed && cd ../..
cd services/booking && uv run alembic upgrade head && cd ../..
cd services/notification && uv run alembic upgrade head && cd ../..

uv run uvicorn catalog.main:app --port 8001 --reload
uv run uvicorn booking.main:app --port 8002 --reload
uv run python -m booking.outbox_relay
uv run python -m notification

npm --prefix web install
npm --prefix web run dev
```

The web app runs at http://localhost:5173 and proxies `/api/*` to the services.

### Environment variables

| Service | Variable | Default |
|---|---|---|
| catalog | `DATABASE_URL` | `postgresql+asyncpg://vagacerta:vagacerta@localhost:5433/catalog` |
| booking | `DATABASE_URL` | `postgresql+asyncpg://vagacerta:vagacerta@localhost:5434/booking` |
| booking | `CATALOG_URL` | `http://localhost:8001` |
| booking relay | `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9094` |
| notification | `DATABASE_URL` | `postgresql+asyncpg://vagacerta:vagacerta@localhost:5435/notification` |
| notification | `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9094` |
| notification | `RABBITMQ_URL` | `amqp://guest:guest@localhost:5672/` |
| notification | `SMTP_HOST` / `SMTP_PORT` | `localhost` / `1025` |
| notification | `WEB_URL` | `http://localhost:8080` (used in e-mail links) |

## API reference

Full interactive documentation is available at `/docs` on each service.

### Catalog — `:8001`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/businesses` | List businesses |
| `POST` | `/businesses` | Create a business |
| `GET` | `/businesses/{id}` | Business with its professionals, working hours and services |
| `POST` | `/businesses/{id}/professionals` | Add a professional with weekly working hours |
| `POST` | `/businesses/{id}/services` | Add a service with duration and price |

### Booking — `:8002`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/availability` | Free start times for a professional, service and date |
| `POST` | `/bookings` | Book a slot |
| `GET` | `/bookings/{id}` | Booking details |
| `POST` | `/bookings/{id}/cancel` | Cancel a booking; the slot becomes available again |

Example:

```bash
curl -X POST http://localhost:8002/bookings \
  -H "Content-Type: application/json" \
  -d '{
    "business_id": "<business id>",
    "professional_id": "<professional id>",
    "service_id": "<service id>",
    "starts_at": "2026-10-27T10:00:00-03:00",
    "customer_name": "Maria Silva",
    "customer_email": "maria@example.com"
  }'
```

| Status | Meaning |
|---|---|
| `201 Created` | Slot booked |
| `404 Not Found` | Unknown business, professional or service |
| `409 Conflict` | The slot was just taken by someone else |
| `422 Unprocessable Entity` | Invalid data, time outside working hours or in the past |

## Events

Booking publishes to the `booking.events` Kafka topic. Messages are keyed by booking id, so all events of a
booking stay in order.

| Type | Published when | `data` |
|---|---|---|
| `booking.created` | A booking is confirmed | Booking times, customer, business, professional and service details |
| `booking.cancelled` | A confirmed booking is cancelled | `booking_id` |

```json
{
  "event_id": "151a457a-5276-4a3f-896f-dd56508a0fb9",
  "type": "booking.created",
  "occurred_at": "2026-10-23T19:40:28.283996+00:00",
  "data": {
    "booking_id": "80be9d06-b39a-4212-963b-882a7a4ef6a0",
    "starts_at": "2026-10-24T10:00:00-03:00",
    "ends_at": "2026-10-24T10:30:00-03:00",
    "customer_name": "Ana Teste",
    "customer_email": "ana@example.com",
    "business_name": "Barbearia Navalha de Ouro",
    "business_address": "Av. Brasil, 1200 · Zona 01, Maringá/PR",
    "timezone": "America/Sao_Paulo",
    "professional_name": "Diego Almeida",
    "service_name": "Barba completa",
    "price_cents": 3500
  }
}
```

## Testing

```bash
uv run pytest            # all tests (integration tests start containers with Docker)
uv run lint-imports      # architecture rules
uv run mypy services/catalog/src services/booking/src services/notification/src
uv run ruff check && uv run ruff format --check
npm --prefix web run build   # type-checks the web app
```

| Kind | What it proves |
|---|---|
| Unit | Availability and reminder rules; e-mail content, local times and HTML escaping |
| Property-based | Hypothesis generates random agendas; no slot ever overlaps busy time or leaves working hours |
| Integration | API + real PostgreSQL through Testcontainers, with the real migrations |
| Concurrency | 10 simultaneous requests for the same slot: exactly one `201`, nine `409` |
| Outbox | Events are written only when the booking is committed; the relay publishes each one once, in order, to a real Kafka |
| Messaging | Against a real RabbitMQ: e-mails are delivered, retried with backoff and dead-lettered after the last attempt |
| Idempotency | A redelivered event sends no second e-mail; a reminder is sent exactly once and never for cancelled bookings |
| Architecture | Domain modules stay independent of frameworks and brokers |

Every push to `main` and `develop`, and every pull request, runs the whole suite on GitHub Actions, plus
the web build and the Docker image builds.

## Roadmap

- [x] **Phase 1** — Catalog and Booking services, real-time availability, double-booking prevention,
      web app, CI
- [x] **Phase 2** — Domain events on Kafka with the transactional outbox; Notification service with
      e-mails on RabbitMQ (retries, dead-letter queue) and reminders
- [ ] **Phase 3** — Waitlist service (saga): a cancelled slot is offered to the next person in line;
      Keycloak authentication, API gateway and k6 load tests
- [ ] **Phase 4** — OpenTelemetry tracing, Prometheus, Grafana and Loki; Pact contract tests; Analytics
      service with CQRS
- [ ] **Phase 5** — Kubernetes with kind and Helm; natural-language booking with a local LLM (Ollama) and
      an MCP server

See the [changelog](CHANGELOG.md) for what changed in each release.

## Contributing

### Branching model

The repository follows **Gitflow**:

| Branch | Purpose |
|---|---|
| `main` | Production-ready code. Every merge is a release, tagged `vX.Y.Z` |
| `develop` | Integration branch for the next release |
| `feature/<name>` | New work, branched from `develop` and merged back through a pull request |
| `release/<version>` | Release preparation, merged into `main` and `develop` |
| `hotfix/<name>` | Urgent fixes, branched from `main` and merged into `main` and `develop` |

### Commit messages

Commits follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<optional scope>): <short summary in the imperative>
```

| Type | Use for |
|---|---|
| `feat` | A new feature |
| `fix` | A bug fix |
| `test` | Adding or changing tests |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `docs` | Documentation only |
| `ci` / `build` | Pipeline, Docker or dependency changes |
| `chore` | Maintenance tasks |

Examples: `feat(booking): add waitlist offer endpoint`, `fix(web): keep selected day when switching service`.

Before opening a pull request, make sure the [test commands](#testing) pass.

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.

## Author

**Matheus França Santana** — Back-end developer

[![LinkedIn](https://img.shields.io/badge/LinkedIn-matheusfrancasantana-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/matheusfrancasantana/)
[![GitHub](https://img.shields.io/badge/GitHub-dev--matheusfranca-181717?logo=github&logoColor=white)](https://github.com/dev-matheusfranca)
