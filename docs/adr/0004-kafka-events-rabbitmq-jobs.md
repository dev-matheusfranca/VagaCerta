# ADR 0004 — Kafka for events, RabbitMQ for e-mail jobs

**Status:** accepted

## Context

The system needs two kinds of messaging:

1. **Domain events** (`booking.created`, `booking.cancelled`): facts that several services will consume over
   time (Notification now; Waitlist and Analytics in later phases), possibly replaying history.
2. **E-mail jobs**: units of work that must be retried when the SMTP server fails, with increasing delays,
   and set aside for inspection when they keep failing.

## Decision

- Domain events go to **Kafka**. Each consumer group keeps its own offset, and the log can be replayed to
  build new read models.
- E-mail jobs go to **RabbitMQ**, using one retry queue per attempt:

  | Queue | Role |
  |---|---|
  | `notification.email` | Jobs ready to be sent |
  | `notification.email.retry.N` | Waits for a fixed TTL (5 s, 30 s, 2 min), then dead-letters back to `notification.email` |
  | `notification.email.dead` | Jobs that failed every attempt, kept for inspection |

  The worker acknowledges the original message and republishes it to the next queue with an
  `x-failed-attempts` header.

## Consequences

- Each broker does what it is best at: a replayable log for facts, per-message acknowledgement and
  dead-lettering for jobs.
- Fixed TTL per queue gives increasing delays without the delayed-message plugin and without
  head-of-line blocking (a single queue with different per-message TTLs only expires messages at its head).
- Two brokers to operate instead of one. Acceptable here: the project also aims to show both tools in
  their natural roles.
- E-mail delivery is at least once: a crash after sending but before acknowledging resends the e-mail.
