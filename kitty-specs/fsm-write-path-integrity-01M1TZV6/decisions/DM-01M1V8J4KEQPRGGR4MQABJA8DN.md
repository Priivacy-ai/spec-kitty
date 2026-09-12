# Decision Moment `01M1V8J4KEQPRGGR4MQABJA8DN`

- **Mission:** `fsm-write-path-integrity-01M1TZV6`
- **Origin flow:** `plan`
- **Slot key:** `plan.wp02.emit-cost`
- **Input key:** `emit_cost_policy`
- **Status:** `resolved`
- **Created:** `2026-09-06T11:44:49.774591+00:00`
- **Resolved:** `2026-09-06T11:48:40.496845+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

Q7: WP02 preserves O(n) _derive_from_lane full-log read, or allows snapshot-anchored read in scope?

## Options

- Preserve; follow-up on #3893 (default)
- Allow snapshot-anchored read
- Other

## Final answer

Preserve. _derive_from_lane still invoked at most once per emit and reads the full log exactly once (NFR-004 call-count assertion). Snapshot-anchored read and compaction are follow-ups on #3893 with the O(n^2) evidence.

## Rationale

_(none)_

## Change log

- `2026-09-06T11:44:49.774591+00:00` — opened
- `2026-09-06T11:48:40.496845+00:00` — resolved (final_answer="Preserve. _derive_from_lane still invoked at most once per emit and reads the full log exactly once (NFR-004 call-count assertion). Snapshot-anchored read and compaction are follow-ups on #3893 with the O(n^2) evidence.")
