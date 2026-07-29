# Tracer: approach — journal-project-consent-3030

## Wave order, and why it held

Containment (WP01/WP02) before the durable fix (WP04→WP06), because containment
needed no schema change. That ordering survived contact: WP02 deleted a whole
second leaking drain in a day, and WP04's migration was the load-bearing
prerequisite the plan predicted.

## T010 before T012 was not bureaucratic

The journal had no schema-migration mechanism at all, while all four SQL constants
derive from `_COLUMN_LIST`. Adding columns without the ALTER step would have raised
`no such column` on every journal file on disk. Landing T010 first meant T012 —
which changed `ORDERED_COLUMNS`, touching every derived statement — produced zero
regressions.

## Red-first, measured against the lane's own baseline

Every WP measured before and after. Two lane baselines were wrong on arrival and
would have produced false greens if trusted:

- **lane-c** was cut from a commit predating the #3031 absorption, WP01 and WP02,
  so it reported **0 failures because the acceptance pins did not exist**.
- **lane-d/e** needed the mission branch merged in to see prior WPs' work.

Merging the mission branch into a fresh lane before measuring is now the habit.

## Bugs the plan did not predict

- New captures never populated the identity columns (T012 added them and a
  backfill; `capture_teamspace_bound` built `Event()` without them). The drain
  would have gone silent for live traffic while history stayed deliverable.
- `_sync_once` silently lost its backoff reset and `last_sync` stamp in WP02's WIP.
- A guard's own `except` swallowed a wrong-arity call, so it reported "clean"
  unconditionally while every stub-based test passed.

Each was caught by measurement or by an anchor test, never by reading the diff.

## Test churn was re-basing, not weakening

Roughly 20 tests moved. Every one encoded the pre-amendment default (capture
unconditional, or selection without identity). Each was given a consented identity
and kept asserting what it always did; the non-consenting halves are pinned
separately. Two tests were deleted outright because their contract was removed, not
changed (event→body drain ordering, and the "events failed, skip bodies" gate).
