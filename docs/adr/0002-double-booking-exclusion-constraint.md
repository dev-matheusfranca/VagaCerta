# ADR 0002 — Double booking is prevented by the database

**Status:** accepted

## Context

Two customers can try to book the same professional at overlapping times at the same moment. A check in the
application ("is this slot free?") followed by an insert is a race condition: both requests pass the check
and both insert.

## Decision

The `bookings` table has a PostgreSQL **exclusion constraint**:

```sql
EXCLUDE USING gist (professional_id WITH =, tstzrange(starts_at, ends_at) WITH &&)
WHERE (status = 'confirmed')
```

The application validates that the slot fits the professional's working hours, inserts, and turns a
constraint violation into `409 Conflict`.

## Consequences

- Correct under any concurrency, with no application-level locks or distributed locks.
- Overlaps are detected for any duration, not only for identical start times (a unique index would miss
  09:00–10:00 vs 09:30–10:30).
- Cancelled bookings are outside the constraint, so a cancelled slot can be booked again immediately.
- Requires the `btree_gist` extension, which ships with PostgreSQL.
- Covered by `test_only_one_of_many_simultaneous_requests_gets_the_slot`.
