# Decision Moment `01KZJQP5K4C0VGNB53GZZT3QWP`

- **Mission:** `charter-synthesize-reconciliation-01KZJQN6`
- **Origin flow:** `specify`
- **Slot key:** `specify.reconciliation.drop-semantics`
- **Input key:** `drop_semantics`
- **Status:** `resolved`
- **Created:** `2026-08-09T07:44:36.964642+00:00`
- **Resolved:** `2026-08-09T07:44:38.047833+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

Default semantics when a synthesize rebuild no longer targets content that still exists in the on-disk graph (backed by doctrine artifacts)?

## Options

- preserve-by-default
- refuse-with-prune
- hybrid

## Final answer

refuse-with-prune: a plain synthesize that would drop still-backed nodes/edges fails closed and lists the deletions; removal requires an explicit --prune opt-in

## Rationale

_(none)_

## Change log

- `2026-08-09T07:44:36.964642+00:00` — opened
- `2026-08-09T07:44:38.047833+00:00` — resolved (final_answer="refuse-with-prune: a plain synthesize that would drop still-backed nodes/edges fails closed and lists the deletions; removal requires an explicit --prune opt-in")
