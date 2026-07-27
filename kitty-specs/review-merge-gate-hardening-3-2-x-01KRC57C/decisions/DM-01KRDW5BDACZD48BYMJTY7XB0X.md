# Decision Moment `01KRDW5BDACZD48BYMJTY7XB0X`

- **Mission:** `review-merge-gate-hardening-3-2-x-01KRC57C`
- **Origin flow:** `plan`
- **Slot key:** `plan.wp03.issue-matrix-validator-strictness`
- **Input key:** `issue_matrix_validator_mode`
- **Status:** `resolved`
- **Created:** `2026-05-12T10:36:43.818918+00:00`
- **Resolved:** `2026-05-12T10:40:18.840105+00:00`
- **Other answer:** `false`

## Question

issue-matrix.md validator strictness: real-world drift exists today (4-col vs 5-col tables; 'Evidence ref' vs 'evidence_ref' capitalization; narrative-before-table vs table-first). What's the validator's contract?

## Options

- strict_header_additive_tolerant_loose_body
- strict_throughout
- loose_warn_only
- Other

## Final answer

strict_header_additive_tolerant_loose_body — Header must contain canonical 4 columns 'Issue | Scope | Verdict | Evidence ref' in that order; additional columns may be appended freely; renames/reorders/removals hard-fail with diagnostic MISSION_REVIEW_ISSUE_MATRIX_SCHEMA_DRIFT; body cells stay free-form Markdown.

## Rationale

_(none)_

## Change log

- `2026-05-12T10:36:43.818918+00:00` — opened
- `2026-05-12T10:40:18.840105+00:00` — resolved (final_answer="strict_header_additive_tolerant_loose_body — Header must contain canonical 4 columns 'Issue | Scope | Verdict | Evidence ref' in that order; additional columns may be appended freely; renames/reorders/removals hard-fail with diagnostic MISSION_REVIEW_ISSUE_MATRIX_SCHEMA_DRIFT; body cells stay free-form Markdown.")
