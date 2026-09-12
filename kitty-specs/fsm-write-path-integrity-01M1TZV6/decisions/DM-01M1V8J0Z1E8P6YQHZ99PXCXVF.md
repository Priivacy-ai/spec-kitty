# Decision Moment `01M1V8J0Z1E8P6YQHZ99PXCXVF`

- **Mission:** `fsm-write-path-integrity-01M1TZV6`
- **Origin flow:** `plan`
- **Slot key:** `plan.wp01.superseded-retro-writer`
- **Input key:** `superseded_retro_writer`
- **Status:** `resolved`
- **Created:** `2026-09-06T11:44:46.049561+00:00`
- **Resolved:** `2026-09-06T11:48:37.141271+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

Q3: Harden retrospective/events.py (superseded run_terminus path) or deprecation note only, prioritizing lifecycle_events.py?

## Options

- Harden both, live one first (default)
- Deprecation note only for events.py
- Other

## Final answer

Harden both; retrospective/lifecycle_events.py (live post-merge path) first, retrospective/events.py (superseded run_terminus path) second with its existing do-not-add-callers note preserved.

## Rationale

_(none)_

## Change log

- `2026-09-06T11:44:46.049561+00:00` — opened
- `2026-09-06T11:48:37.141271+00:00` — resolved (final_answer="Harden both; retrospective/lifecycle_events.py (live post-merge path) first, retrospective/events.py (superseded run_terminus path) second with its existing do-not-add-callers note preserved.")
