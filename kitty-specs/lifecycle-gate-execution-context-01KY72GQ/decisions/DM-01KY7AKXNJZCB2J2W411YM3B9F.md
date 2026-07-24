# Decision Moment `01KY7AKXNJZCB2J2W411YM3B9F`

- **Mission:** `lifecycle-gate-execution-context-01KY72GQ`
- **Origin flow:** `plan`
- **Slot key:** `plan.architecture.merge-reverify-hook`
- **Input key:** `merge_reverify_hook`
- **Status:** `resolved`
- **Created:** `2026-07-23T11:08:51.250556+00:00`
- **Resolved:** `2026-07-23T11:14:54.208634+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

Where does the merge-phase negative-invariant re-verification hook live?

## Options

- new acceptance/merge_phase seam
- inside merge/executor.py
- Other

## Final answer

New acceptance/merge_phase seam. Keeps invariant logic in the acceptance package with a narrow call-in from merge, and guarantees the merge-phase re-verify WP and the merge-exemption-retirement WP have disjoint owned_files.

## Rationale

_(none)_

## Change log

- `2026-07-23T11:08:51.250556+00:00` — opened
- `2026-07-23T11:14:54.208634+00:00` — resolved (final_answer="New acceptance/merge_phase seam. Keeps invariant logic in the acceptance package with a narrow call-in from merge, and guarantees the merge-phase re-verify WP and the merge-exemption-retirement WP have disjoint owned_files.")
