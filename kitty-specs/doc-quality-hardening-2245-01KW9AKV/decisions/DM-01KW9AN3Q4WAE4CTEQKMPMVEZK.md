# Decision Moment `01KW9AN3Q4WAE4CTEQKMPMVEZK`

- **Mission:** `doc-quality-hardening-2245-01KW9AKV`
- **Origin flow:** `specify`
- **Slot key:** `specify.adr.link-approach`
- **Input key:** `adr_link_approach`
- **Status:** `resolved`
- **Created:** `2026-06-29T09:16:35.428736+00:00`
- **Resolved:** `2026-06-29T09:16:55.154826+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

For the ~26 broken links inside byte-invariant ADR bodies, which approach?

## Options

- Redirect-aware tolerant gate
- One-time C-002-waived migration
- Other

## Final answer

One-time C-002-waived migration: rewrite the ~26 dead links in ADR bodies to live targets in a sanctioned pass, amend 2026-06-27-1-common-docs-reconciliation.md with the waiver+before/after rationale, and re-pin the byte-invariance baseline. Preferred over a redirect-tolerant gate for a clean end-state with no link indirection; lets the new gate cover docs/adr/ with no special tolerance afterward.

## Rationale

_(none)_

## Change log

- `2026-06-29T09:16:35.428736+00:00` — opened
- `2026-06-29T09:16:55.154826+00:00` — resolved (final_answer="One-time C-002-waived migration: rewrite the ~26 dead links in ADR bodies to live targets in a sanctioned pass, amend 2026-06-27-1-common-docs-reconciliation.md with the waiver+before/after rationale, and re-pin the byte-invariance baseline. Preferred over a redirect-tolerant gate for a clean end-state with no link indirection; lets the new gate cover docs/adr/ with no special tolerance afterward.")
