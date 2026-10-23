# ADR 0001 — Python + FastAPI for the services

**Status:** accepted

## Context

The services are I/O bound (HTTP, PostgreSQL, and later Kafka and RabbitMQ) and the project will add AI
features (local LLM, MCP server) in later phases.

## Decision

Use Python 3.13 with FastAPI, async SQLAlchemy 2 and Pydantic v2, managed as a single **uv workspace**
with one package per service.

## Consequences

- Async end to end: one process handles many concurrent requests waiting on I/O.
- Pydantic validates every input at the edge and generates OpenAPI docs for free.
- The Python ecosystem covers the AI phases without introducing another language.
- One lock file for the whole repository; each service still builds its own image with only its dependencies
  (`uv sync --package <service>`).
