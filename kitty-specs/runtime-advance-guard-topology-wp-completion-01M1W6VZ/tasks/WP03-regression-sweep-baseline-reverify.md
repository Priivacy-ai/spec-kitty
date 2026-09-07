---
work_package_id: WP03
title: Baseline re-verification, tracer close-out
dependencies:
- WP01
requirement_refs:
- NFR-001
- NFR-003
planning_base_branch: fix/runtime-advance-guard-3883
merge_target_branch: fix/runtime-advance-guard-3883
branch_strategy: "single_branch topology (per meta.json): this mission has no coordination branch, no per-WP branches, and no worktrees. All planning and implementation happen directly on fix/runtime-advance-guard-3883, the mission's one and only branch. planning_base_branch and merge_target_branch both name that same branch because there is no separate landing/merge step for this WP -- committed changes land on fix/runtime-advance-guard-3883 directly."
subtasks:
- T014
- T015
- T016
history: []
agent_profile: python-pedro
authoritative_surface: kitty-specs/runtime-advance-guard-topology-wp-completion-01M1W6VZ/
create_intent: []
execution_mode: planning_artifact
model: claude-sonnet-4-6
owned_files:
- kitty-specs/runtime-advance-guard-topology-wp-completion-01M1W6VZ/tracer-approach.md
- kitty-specs/runtime-advance-guard-topology-wp-completion-01M1W6VZ/tracer-design-decisions.md
- kitty-specs/runtime-advance-guard-topology-wp-completion-01M1W6VZ/tracer-tooling-friction.md
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Re-verify NFR-001's exact baseline invocations against WP01's final diff, close out
this mission's three tracer files, and write the PR description's rollout-impact
operator note — the final gate before this mission is presented for review.

## Context

