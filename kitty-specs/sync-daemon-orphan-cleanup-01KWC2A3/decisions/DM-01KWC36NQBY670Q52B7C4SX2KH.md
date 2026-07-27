# Decision Moment `01KWC36NQBY670Q52B7C4SX2KH`

- **Mission:** `sync-daemon-orphan-cleanup-01KWC2A3`
- **Origin flow:** `plan`
- **Slot key:** `plan.cleanup.wedged-listener-classification`
- **Input key:** `wedged_listener_class`
- **Status:** `resolved`
- **Created:** `2026-06-30T11:04:05.611934+00:00`
- **Resolved:** `2026-06-30T11:05:12.431890+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

How should a sync-range listener that does NOT answer /api/health (wedged/unresponsive) but has provable cmdline scope markers be classified?

## Options

- operator_required (require a live health self-report for safe_auto)
- safe_auto (cmdline scope-proof alone suffices)
- Other

## Final answer

operator_required: require a live /api/health self-report for safe_auto; a wedged/unresponsive in-range listener with cmdline scope-proof is operator_required (surfaced, cleaned by --reset, never auto-killed at startup).

## Rationale

_(none)_

## Change log

- `2026-06-30T11:04:05.611934+00:00` — opened
- `2026-06-30T11:05:12.431890+00:00` — resolved (final_answer="operator_required: require a live /api/health self-report for safe_auto; a wedged/unresponsive in-range listener with cmdline scope-proof is operator_required (surfaced, cleaned by --reset, never auto-killed at startup).")
