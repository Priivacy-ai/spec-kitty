# Decision Moment `01KX5SK7HMAK0SYYERNGPY2TG6`

- **Mission:** `unify-charter-activation-surfaces-01KX5SJ9`
- **Origin flow:** `specify`
- **Slot key:** `specify.reconciliation.direction`
- **Input key:** `reconciliation_direction`
- **Status:** `resolved`
- **Created:** `2026-07-10T10:36:26.548464+00:00`
- **Resolved:** `2026-07-10T10:55:00.119160+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

How should config.activated_* and answers.selected_* be reconciled so activation never dangles?

## Options

- write-through-plus-resynthesize
- config-single-authority
- explicit-resynthesize-flag

## Final answer

config-single-authority: config.activated_* is THE single activation authority; references.yaml + graph + the compiled reference set derive from config.activated_*; answers.selected_* is retired as an activation source (interview-record only); consistency_check asserts references/graph parity with config and fails closed on divergence.

## Rationale

_(none)_

## Change log

- `2026-07-10T10:36:26.548464+00:00` — opened
- `2026-07-10T10:55:00.119160+00:00` — resolved (final_answer="config-single-authority: config.activated_* is THE single activation authority; references.yaml + graph + the compiled reference set derive from config.activated_*; answers.selected_* is retired as an activation source (interview-record only); consistency_check asserts references/graph parity with config and fails closed on divergence.")
