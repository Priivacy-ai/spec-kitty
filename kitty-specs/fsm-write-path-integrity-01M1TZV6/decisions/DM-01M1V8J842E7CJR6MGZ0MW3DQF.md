# Decision Moment `01M1V8J842E7CJR6MGZ0MW3DQF`

- **Mission:** `fsm-write-path-integrity-01M1TZV6`
- **Origin flow:** `plan`
- **Slot key:** `plan.wp05.run-index-migration`
- **Input key:** `run_index_migration_shape`
- **Status:** `resolved`
- **Created:** `2026-09-06T11:44:53.378704+00:00`
- **Resolved:** `2026-09-06T12:39:01.720396+00:00`
- **Resolved by:** `claude-fable-5-1 (WP05 implementer)`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

Q9: Run-index rekey shape (in-place on first touch vs one-shot migrate) and legacy key (adopt legacy-<slug> precedent?)

## Options

- Defer to WP05 implementer
- In-place rekey + legacy-<slug>
- One-shot migrate
- Other

## Final answer

In-place rekey + legacy-<slug>

## Rationale

In-place rekey on first touch by get_or_start_run (the index's single writer); readers canonicalize in memory only. Key is mission_id, or legacy-<slug> for a mission without one (the status_transition.py lock-key precedent). Idempotent and lossless; see design-notes/WP05-run-state.md.

## Change log

- `2026-09-06T11:44:53.378704+00:00` — opened
- `2026-09-06T12:39:01.720396+00:00` — resolved (final_answer="In-place rekey + legacy-<slug>")
