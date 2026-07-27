# Decision Moment `01KXRVT2KA1Y3M4XQAYVQ3HHXF`

- **Mission:** `doctrine-activation-freshness-01KXRSDN`
- **Origin flow:** `plan`
- **Slot key:** `plan.freshness.references-hash-fork`
- **Input key:** `references_hash_fork`
- **Status:** `resolved`
- **Created:** `2026-07-17T20:20:42.218287+00:00`
- **Resolved:** `2026-07-17T20:26:26.596912+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

How should #2758 fix the references.yaml permanent-stale (references.yaml is in the 4-file content-hash but sync never writes it)?

## Options

- fail-closed-preflight
- narrow-to-triad
- Other

## Final answer

fail-closed-preflight: keep the 4-file content-hash; when references.yaml is absent surface a single actionable 'run charter generate first' preflight instead of a dead-end None. Leaves #2773's references.yaml deprecation clean (no stopgap). No dual-edit, no manifest derived-set change.

## Rationale

_(none)_

## Change log

- `2026-07-17T20:20:42.218287+00:00` — opened
- `2026-07-17T20:26:26.596912+00:00` — resolved (final_answer="fail-closed-preflight: keep the 4-file content-hash; when references.yaml is absent surface a single actionable 'run charter generate first' preflight instead of a dead-end None. Leaves #2773's references.yaml deprecation clean (no stopgap). No dual-edit, no manifest derived-set change.")
