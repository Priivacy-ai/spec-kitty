# Decision Moment `01M0QX16N1VRWH7HDKP6W6W8WG`

- **Mission:** `durable-concurrent-review-cycle-records-01M0QRX7`
- **Origin flow:** `plan`
- **Slot key:** `plan.architecture.queue-behavior`
- **Input key:** `queue_behavior`
- **Status:** `resolved`
- **Created:** `2026-08-23T18:09:55.361155+00:00`
- **Resolved:** `2026-08-23T18:10:20.363650+00:00`
- **Resolved by:** `operator`
- **Opened by:** `codex`
- **Other answer:** `false`

## Question

When two reviewers save verdicts concurrently, should the second wait or should colliding saves retry?

## Options

- wait in line
- retry on collision
- Other

## Final answer

Wait in line; the second verdict save waits for the first.

## Rationale

The operator chose the simpler serialized behavior over collision retry.

## Change log

- `2026-08-23T18:09:55.361155+00:00` — opened
- `2026-08-23T18:10:20.363650+00:00` — resolved (final_answer="Wait in line; the second verdict save waits for the first.")
