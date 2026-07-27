# Decision Moment `01KTRFSGQ3W8YE5CD1WNSQKG0A`

- **Mission:** `01KTRC04`
- **Origin flow:** `plan`
- **Slot key:** `plan.analysis.findings-carrier`
- **Input key:** `findings_carrier`
- **Status:** `resolved`
- **Created:** `2026-06-10T10:03:35.523959+00:00`
- **Resolved:** `2026-06-10T10:06:58.485108+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

FR-004: structured findings carrier form?

## Options

- frontmatter-block
- validated-table-contract
- both

## Final answer

Frontmatter block (operator choice): schema-validated YAML frontmatter on analysis-report.md (analysis-findings/v1: findings[] with id+severity from a canonical enum, counts). Verdict computed from frontmatter only; body prose is presentation; malformed/missing carrier fails loudly.

## Rationale

_(none)_

## Change log

- `2026-06-10T10:03:35.523959+00:00` — opened
- `2026-06-10T10:06:58.485108+00:00` — resolved (final_answer="Frontmatter block (operator choice): schema-validated YAML frontmatter on analysis-report.md (analysis-findings/v1: findings[] with id+severity from a canonical enum, counts). Verdict computed from frontmatter only; body prose is presentation; malformed/missing carrier fails loudly.")
