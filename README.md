<h1 align="center">VagaCerta</h1>

<p align="center">
  <strong>The right time slot, without the back-and-forth of chat messages.</strong><br />
  Online scheduling for small service businesses, built as event-driven microservices.
</p>

<p align="center">
  <a href="https://github.com/dev-matheusfranca/VagaCerta/actions/workflows/ci.yml"><img src="https://github.com/dev-matheusfranca/VagaCerta/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <img src="https://img.shields.io/badge/python-3.13-3776AB?logo=python&logoColor=white" alt="Python 3.13" />
  <img src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
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
3. **Empty chairs** when someone cancels at the last minute and nobody else finds out.

VagaCerta lets customers pick a service, a professional and a free slot in a few clicks, at any hour. The
system **guarantees that a slot is never booked twice**, even when many people try to book it at the same
moment.

The project grows in phases toward a full event-driven architecture with Kafka, RabbitMQ, a waitlist saga,
observability, Kubernetes and AI. See the [roadmap](#roadmap).

## Features

- Browse businesses, their services (duration and price) and their professionals.
- Real-time availability, calculated from each professional's weekly working hours and existing bookings.
- Booking with no double booking under concurrency, enforced by the database.
- Cancellation that immediately returns the slot to the agenda.
- Booking confirmation page that works as a shareable receipt.
- Responsive web app, from phones to wide screens.
- Interactive API documentation (OpenAPI/Swagger) for every service.

## Screenshots

| Choose service, professional and time | Booking confirmation |
|---|---|
| <img src="docs/screenshots/business.png" alt="Business page with services, professionals and free slots" /> | <img src="docs/screenshots/booking.png" alt="Booking confirmation page" /> |

## Architecture

```mermaid
flowchart LR
    user((Customer)) --> web
    web["Web app<br/>Vue 3 + nginx"] -->|/api/catalog| catalog
    web -->|/api/booking| booking
    booking -->|REST| catalog
    catalog["Catalog service<br/>FastAPI"] --> catalogdb[(PostgreSQL<br/>catalog)]
    booking["Booking service<br/>FastAPI"] --> bookingdb[(PostgreSQL<br/>booking)]
```

| Component | Responsibility |
|---|---|
| **catalog** | Businesses, professionals, services and weekly working hours |
| **booking** | Availability calculation, bookings and cancellations |
| **web** | Customer-facing booking flow; nginx also routes `/api/*` to the services |

### Design decisions

- **Database per service.** Each service owns its schema and migrations; they only talk through APIs.
- **Anti-corruption layer.** Booking reads Catalog through
  [`catalog_client.py`](services/booking/src/booking/catalog_client.py), which maps only the fields it needs.
- **Framework-free domain.** Availability rules live in pure functions
  ([`domain.py`](services/booking/src/booking/domain.py)); an architecture test forbids that module from
  importing FastAPI, SQLAlchemy, httpx or Pydantic.
- **Concurrency handled by PostgreSQL.** An exclusion constraint rejects overlapping bookings, so the API
  returns `409 Conflict` to everyone but the first request.

Each decision is recorded as an ADR:

- [ADR 0001 — Python + FastAPI](docs/adr/0001-python-fastapi.md)
- [ADR 0002 — Double booking is prevented by the database](docs/adr/0002-double-booking-exclusion-constraint.md)

## Tech stack

| Layer | Technologies |
|---|---|
| Services | Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2 (async), asyncpg, Alembic |
| Database | PostgreSQL 17 (`btree_gist` exclusion constraint) |
| Web | Vue 3, TypeScript, Vite, Tailwind CSS 4, Vue Router, Lucide icons |
| Testing | pytest, Testcontainers, Hypothesis, import-linter |
| Code quality | ruff (lint + format), mypy (strict), vue-tsc |
| Infrastructure | Docker, Docker Compose, nginx, GitHub Actions |
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
│   └── booking/
│       ├── migrations/         # includes the anti-overlap constraint
│       ├── src/booking/        # domain rules, API routes and Catalog client
│       └── tests/
├── web/                        # Vue 3 front-end, served by nginx in Docker
├── docs/
│   ├── adr/                    # architecture decision records
│   └── screenshots/
├── .github/workflows/ci.yml    # lint, types, tests and builds on every push
├── docker-compose.yml
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
| http://localhost:8001/docs | Catalog API docs |
| http://localhost:8002/docs | Booking API docs |

Migrations run automatically, and the catalog is seeded with four sample businesses on first start.

### Run locally

Start only the databases with Docker, then run each part in its own terminal:

```bash
docker compose up -d catalog-db booking-db
uv sync

cd services/catalog && uv run alembic upgrade head && uv run python -m catalog.seed && cd ../..
cd services/booking && uv run alembic upgrade head && cd ../..

uv run uvicorn catalog.main:app --port 8001 --reload
uv run uvicorn booking.main:app --port 8002 --reload

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

## Testing

```bash
uv run pytest            # all tests (integration tests start PostgreSQL with Docker)
uv run lint-imports      # architecture rules
uv run mypy services/catalog/src services/booking/src
uv run ruff check && uv run ruff format --check
npm --prefix web run build   # type-checks the web app
```

| Kind | What it proves |
|---|---|
| Unit | Availability rules: working periods, busy time and past slots |
| Property-based | Hypothesis generates random agendas; no slot ever overlaps busy time or leaves working hours |
| Integration | API + real PostgreSQL through Testcontainers, with the real migrations |
| Concurrency | 10 simultaneous requests for the same slot: exactly one `201`, nine `409` |
| Architecture | The booking domain stays independent of frameworks |

Every push to `main` and `develop`, and every pull request, runs the whole suite on GitHub Actions, plus
the web build and the Docker image builds.

## Roadmap

- [x] **Phase 1** — Catalog and Booking services, real-time availability, double-booking prevention,
      web app, CI
- [ ] **Phase 2** — Domain events on Kafka with the Outbox pattern; Notification service on RabbitMQ with
      retries, dead-letter queue and delayed reminders
- [ ] **Phase 3** — Waitlist service (saga): a cancelled slot is offered to the next person in line;
      Keycloak authentication, API gateway and k6 load tests
- [ ] **Phase 4** — OpenTelemetry tracing, Prometheus, Grafana and Loki; Pact contract tests; Analytics
      service with CQRS
- [ ] **Phase 5** — Kubernetes with kind and Helm; natural-language booking with a local LLM (Ollama) and
      an MCP server

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
