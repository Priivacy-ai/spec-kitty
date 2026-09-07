# Decision Moment `01M1V8HXAVBEYAMC67M5KBHDEY`

- **Mission:** `fsm-write-path-integrity-01M1TZV6`
- **Origin flow:** `plan`
- **Slot key:** `plan.wp01.batch-lock-placement`
- **Input key:** `batch_lock_placement`
- **Status:** `resolved`
- **Created:** `2026-09-06T11:44:42.332056+00:00`
- **Resolved:** `2026-09-06T11:48:33.293821+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

Q1: Batch door lock (FR-018) lands in WP01 (store layer, immediately) or WP02 (shell composition, single-owner files)?

## Options

- WP02 (default)
- WP01
- Other

## Final answer

WP02. Batch door acquires feature_status_lock as part of the shell composition, keeping status/emit.py single-owner (WP02). WP01 owns only out-of-pipeline writers.

## Rationale

_(none)_

## Change log

- `2026-09-06T11:44:42.332056+00:00` — opened
- `2026-09-06T11:48:33.293821+00:00` — resolved (final_answer="WP02. Batch door acquires feature_status_lock as part of the shell composition, keeping status/emit.py single-owner (WP02). WP01 owns only out-of-pipeline writers.")
