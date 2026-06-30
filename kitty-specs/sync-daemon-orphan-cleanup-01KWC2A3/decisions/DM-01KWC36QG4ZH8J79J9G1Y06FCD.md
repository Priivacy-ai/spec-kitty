# Decision Moment `01KWC36QG4ZH8J79J9G1Y06FCD`

- **Mission:** `sync-daemon-orphan-cleanup-01KWC2A3`
- **Origin flow:** `plan`
- **Slot key:** `plan.reset.operator-required-confirmation`
- **Input key:** `reset_operator_required_ux`
- **Status:** `resolved`
- **Created:** `2026-06-30T11:04:07.428732+00:00`
- **Resolved:** `2026-06-30T11:05:14.401976+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

How should 'auth doctor --reset' treat operator_required daemons (cross-root / pre-marker / ambiguous)?

## Options

- Require explicit --force or confirmation before killing operator_required
- --reset cleans all cleanable (safe_auto + operator_required) in one shot
- Other

## Final answer

Guard operator_required behind explicit confirmation: --reset auto-cleans safe_auto, but requires interactive y/N (or --force in --json/non-interactive) before killing operator_required (cross-root/different-HOME/ambiguous) daemons.

## Rationale

_(none)_

## Change log

- `2026-06-30T11:04:07.428732+00:00` — opened
- `2026-06-30T11:05:14.401976+00:00` — resolved (final_answer="Guard operator_required behind explicit confirmation: --reset auto-cleans safe_auto, but requires interactive y/N (or --force in --json/non-interactive) before killing operator_required (cross-root/different-HOME/ambiguous) daemons.")
