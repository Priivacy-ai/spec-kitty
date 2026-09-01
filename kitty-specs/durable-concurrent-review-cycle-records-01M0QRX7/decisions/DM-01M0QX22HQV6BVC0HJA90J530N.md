# Decision Moment `01M0QX22HQV6BVC0HJA90J530N`

- **Mission:** `durable-concurrent-review-cycle-records-01M0QRX7`
- **Origin flow:** `plan`
- **Slot key:** `plan.architecture.queue-granularity`
- **Input key:** `queue_granularity`
- **Status:** `resolved`
- **Created:** `2026-08-23T18:10:23.927172+00:00`
- **Resolved:** `2026-08-23T18:10:25.034823+00:00`
- **Resolved by:** `operator`
- **Opened by:** `codex`
- **Other answer:** `false`

## Question

Should the verdict queue cover all missions using the same Git checkout?

## Options

- checkout-wide across missions
- per mission
- Other

## Final answer

Checkout-wide across missions sharing the same Git checkout.

## Rationale

All such verdict commits share one staging area, even though cross-mission collisions are unlikely.

## Change log

- `2026-08-23T18:10:23.927172+00:00` — opened
- `2026-08-23T18:10:25.034823+00:00` — resolved (final_answer="Checkout-wide across missions sharing the same Git checkout.")
