# Decision Moment `01KQEKDHEN3AC6QG4241TP5E9G`

- **Mission:** `auth-tranche-2-5-cli-contract-consumption-01KQEJZK`
- **Origin flow:** `plan`
- **Slot key:** `plan.refresh.replay_retry_location`
- **Input key:** `replay_retry_location`
- **Status:** `resolved`
- **Created:** `2026-04-30T07:07:27.574216+00:00`
- **Resolved:** `2026-04-30T07:11:17.971817+00:00`
- **Other answer:** `false`

## Question

Where should the benign 409 replay retry happen: (A) inside _run_locked (transparent to token_manager — one transaction, one retry within the lock), or (B) surfaced as a new RefreshOutcome that token_manager handles with a second run_refresh_transaction call (two distinct transactions)?

## Options

- Inside _run_locked (one transaction)
- New outcome surfaced to token_manager (two transactions)

## Final answer

Inside _run_locked (one transaction)

## Rationale

_(none)_

## Change log

- `2026-04-30T07:07:27.574216+00:00` — opened
- `2026-04-30T07:11:17.971817+00:00` — resolved (final_answer="Inside _run_locked (one transaction)")
