# Decision Moment `01KZ1ED8JHG7C0DKBGKZVQMA09`

- **Mission:** `review-verdict-write-integrity-01KZ1CGF`
- **Origin flow:** `plan`
- **Slot key:** `plan.architecture.approved-writer-shape`
- **Input key:** `approved_writer_shape`
- **Status:** `resolved`
- **Created:** `2026-08-02T14:35:22.577336+00:00`
- **Resolved:** `2026-08-02T14:47:59.427721+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

FR-001 needs a function that persists an approved-verdict review-cycle artifact. Should it be a new function create_approved_review_cycle, or should create_rejected_review_cycle be generalized with a verdict parameter (shared with FR-002's provenance-validation guard)?

## Options

- New function create_approved_review_cycle (mirrors the existing rejected-writer, minimal risk to existing callers)
- Generalize create_rejected_review_cycle with a verdict parameter (single code path for both verdicts, shared validation)
- Other

## Final answer

Generalize create_rejected_review_cycle with a verdict parameter (verdict="rejected" default preserves existing call sites); FR-002's provenance guard protects both verdicts in the same function.

## Rationale

_(none)_

## Change log

- `2026-08-02T14:35:22.577336+00:00` — opened
- `2026-08-02T14:47:59.427721+00:00` — resolved (final_answer="Generalize create_rejected_review_cycle with a verdict parameter (verdict="rejected" default preserves existing call sites); FR-002's provenance guard protects both verdicts in the same function.")
