# Known Gap: `spec-kitty` CLI status-tracking defects observed during WP02

**Not a muster or mission-content defect** — this documents a defect in the
`spec-kitty` CLI tooling itself (`MOES-Media/spec-kitty`), encountered while
running this WP's own status-tracking commands. Filed upstream as
[`MOES-Media/spec-kitty#45`](https://github.com/MOES-Media/spec-kitty/issues/45)
and recorded here per the mission's own Evidence Artifact principle — a
defect this significant to how work packages are tracked should not live
only in an issue tracker a future contributor might not think to search.

## What was observed

1. **`spec-kitty agent tasks mark-status`'s first invocation per mission is
   silently dropped while the command still reports
   `{"outcome": "updated"}`.** Reproduced twice on this mission
   (`doctrine-behavioral-suite-01KYW5XK`, WP02, subtask sequence
   T006→T007→T008→...): `T006` (the first call) was lost in both trials;
   `T007`/`T008` (the next two calls in the same sequence) persisted
   correctly in both trials. No error, no warning, no diagnostic
   distinguishing the dropped call's output from a genuinely successful one.

2. **`spec-kitty agent status materialize`'s human-readable `"N events ->
   M WPs"` line presents two differently-populated counts as one arrow —
   confirmed by construction, not an open question.** `event_count` is
   `len(EventStream.transitions)` (`src/specify_cli/status/reducer.py:366`)
   — **lane transitions only**. `wp_count` is
   `len(snapshot.work_packages)`, and `reducer.py:333-341` materialises a
   runtime-only WP entry for an annotation with no prior transition of its
   own. These are different populations: a surface with zero lane
   transitions and at least one annotation for a given `wp_id` prints
   exactly `"0 events -> 1 WPs"`, which reads like an integrity violation
   (a WP existing with zero events) but is actually two counters over
   disjoint event categories displayed side by side.

   Built from this mission's own coord log, varying only which lines are
   present:

   | Surface | transitions | annotations | printed line |
   |---|---|---|---|
   | A. coord log as-is (12 lines) | 2 | 10 | `2 events -> 2 WPs` |
   | B. annotations only, WP01 only | 0 | 6 | `0 events -> 1 WPs` (the original observation) |
   | C. annotations only, both WPs | 0 | 10 | `0 events -> 2 WPs` |
   | D. main-worktree surface | 0 | 0 | `0 events -> 0 WPs` |

   The original `"0 events -> 1 WPs"` observation (row B) and this
   remediation pass's independent re-verification (`event_count: 2`, both
   WPs present, matching row A's shape) are **both correct** — they were
   run against different starting states, not a failed reproduction of the
   same input. Reframed accordingly: not "could not reproduce / open
   question for the maintainer," but a **confirmed defect** — the
   human-readable line should disambiguate the two counts (e.g. "N lane
   transitions across M work packages") rather than presenting them as a
   single before/after arrow, which invites reading `wp_count` as if it
   were bounded by `event_count`.

Both are filed as further instances of the "reports success while silently
dropping/misreporting content" family previously identified in this
programme's other missions
(`MOES-Media/spec-kitty#33`, `#35`, `#36`, `#39`).

## Impact on this WP

None of this mission's own committed work (FR-005/FR-007/C-001/C-002
deliverables) depends on `mark-status`'s auto-commit or `materialize`'s
`event_count` field for correctness — both are status-tracking metadata,
not the behavioral suite's own graded artifacts. The impact is
operational: a mission's very first subtask-completion call can be lost
silently, which is easy to misdiagnose as an agent forgetting to mark a
subtask done rather than a CLI defect, and is worth a future contributor
knowing about before trusting `mark-status`'s own JSON output as proof a
status update actually landed.

## Workaround used in this WP

Every `mark-status`/status-tracking call this WP made was followed by a
`git status` + `git log --oneline` check (per this WP's own Definition of
Done) rather than trusting the command's own reported outcome — the
correct mitigation until the upstream defect is fixed.
