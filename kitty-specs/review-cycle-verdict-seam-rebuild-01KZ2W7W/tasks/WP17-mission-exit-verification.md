---
work_package_id: WP17
title: Mission-exit verification
dependencies:
- WP02
- WP03
- WP05
- WP13
- WP14
- WP15
- WP16
- WP18
requirement_refs:
- NFR-001
- NFR-004
- C-005
planning_base_branch: pr/review-verdict-write-integrity-01KZ1CGF
merge_target_branch: pr/review-verdict-write-integrity-01KZ1CGF
branch_strategy: Planning artifacts for this mission were generated on pr/review-verdict-write-integrity-01KZ1CGF. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/review-verdict-write-integrity-01KZ1CGF unless the human explicitly redirects the landing branch.
created_at: '2026-08-03T08:13:56Z'
subtasks:
- T074
agent: claude
history:
- at: '2026-08-03T08:13:56Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: reviewer-renata
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_mission_exit_baseline.py
- tests/architectural/mission_exit_baseline.txt
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_mission_exit_baseline.py
- tests/architectural/mission_exit_baseline.txt
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP17 - Mission-exit verification

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load reviewer-renata
```

## Objective

This WP discharges NFR-001 and SC-009 — the mission cannot claim done without
it, and it is, by design, "the surface most tempting to discharge by re-run"
(plan.md's IC-14 Risks note). It is the last WP in the dependency graph and
touches exactly one file: the committed baseline.

**The verification method is a diff against a committed node-id set, never a
re-run judgement.** `research/baseline-8466727eb.md` records, at the
merge-base with `main`, `8466727eb`:

```
2 failed, 2815 passed, 1 skipped, 2 xfailed in 118.77s   (2820 collected)
```

with the two failures attributed by test node id: #3157's date-bomb
(`tests/status/test_work_package_lifecycle.py::test_real_implement_and_review_claims_persist_structured_latest_binding`)
and #3160's frozen-flag drift
(`tests/specify_cli/cli/commands/agent/test_mission_cli_golden_contract.py::test_command_exposes_exact_flag_surface[acceptance-verdict]`).
NFR-001 states this set as a **floor**: it may grow (a genuinely new,
justified pre-existing failure could in principle be added with evidence it
also reproduces at `8466727eb`), but it may never shrink by any of the
prohibited methods NFR-001 enumerates verbatim — re-running, a skip/xfail/
quarantine marker, widening a threshold without a recorded investigation,
deleting an assertion, deleting the test, moving it out of the affected-suites
paths, reducing its parametrization, narrowing an assertion, or excluding it at
collection or marker-selection level.

**A node id disappearing is a violation, not a pass — regardless of why it
disappeared.** If the test moved, was deleted, lost parametrization, had an
assertion narrowed, or was excluded at collection/marker-selection level, that
is an NFR-001 violation to be reported and fixed, not a silently-accepted
improvement.

**A test absent at `8466727eb` can never be classified "retained as
pre-existing."** `tests/regression/test_2646_stale_verdict_closes_via_fr001.py`
is in exactly this category — it was added by the predecessor mission's own
folds, after the merge-base this mission's baseline anchors to. If this test
(or any other test that does not exist at `8466727eb`) is red at mission exit,
it must be fixed outright. Do not, under any framing, attribute its failure to
"pre-existing baseline red" — that classification is only available to the two
rows this baseline document names, both of which reproduce at `8466727eb`
itself, verified.

## Context & Constraints

Read in full before starting:

- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/spec.md` — NFR-001
  verbatim (the prohibited-methods list is load-bearing and must be checked
  item by item, not paraphrased), SC-009, and the Baseline section explaining
  why `8466727eb` (the merge-base with `main`), not the branch tip, is the
  regression anchor.
- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/quickstart.md` — "Before
  anything: the baseline" section's exact invocation; run this WP's
  verification with the identical command, not a paraphrase of it.
- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/research/baseline-8466727eb.md`
  — read its "How to verify NFR-001" section, which states the diff method
  this WP executes. (`tests/architectural/test_mission_exit_baseline.py` and
  `tests/architectural/mission_exit_baseline.txt` are this WP's own
  `create_intent` — they do not exist yet and carry no such section; do not
  look for it there.)
- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/decisions/` — check
  whether any planning decision recorded during WP01-WP16's execution affects
  what counts as in-scope for this baseline (e.g. a decision to add a test to
  the affected-suites list).

**Binding constraint**: this WP depends on WP02, WP03, WP05, WP13, WP14, WP15
and WP16 — the WPs that either fix a coverage/CI prerequisite (WP02, WP05),
clear board hygiene (WP03), or land the mission's substantive behaviour changes
(WP13-WP16). Do not run this WP's verification before all seven have actually
merged into the branch this WP checks out from — a premature run would measure
an incomplete mission and produce a false "clean" or falsely-alarming result.

## Subtask T074 — Diff the affected-suites node-id set against the committed baseline

- **Purpose**: The single subtask that discharges NFR-001/SC-009: run the
  affected-suites invocation, collect the actual failing node-id set, and diff
  it against the committed baseline — never substitute a re-run's exit code for
  the diff itself.
- **Steps**:
  1. Run the exact invocation from `quickstart.md`'s "Before anything: the
     baseline" section (identical to `research/baseline-8466727eb.md`'s own
     "Invocation" section):
     ```bash
     PWHEADLESS=1 uv run pytest \
       tests/review/ tests/status/ \
       tests/regression/test_2646_stale_verdict_closes_via_fr001.py \
       tests/integration/test_review_cycle_rejection_only.py \
       tests/integration/test_ac5_hash_guard.py \
       tests/integration/test_wp_file_hash_stability.py \
       tests/post_merge/test_review_artifact_consistency.py \
       tests/specify_cli/cli/commands/agent/ -q
     ```
  2. Collect the full list of failing node ids from this run (not merely the
     summary counts — `research/baseline-8466727eb.md`'s table is keyed by
     node id, and the diff must be too).
  3. For every failing node id: check whether it appears in the baseline's
     two-row table.
     - **Present, and reproduces identically at `8466727eb`** (already
       verified by the baseline document): retained, no action, note it as
       "still red, pre-existing" in this WP's Activity Log.
     - **Absent from the baseline table**: this is either (a) a genuinely new
       failure introduced by WP01-WP16's work — file it and route it back to
       the owning WP for a fix, this WP does not fix production code itself; or
       (b) a test that did not exist at `8466727eb` (like
       `test_2646_stale_verdict_closes_via_fr001.py`) — per this WP's Objective,
       such a test must be fixed outright and can never be classified
       pre-existing, regardless of how plausible that classification looks.
  4. For every node id present in the baseline table that is **absent** from
     this run's failure list: confirm it is absent because it now **passes**
     (verify by finding it in the passed count, not merely its absence from
     the failure list — a test excluded at collection would also be "absent
     from the failure list" while being an NFR-001 violation). If it is absent
     because it was deleted, moved out of the affected-suites paths, had its
     parametrization reduced, or was excluded at collection/marker-selection
     level, that is an NFR-001 violation — report it explicitly, do not treat
     the numeric failure count dropping as sufficient evidence of a clean
     result.
  5. Cross-check collection count: the baseline recorded 2820 collected tests.
     If this run's collected count differs, investigate why before accepting
     the run as comparable — a lower collected count with the same or fewer
     failures could indicate exactly the excluded-test violation NFR-001
     forbids, disguised as an improvement.
  6. Update `research/baseline-8466727eb.md` with the final measurement: the
     new invocation's result line, the reconciled failure table (still keyed
     by node id, still attributing each to a tracked issue), and an explicit
     attribution paragraph for anything retained versus anything newly fixed —
     matching the existing document's style (its "How to verify NFR-001"
     section should be left intact; add a new dated section below it rather
     than overwriting the original measurement, so the historical record of
     the pre-mission baseline is preserved alongside the final one). This
     update is informational only — `research/baseline-8466727eb.md` sits
     under `kitty-specs/`, which this WP cannot list in `owned_files`, so this
     step is not a gating Definition-of-Done item; the actual deliverables
     this WP is accountable for are `tests/architectural/mission_exit_baseline.txt`
     and `tests/architectural/test_mission_exit_baseline.py` (steps 8-10).
  7. Confirm SC-009's second clause: every failure remaining in the affected
     suites is listed by test node id against an **open tracked issue** — not
     merely "known" informally. If a retained failure has no open issue
     reference, file one and cite it in the updated baseline document.
  8. Extract the full **collected** node-id set from the same invocation
     (`--collect-only -q` over the identical path list) — all ~2820 node ids,
     not only the two known failures — and write it, one node id per line,
     sorted, into `tests/architectural/mission_exit_baseline.txt` (this WP's
     own `create_intent`), committed. This is the actual "floor" NFR-001
     names: the full collected set, not a summary count.
  9. Author `tests/architectural/test_mission_exit_baseline.py` (this WP's
     other `create_intent`): a test that reads
     `mission_exit_baseline.txt`'s committed node-id set and re-collects the
     identical affected-suites invocation via `--collect-only`, asserting
     every node id in the committed file is present in the live collection.
     This makes NFR-001's "the floor may grow, never shrink" **executable
     code**, not merely a documented rule — a node id's disappearance, whether
     from deletion, a move out of the affected-suites paths,
     de-parametrization, or exclusion at collection/marker-selection level,
     fails this test mechanically, without requiring a human diff.
  10. In the same test file, pin the two known baseline failures
      (`test_work_package_lifecycle.py::test_real_implement_and_review_claims_persist_structured_latest_binding`
      for #3157, `test_mission_cli_golden_contract.py::test_command_exposes_exact_flag_surface[acceptance-verdict]`
      for #3160) as two **separately named** entries — a distinct assertion or
      parametrized case per node id, not folded anonymously into the bulk
      ~2820-line floor check — so a reviewer can see, individually, whether
      each one is still red (per this subtask's reconciliation in steps 1-7)
      or now green, without needing to grep the full baseline file.
- **Files**: `tests/architectural/test_mission_exit_baseline.py`,
  `tests/architectural/mission_exit_baseline.txt`
- **Validation checklist**:
  - [ ] The exact `quickstart.md` invocation was run, not a paraphrase or a
        narrower/wider substitute.
  - [ ] Every failing node id in this run is individually reconciled against
        the baseline table (present-and-reproducing, genuinely new, or
        never-existed-at-baseline).
  - [ ] `tests/regression/test_2646_stale_verdict_closes_via_fr001.py` is
        confirmed green, or if red, is fixed outright (never classified
        pre-existing).
  - [ ] Collected-test count is reconciled against the baseline's 2820, with
        any difference explained.
  - [ ] `tests/architectural/mission_exit_baseline.txt` contains the full
        collected node-id set (~2820 entries), committed — not merely the two
        known failures.
  - [ ] `tests/architectural/test_mission_exit_baseline.py` fails when any node
        id in `mission_exit_baseline.txt` is absent from a live
        `--collect-only` of the affected-suites invocation (proven, e.g., by
        temporarily removing one line and confirming red, then reverting).
  - [ ] The two known baseline failures (#3157, #3160) are pinned by node id
        as separately-named entries, distinct from the bulk floor check.
  - [ ] The updated baseline document preserves the original pre-mission
        measurement alongside the final one, and every retained failure cites
        an open tracked issue.
  - [ ] C-005's two pins (`test_issue_2804_*`, `test_issue_3086_*`) are
        confirmed still red — greening either is itself a violation of C-005,
        not a bonus fix.
  - [ ] NFR-004: changed-line coverage on this mission's diff meets or exceeds
        the repository's 90% diff-coverage threshold, measured with the same
        command CI's `diff-coverage` job runs (`.github/workflows/ci-quality.yml`):
        `uv run diff-cover <coverage-xml-reports> --compare-branch=origin/main
        --fail-under=90 --include <critical-paths>` — run it against this
        mission's cumulative diff and record the reported percentage, rather
        than asserting compliance.
- **Edge Cases**: a failure that is flaky (fails on one run, passes on a
  re-run) — NFR-001's method prohibition forbids resolving a failure "by
  re-running," so a flaky failure must be diagnosed and either fixed or
  explicitly filed with its flake rate recorded, not silently accepted because
  a second run happened to go green.

## Branch Strategy

Planning artifacts for this mission were generated on
`pr/review-verdict-write-integrity-01KZ1CGF`. During `/spec-kitty.implement`
this WP may branch from a dependency-specific base (WP02, WP03, WP05, WP13,
WP14, WP15 and WP16 must all be merged into whatever base this WP branches
from), but completed changes must merge back into
`pr/review-verdict-write-integrity-01KZ1CGF` unless the human explicitly
redirects the landing branch.

## Definition of Done

- [ ] The affected-suites invocation ran verbatim per `quickstart.md`, and its
      failing node-id set is fully reconciled against
      `research/baseline-8466727eb.md`.
- [ ] `test_2646_stale_verdict_closes_via_fr001.py` is green, or was fixed
      outright with the fix attributed in the updated baseline.
- [ ] No node id present at the mission's start is missing from the final run
      for any reason other than "now passes."
- [ ] `tests/architectural/mission_exit_baseline.txt` contains the full
      collected node-id set (~2820), committed, and
      `tests/architectural/test_mission_exit_baseline.py` mechanically fails
      when any node id in it is absent from a live `--collect-only` of the
      affected-suites invocation.
- [ ] C-005: the red-first classification was applied to **exactly** the two
      named pin paths (`tests/regression/test_issue_2804_merge_resets_gate_artifacts.py`,
      `tests/regression/test_issue_3086_merge_delete_branch_flattens_coordination_metadata.py`)
      and no others — every other retained failure in this run's reconciliation
      is attributed to reproducing at `8466727eb` (NFR-001's baseline), never to
      C-005's classification. Both named pins are confirmed still red.
- [ ] NFR-004: the diff-coverage command
      (`uv run diff-cover ... --fail-under=90`, matching CI's
      `diff-coverage` job) was run against this mission's cumulative diff and
      its reported percentage is recorded.
- [ ] **NFR-002** — every function this WP touches ends at cyclomatic complexity ≤15: `uv run ruff check --select C901 <touched files>` is clean. Extract helpers rather than leaving a function at 16+.
- [ ] **NFR-003** — `uv run ruff check` and `uv run mypy --strict` are clean on every touched file, with **zero** new `# noqa` / `# type: ignore` suppressions.

