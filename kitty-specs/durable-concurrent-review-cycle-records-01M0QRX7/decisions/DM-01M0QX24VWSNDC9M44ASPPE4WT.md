# Decision Moment `01M0QX24VWSNDC9M44ASPPE4WT`

- **Mission:** `durable-concurrent-review-cycle-records-01M0QRX7`
- **Origin flow:** `plan`
- **Slot key:** `plan.reliability.queue-timeout`
- **Input key:** `queue_timeout`
- **Status:** `resolved`
- **Created:** `2026-08-23T18:10:26.300131+00:00`
- **Resolved:** `2026-08-23T18:10:27.589155+00:00`
- **Resolved by:** `operator`
- **Opened by:** `codex`
- **Other answer:** `false`

## Question

How long should a verdict save wait for the queue before refusing?

## Options

- 10 seconds
- 30 seconds
- Other

## Final answer

Wait at most 10 seconds, then return an explicit busy failure with no automatic command retry.

## Rationale

Ten seconds is sufficient for ordinary verdict commits while bounding a stuck holder.

## Change log

- `2026-08-23T18:10:26.300131+00:00` — opened
- `2026-08-23T18:10:27.589155+00:00` — resolved (final_answer="Wait at most 10 seconds, then return an explicit busy failure with no automatic command retry.")
