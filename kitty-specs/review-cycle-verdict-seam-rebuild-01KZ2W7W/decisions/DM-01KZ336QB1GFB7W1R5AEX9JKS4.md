# Decision Moment `01KZ336QB1GFB7W1R5AEX9JKS4`

- **Mission:** `review-cycle-verdict-seam-rebuild-01KZ2W7W`
- **Origin flow:** `plan`
- **Slot key:** `plan.concurrency.serialization-boundary`
- **Input key:** `serialization_boundary`
- **Status:** `resolved`
- **Created:** `2026-08-03T05:58:02.849043+00:00`
- **Resolved:** `2026-08-03T06:29:47.118806+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

How should FR-005 serialize concurrent verdict writes given NFR-006 forbids holding an inter-process lock across a git subprocess?

## Options

_(none)_

## Final answer

Lock allocation+write, retry the commit. feature_status_lock covers next_cycle_number and the file write only; the commit runs outside it with retry-on-index-contention. Honours NFR-006's no-lock-across-subprocess rule; a contention loser retries rather than losing its verdict.

## Rationale

_(none)_

## Change log

- `2026-08-03T05:58:02.849043+00:00` — opened
- `2026-08-03T06:29:47.118806+00:00` — resolved (final_answer="Lock allocation+write, retry the commit. feature_status_lock covers next_cycle_number and the file write only; the commit runs outside it with retry-on-index-contention. Honours NFR-006's no-lock-across-subprocess rule; a contention loser retries rather than losing its verdict.")
