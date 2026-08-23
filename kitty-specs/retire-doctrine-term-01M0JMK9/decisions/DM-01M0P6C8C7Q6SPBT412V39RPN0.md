# Decision Moment `01M0P6C8C7Q6SPBT412V39RPN0`

- **Mission:** `retire-doctrine-term-01M0JMK9`
- **Origin flow:** `plan`
- **Slot key:** `plan.m5.serialized-historical-records`
- **Input key:** `serialized_historical_records_disposition`
- **Status:** `deferred`
- **Created:** `2026-08-23T02:14:45.895803+00:00`
- **Resolved:** `2026-08-23T02:15:11.671904+00:00`
- **Resolved by:** `operator`
- **Opened by:** `operator`
- **Other answer:** `false`

## Question

How does M5 treat tracked serialized runtime records keyed to immutable kitty-specs/ archive slugs or retired profile IDs (mission-state quarantine status.events.jsonl, kitty-ops/*.jsonl, .kittify/missions/**/retrospective.yaml)?

## Options

- Treat as immutable historical records: add them to the fixed exclusion set next to kitty-specs/ (amend DM-01M0NMS9WPH33EPFCJQRTQVNSA)
- Untrack/delete after verified backup (Git history retains them)
- Schema-aware rewrite with CR-08-style aliases for profile IDs; slug values keep the archive slug

## Final answer

_(none)_

## Rationale

Operator call raised by the whole-mission adversarial squad (architect lens): each option changes the M5 row set and the terminal gate — excluding these records alongside kitty-specs/ amends DM-01M0NMS9WPH33EPFCJQRTQVNSA, untracking loses tracked history, rewriting breaks linkage to immutable archive slugs. Resolve before M5 is specified; M1-M4 are unaffected.

## Change log

- `2026-08-23T02:14:45.895803+00:00` — opened
- `2026-08-23T02:15:11.671904+00:00` — deferred
