# ADR 0003 — Transactional outbox for booking events

**Status:** accepted

## Context

Other services need to react when a booking is created or cancelled. Writing the booking to PostgreSQL and
then publishing to Kafka is a dual write: if the process dies between the two, either the booking exists
without an event, or an event announces a booking that was rolled back (for example, by the anti-overlap
constraint).

## Decision

Booking writes the event to an `outbox` table **in the same transaction** as the booking change. A separate
process, the outbox relay, polls pending rows in id order, publishes them to the `booking.events` topic and
marks them as published.

- Rows are selected with `FOR UPDATE SKIP LOCKED`, so several relay replicas can run without publishing the
  same event at the same time.
- Messages are keyed by booking id, so all events of one booking land on the same partition, in order.
- A partial index on pending rows keeps polling cheap as the table grows.

## Consequences

- An event is published if and only if the booking change was committed.
- Delivery is **at least once**: if the relay crashes after publishing but before marking a row, the event
  is published again. Consumers must be idempotent (see the `processed_events` table in Notification).
- Events reach Kafka with a small delay (the polling interval, 0.5 s when idle).
- Change data capture (Debezium) would remove polling, at the cost of running Kafka Connect; polling is
  enough for this volume.