**This mission was narrowed by operator ruling on 2026-09-07** from two issues
(#3883 + #3884) down to #3884 only. See `spec.md`'s "Scope Narrowing" section and
`plan.md`'s "Narrowing" section for the full evidence. **This WP's own scope shrank
as a direct consequence**: the pre-narrowing draft's Subtask T020 (C-002's
byte-exact `guard_failures` regression suite — six named tests plus a fresh
repo-wide grep) is **removed**, because C-002 itself no longer exists in spec.md —
it existed only to protect `gather_artifact_presence`'s `guard_failures`-string
output, a function this mission no longer touches at all (that surface is PR
#3923's). This mission's surviving fix (`_wp_blocks_step`/`_should_advance_wp_step`)
feeds a different, boolean `wp_advance_ready` field, not the `guard_failures` list
of missing-artifact-name strings C-002 protected — there is nothing in this
mission's diff for that regression suite to guard. NFR-001's own general baseline
re-verification (this WP's Subtask T014) already covers this mission's actual blast
radius.

This WP owns no production code and creates no new source or test files — its
`owned_files` are exclusively the three tracer `.md` files already seeded at
planning time (`tracer-approach.md`, `tracer-design-decisions.md`,
`tracer-tooling-friction.md`). It is `execution_mode: planning_artifact` accordingly,
even though most of its actual work is running (not writing) tests.

**Why this WP depends on WP01 and runs last.** Every check here is a post-fix
verification against the completed production diff — the NFR-001 baseline counts
must be re-verified AFTER the fix lands (to confirm zero net-new reds), not before.

**Tracer-file append discipline**: WP02 and WP01 both append small, well-justified
entries to `tracer-design-decisions.md` during their own work (WP02's empirical
finding; any WP01 implementation-time design note) under this repo's ownership-map
leeway norm, even though this WP is the one that formally owns these files in
`wps.yaml`. Do not overwrite or remove their entries, or the 2026-09-07 narrowing
entry already present in all three tracer files — this WP's own edits are
additive, closing entries, same as theirs.

## Subtask T014: NFR-001 baseline re-verification — the exact invocations, cited verbatim

**Purpose**: Confirm zero net-new reds against the EXACT baseline plan.md already
recorded AND against the mission's own freshly-observed pre-change baseline (WP02's
Subtask T005 step 4 entry in `tracer-design-decisions.md`), using the EXACT
invocations — a bare `pytest tests/runtime` gives a different, larger, misleading
number (745/746) than the invocation NFR-001 actually specifies (672/1, via
`--ignore=tests/runtime/next`).

**Steps**:
1. Run, and confirm the count matches exactly:
   ```
   pytest tests/runtime tests/next tests/specify_cli/next tests/specify_cli/status
   ```
   (fast/unit tier) — must report **1666 passed, 1 skipped, 325 deselected**, per
   plan.md's Baseline (NFR-001) section, cited verbatim, not re-derived.
2. Run, and confirm the count matches exactly:
   ```
   pytest tests/runtime/next tests/next
   ```
   (full) — must report **598 passed**.
3. Run, and confirm the count matches exactly, THE EXACT INVOCATION:
   ```
   pytest tests/runtime --ignore=tests/runtime/next
   ```
   — must report **672 passed, 1 skipped** (673 collected). **Do NOT run the naive
   `pytest tests/runtime -q` without `--ignore` and mistake its 746-collected/745-passed
   count for a regression** — that is a different, larger number by design, not a
   defect in WP01's diff.
4. For any count that differs from the stated baseline: classify per the CLAUDE.md
   baseline-red gotcha BEFORE attributing it to this mission — (1) a pre-existing
   known-P0 red (#2736, #2772, #1834), confirmed by running the same test against
   `main`/`upstream/main` at the same commit; (2) a CI-environment failure; (3) a
   stale-install false red; (4) a stale-venv false red (re-run `uv sync --frozen
   --all-extras` and retry before concluding regression). Only a count that is red
   on this branch AND green on `main` at the same commit is this mission's to fix.
5. If, after classification, a genuine net-new red remains, do NOT green-wash it
   (Standing Order #9) — report it explicitly rather than silently working around
   it; this is a BLOCKED condition for this WP, not something to paper over to
   reach a clean report.
6. **Diff against WP02's own freshly-captured "before" baseline, not only against
   plan.md's static citation.** Read WP02's Subtask T005 step 4 entry in
   `tracer-design-decisions.md` — the mission's own "before" counts for these same
   three exact invocations, observed immediately before WP01's first
   production-code commit. Compare those recorded "before" counts against the
   "after" counts you just observed in steps 1-3 above. In the normal case the two
   should agree exactly; if they do NOT agree, classify the discrepancy per this
   subtask's own Step 4 baseline-red gotcha classification and record which of the
   two baselines (plan.md's citation, or WP02's live "before" entry) the observed
   deviation is measured against. Record the comparison outcome (agreement, or a
   classified discrepancy) as part of this subtask's `tracer-design-decisions.md`
   append.

**Files**: `tracer-design-decisions.md` (append the three exact invocations and
their resulting counts, plus the diff-against-WP02's-baseline outcome from step 6).

**Validation**: All three counts match NFR-001/SC-005 exactly, or every deviation is
classified and either resolved as non-attributable or reported as a genuine,
unresolved regression; the "after" counts have also been diffed against WP02's
T005-step-4 "before" entry per step 6, with the outcome recorded.

## Subtask T015: Final tracer-file updates

**Purpose**: Close out this mission's tracer trail per Standing Order #3 — append,
do not replace.

**Steps**:
1. In `tracer-approach.md`: append a closing entry noting the ACTUAL sequencing this
   mission followed post-narrowing (WP02 -> WP01 -> WP03), contrasting it with the
   file's own pre-existing seed content (which described a pre-narrowing, two-issue
   4-WP shape) — do not delete the seed content or the 2026-09-07 narrowing entry
   already appended there; add a dated note pointing to `wps.yaml`/this mission's
   tasks-phase decision for the full rationale.
2. In `tracer-design-decisions.md`: confirm WP02's empirical-spike entry, WP02's
   NFR-001 pre-change baseline entry (Subtask T005 step 4), and any WP01
   implementation-time notes are present and legible; append a closing summary of
   what those findings turned out to mean for the shipped fix (e.g., whether the
   `mission_slug` fallback held, and whether T014 step 6's diff against WP02's
   captured "before" baseline agreed with plan.md's cited baseline or surfaced a
   classified discrepancy).
3. In `tracer-tooling-friction.md`: append any NEW friction encountered during
   WP01/WP02/WP03's actual implementation (distinct from the plan-phase friction
   and the 2026-09-07 narrowing friction already recorded there) — e.g. any
   line-number drift between plan.md's citations and the as-implemented diff, any
   test-venv lock contention observed (NFR-003), or anything else future missions
   on this seam should know. If nothing new arose, record that explicitly rather
   than leaving the file looking incomplete.

**Files**: all three tracer files (append only).

**Validation**: All three files retain their original seed content and the
2026-09-07 narrowing entries, plus new, dated, legible closing entries.

## Subtask T016: PR description's rollout-impact operator note

**Purpose**: Per plan.md's "Reflexivity — rollout impact" section: this is an
operational note for the PR description and merge hand-off, not a new code
requirement — record it now so the implement/review phase does not have to
re-derive it. Also record the PR body's scope statement plainly, since this
mission's scope changed mid-flight.

**Steps**:
1. Draft the operator note (for inclusion in the eventual PR body, not as a new FR
   or code change): shipping this fix will newly (and correctly) block a mission
   whose WP was never claimed (#3884) and was previously sliding through
   `implement` unblocked — including, now that FR-009 ships alongside FR-004, a
   real COORD-topology mission in that state, not only a SINGLE_BRANCH/LANES one.
   Recommend that whoever merges this spot-checks currently-in-`implement`
   coord-topology missions immediately after merge, so an operator is not
   surprised by a mission newly blocking on its next `next` call with no
   user-visible change of their own.
2. Record this draft note in `tracer-approach.md` (append, tagged clearly as "PR
   description operator note — copy into the PR body at review time") so it is not
   lost between the tasks phase and the eventual PR write-up.
3. State explicitly (matching plan.md's own framing) that no mission-tracking code
   change is proposed for this note — it is a call-out about a real operational
   discontinuity, not an internal test-suite delta.
4. **State the PR body's scope line explicitly, since it changed from the mission's
   original two-issue premise**: the PR description must say `Closes #3884` only —
   **not** `Closes #3883`. #3883 is out of scope for this mission (draft PR #3923
   fixes it independently); a handover comment recording that has already been
   posted on #3883. Record this scope line alongside the rollout-impact note in
   `tracer-approach.md` so the implement/review phase does not accidentally close
   #3883 by habit from the mission's original two-issue framing.

**Files**: `tracer-approach.md` (append).

**Validation**: The operator note and the `Closes #3884`-only scope line are both
present, dated, and clearly marked for reuse in the PR body.

## Definition of Done

- All three NFR-001 exact invocations (fast/unit tier; `tests/runtime/next
  tests/next` full; `pytest tests/runtime --ignore=tests/runtime/next`) match their
  stated baseline counts exactly, or every deviation is classified per the
  baseline-red gotcha and, if genuinely attributable, reported rather than silently
  resolved; the observed "after" counts have also been diffed against WP02's
  Subtask T005 step 4 "before" entry in `tracer-design-decisions.md`, with the
  comparison outcome recorded (T014).
- **Baseline-red discipline, applied at this WP's own scale**: this WP is the
  mission's authoritative baseline-reconciliation point — every count produced here
  that does not match NFR-001 must be run against `main`/`upstream/main` at the
  same commit before being classified, and a genuine net-new red must be reported
  as BLOCKED, never quietly folded into a "tests pass" summary (Standing Order #9,
  red-main-release-discipline).
- All three tracer files carry dated closing entries appended (not replacing) their
  pre-existing content, including the 2026-09-07 narrowing entries (T015).
- The PR description's rollout-impact operator note AND its `Closes #3884`-only
  scope line are both drafted and recorded for reuse at review time (T016).
- `spec-kitty agent tasks mark-status T00N --status done` recorded for each of
  T014–T016.

## Risks

- **This WP is the mission's last gate before review — do not rush it.** A
  clean-looking summary that has not actually re-run the exact NFR-001 invocations
  is not evidence of anything; run the exact commands, not an approximation.
- **Test-venv lock contention (#3283, NFR-003)** may cause a spurious timeout under
  concurrent test execution — classify per the baseline-red gotcha as
  environmental, do not fold into this WP's own pass/fail accounting.
- **Habit risk**: this mission's original two-issue framing (#3883+#3884) is still
  visible in the seed tracer content and in `reviews/*.yaml`'s review history —
  do not let that make it into the PR body as `Closes #3883, #3884`. The PR body
  carries `Closes #3884` only.

## Reviewer Guidance

- Confirm the exact NFR-001 invocations were actually run (check the recorded
  commands in `tracer-design-decisions.md`, not just a summary claim) and that the
  counts genuinely match, or that any deviation is properly classified and
  reported.
- Confirm T014 step 6's diff against WP02's Subtask T005 step 4 "before" entry was
  actually performed and its outcome is recorded in `tracer-design-decisions.md`.
- Confirm all three tracer files retain their original seed content and the
  2026-09-07 narrowing entries — verify nothing was deleted or overwritten, only
  appended.
- Confirm the rollout-impact operator note AND the `Closes #3884`-only scope line
  are present and will actually make it into the PR body at review time.

**Implementation command**: `spec-kitty agent action implement WP03 --agent claude`