## Risks & Mitigations

- **Re-run-as-verification risk**: the single highest risk this WP exists to
  prevent — treating "the suite is green" or "the count dropped" as sufficient
  without reconciling node ids individually. Mitigate by making the
  per-node-id reconciliation table the actual deliverable, not a side note.
- **Silent-exclusion risk**: a test excluded at collection or marker-selection
  level lowers the failure count without fixing anything, and can look
  identical to a genuine fix in a summary line. Mitigate by cross-checking the
  collected-test count against the baseline's 2820 on every run.
- **Misattribution risk**: classifying a test that did not exist at
  `8466727eb` as "pre-existing" would silently launder a new defect into the
  floor. Mitigate by checking each newly-red test's existence at the
  merge-base directly (`git show 8466727eb:<path>` or an equivalent check),
  not by assuming based on how the failure looks.

## Reviewer Guidance

- Confirm the reconciliation is per-node-id, not a summary-count comparison —
  ask to see the actual failing node-id list from the final run, not just
  "2 failed" restated.
- Confirm `test_2646_stale_verdict_closes_via_fr001.py`'s status is addressed
  explicitly — this is the one test this WP's Objective calls out by name as a
  trap.
- Confirm the updated baseline document did not overwrite the original
  pre-mission measurement — both should be readable in the final file.
