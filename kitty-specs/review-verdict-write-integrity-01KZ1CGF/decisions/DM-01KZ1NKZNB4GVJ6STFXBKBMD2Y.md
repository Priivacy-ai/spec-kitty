# Decision Moment `01KZ1NKZNB4GVJ6STFXBKBMD2Y`

- **Mission:** `review-verdict-write-integrity-01KZ1CGF`
- **Origin flow:** `plan`
- **Slot key:** `plan.post-plan-squad.ic03-fate`
- **Input key:** `ic03_fate`
- **Status:** `resolved`
- **Created:** `2026-08-02T16:41:22.859259+00:00`
- **Resolved:** `2026-08-02T16:41:25.814693+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

IC-03's resolve_snapshot_review design is type-shape broken (ReviewOverride has no verdict field) and live evidence suggests #2646 may already close via FR-001 alone. Drop IC-03 and replace with a verify-first task, or keep building a status.py fix regardless?

## Options

- Drop IC-03, verify #2646 closes via FR-001 alone
- Keep building a status.py fix regardless

## Final answer

Drop IC-03's resolve_snapshot_review design. Replace with a verify-first task: confirm #2646 closes via FR-001 alone (zero status.py changes); build a targeted fix only if verification fails.

## Rationale

_(none)_

## Change log

- `2026-08-02T16:41:22.859259+00:00` — opened
- `2026-08-02T16:41:25.814693+00:00` — resolved (final_answer="Drop IC-03's resolve_snapshot_review design. Replace with a verify-first task: confirm #2646 closes via FR-001 alone (zero status.py changes); build a targeted fix only if verification fails.")
