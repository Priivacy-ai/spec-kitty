# Decision Moment `01KYPD2JTZXX9B033EW9QVM7Y3`

- **Mission:** `write-side-seam-matrix-tracer-01KYP3MH`
- **Origin flow:** `plan`
- **Slot key:** `plan.matrix.issue-backcompat`
- **Input key:** `issue_matrix_backcompat`
- **Status:** `resolved`
- **Created:** `2026-07-29T07:40:25.311669+00:00`
- **Resolved:** `2026-07-29T07:44:56.408024+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

Back-compat for existing markdown issue-matrix.md: dual-read+migrate or forward-only?

## Options

- dual-read-and-migrate
- forward-only
- Other

## Final answer

Migrate-on-write + failover-read (read legacy issue-matrix.md when issue-matrix.json is absent), via a shared migration sub-module that also backs a dedicated bulk-migration command for one-shot swap-over.

## Rationale

_(none)_

## Change log

- `2026-07-29T07:40:25.311669+00:00` — opened
- `2026-07-29T07:44:56.408024+00:00` — resolved (final_answer="Migrate-on-write + failover-read (read legacy issue-matrix.md when issue-matrix.json is absent), via a shared migration sub-module that also backs a dedicated bulk-migration command for one-shot swap-over.")