- Confirm C-005's two pins are still red in the final run — greening them here
  would itself be the violation this constraint exists to catch — and confirm
  no OTHER retained failure was classified "red-first/pre-existing" via
  C-005; that classification is available only for the two named paths.
- Confirm `tests/architectural/mission_exit_baseline.txt` holds the full
  ~2820-entry collected node-id set (not just the two known failures), and
  that `tests/architectural/test_mission_exit_baseline.py` was proven to fail
  when a node id is removed from it, not merely asserted to.
- Confirm NFR-004's diff-coverage command was actually run against this
  mission's cumulative diff and its result recorded — not asserted from
  memory of the individual WPs' own coverage claims.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-08-03T08:13:56Z – system – lane=planned – Prompt created.
- 2026-08-05T00:00:00Z – claude (implementer) – lane=doing – T074 executed.
  Confirmed all seven dependency WPs (WP02, WP03, WP05, WP13, WP14, WP15,
  WP16) plus WP18 were `approved` before running verification. Ran the EXACT
  quickstart.md affected-suites invocation:
  `PWHEADLESS=1 uv run pytest tests/review/ tests/status/
  tests/regression/test_2646_stale_verdict_closes_via_fr001.py
  tests/integration/test_review_cycle_rejection_only.py
  tests/integration/test_ac5_hash_guard.py
  tests/integration/test_wp_file_hash_stability.py
  tests/post_merge/test_review_artifact_consistency.py
  tests/specify_cli/cli/commands/agent/ -q`.
  Result: **2874 passed, 1 skipped, 2 xfailed, 0 failed (2877 collected)** —
  zero failures, versus the pre-mission baseline's 2 failed / 2820 collected
  at `8466727eb`. Both pre-mission failures (#3157, #3160) individually
  re-ran and confirmed PASSING now (fixed by WP02/FR-014 and the
  flag-surface fix respectively) — reconciled as "now passes" (T074 step 4),
  not a shrink. Collected-count growth (2820→2877, +57) reconciled via a
  file-level diff against `8466727eb` restricted to the affected-suite
  paths: zero files removed, four files added, each confirmed absent at
  `8466727eb` via `git show 8466727eb:<path>` (so none is misclassifiable as
  pre-existing); remaining growth is new parametrization/tests inside
  already-existing files. Full detail in
  `research/baseline-8466727eb.md`'s new 2026-08-05 dated section
  (informational; original pre-mission measurement preserved unmodified
  above it).
  Wrote `tests/architectural/mission_exit_baseline.txt` (2877-entry sorted
  node-id set, header-documented) and
  `tests/architectural/test_mission_exit_baseline.py` (8 tests: an
  anti-vacuous canary, a pin-membership check, the live `--collect-only`
  floor-diff guard, three in-memory fault-injection unit tests for the
  shrink-detection function, and a 2-way parametrized pin re-running #3157
  and #3160 individually by name). Proved the shrink guard fires on a
  removed node-id via a scratch COPY (`/home/stijn/.claude/jobs/.../tmp/`,
  never the tracked file): copied the real committed baseline, deleted the
  #3157 line in the copy only, ran the module's real `_load_baseline` +
  `shrunk_node_ids` against the scratch mutant, confirmed the single
  expected violation, then discarded the scratch files (git status
  confirmed the tracked file was never touched). All 8 tests pass against
  the real, unmutated baseline (129.96s). Gates: `ruff check`,
  `ruff check --select C901`, `python -m mypy --strict` all clean on both
  owned files, zero suppressions.
  C-005: both named pins
  (`test_issue_2804_merge_resets_gate_artifacts.py`,
  `test_issue_3086_merge_delete_branch_flattens_coordination_metadata.py`)
  re-confirmed RED at mission exit — not touched, not greened. Per
  `decisions/DM-01KZ75H8P1619ZXJP8VF8MS287.md`, C-005 is separately extended
  by the operator to a third path
  (`tests/integration/test_review_durability_matrix.py`'s SC-004 probe,
  outside the affected-suites list) — re-confirmed load-sensitive (passes
  alone, fails when run with the rest of its file); SC-004 reported UNMET
  per that decision, not silently absorbed.
  Other residuals re-confirmed present and reported, not fixed (all in
  files outside this WP's `owned_files`): T062 VOIDED-by-construction
  (`DM-01KZ77CBY9G8SE9PPJEKCV01KN`); FR-007's 3 unrouted reader sites in
  `workflow.py::review` / `workflow_cores.py::has_prior_rejection` /
  `workflow_executor.py::implement_try_render_fix_mode_prompt`
  (`DM-01KZ77DS4F1PZ92MK6V8ATCJWW`); the two backwards-named tests carried
  from WP16 (`test_reader_polarity_merge_gate_regression.py`'s "_refuses_"
  test whose body is `assert result == []`, and
  `test_review_cycle_rejection_only.py`'s "_writes_no_verdict_artifact"
  test whose body asserts an approved artifact IS written); and the WP07
  fragile fixture test
  (`test_reducer.py::TestEventSourcedReviewResultReader::test_event_sourced_review_result_this_missions_own_meta_json_fixture`)
  re-run in isolation and confirmed currently PASSING (the design fragility
  described for it remains latent, not resolved).
  NFR-004: measured `uv run diff-cover ... --fail-under=90` against
  `origin/pr/review-verdict-write-integrity-01KZ1CGF` (this mission's own
  `merge_target_branch` — chosen over a literal `origin/main`, which would
  fold in the ~55-file predecessor stack per C-006 and thousands of
  unrelated files, not "this mission's cumulative diff"). Enforced
  critical-path result: 97% (46/47 lines; one line uncovered at
  `src/mission_runtime/artifacts.py:443`); a narrower-instrumentation run
  measured 100% (35/35) for the same two files — both recorded honestly,
  both clear the 90% floor. Advisory full-diff (non-blocking): 73%
  (431/588 lines) across all touched `src/specify_cli/*` modules.
  Committed both owned files plus the informational
  `research/baseline-8466727eb.md` addendum. Did not move this WP's lane or
  edit this Activity Log's frontmatter beyond this entry, per the task
  brief's constraint — the reviewer handles lane transition.
- 2026-08-05T00:00:00Z – claude-opus-5 – lane=approved – **WP17 REVIEW —
  APPROVED.** Verified independently in the integrated lane-i worktree (all 8
  dependency lanes merged; commit `5cd0bb671`). **(1) Affected-suites run
  reproduced:** I re-ran the EXACT quickstart invocation myself → **2874
  passed, 1 skipped, 2 xfailed, 0 failed** (93.7s), matching the implementer's
  count exactly. **(2) Baseline reds now genuinely green:** the floor module's
  `test_known_baseline_failure_pin[3157]` and `[3160]` both PASS (each re-runs
  its node-id in a fresh subprocess and asserts returncode 0) — not a re-run
  hand-wave. **(3) Collected-count reconciliation:** my own `--collect-only`
  counted **2877**, matching `mission_exit_baseline.txt` exactly (2820→2877,
  +57); the research-doc addendum's file-level diff shows **zero files removed**
  and 4 added, each confirmed absent at `8466727eb` — no NFR-001 shrink. **(4)
  Floor check is real, not decorative:** `test_mission_exit_baseline.py` = 8
  passed incl. the slow live `test_committed_floor_present_in_live_collection`;
  I independently fault-injected the module's real `shrunk_node_ids` against the
  real committed baseline minus one node-id and confirmed it flags exactly that
  vanish, so a future shrink reds mechanically. **(5) No violation methods
  possible:** WP17's diff touches only its 4 own files — no affected-suite test
  was skipped/xfailed/de-parametrized/collection-excluded. **(6) C-005:** both
  named pins (`test_issue_2804_*`, `test_issue_3086_*`) re-confirmed RED by me
  (2 failed) — correctly not greened. The implementer's flag that
  `DM-01KZ75H8P1619ZXJP8VF8MS287` extends C-005 to a **third** path
  (`test_review_durability_matrix.py`'s SC-004 probe) is correct and supersedes
  this WP's task-file DoD "exactly two paths" wording, which predates that
  operator decision — noted, not a defect. **(7) NFR-004:** critical-path
  diff-coverage 97% (≥90 floor) recorded honestly alongside the 73% advisory
  full-diff. **(8) Gates:** ruff / `--select C901` / `mypy --strict` clean on
  the owned module; zero suppressions. **(9) Residuals honestly reported, not
  fixed/greened:** SC-004 UNMET; T062 VOIDED-by-construction; FR-007's 3
  unrouted reader sites; the two WP16-carried backwards-named tests (unowned,
  compensating guards); and the **WP07 fragile fixture test** — I confirmed it
  reads the mission's OWN live `status.events.jsonl` and asserts slot-absent,
  which is why it fails on a lane that has accumulated lane-transition events
  (I saw it red on lane-h) yet passes here and on the primary partition (its
  designed home, whose status stream carries no WP07 review_result slot). It is
  currently green and honestly flagged as a latent branch-content-dependent
  fragility; correctly NOT edited (WP07 owns it). Mission-exit is durable for
  what ships. **Approving WP17 — this is the final WP; all 18 now approved.**

---

### Updating Lane Status

Use: `spec-kitty agent tasks move-task WP17 --to <lane> --note "message"`

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
