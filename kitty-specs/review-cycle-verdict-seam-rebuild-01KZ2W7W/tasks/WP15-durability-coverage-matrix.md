---
work_package_id: WP15
title: Durability coverage matrix
dependencies:
- WP05
- WP10
- WP11
- WP12
requirement_refs:
- FR-015
planning_base_branch: pr/review-verdict-write-integrity-01KZ1CGF
merge_target_branch: pr/review-verdict-write-integrity-01KZ1CGF
branch_strategy: Planning artifacts for this mission were generated on pr/review-verdict-write-integrity-01KZ1CGF. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/review-verdict-write-integrity-01KZ1CGF unless the human explicitly redirects the landing branch.
created_at: '2026-08-03T08:13:56Z'
subtasks:
- T067
- T068
- T069
agent: claude
history:
- at: '2026-08-03T08:13:56Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/integration/
create_intent:
- tests/integration/test_review_durability_matrix.py
execution_mode: code_change
model: ''
owned_files:
- tests/integration/test_review_durability_matrix.py
- tests/specify_cli/cli/commands/agent/test_tasks_ports.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP15 - Durability coverage matrix

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

FR-015 requires the durable-persistence path to be exercised through the **real**
command surface, across the full matrix of verdict × target lane × topology ×
auto-commit setting, such that deleting the commit call turns every cell red.
SC-011/User Story 1 Acceptance Scenario 9 states the same requirement from the
success-criteria side.

**The claim that motivated this WP is false as stated, and the correction matters
for scope.** An earlier planning pass asserted "every existing CLI test passes
`--no-auto-commit`" — implying the commit branch (`auto_commit=True`) has never
run at all. That is not true:
`tests/specify_cli/cli/commands/agent/test_move_task_approval_body_collision.py:139`
already calls `_do_move_task(..., auto_commit=True, ...)`. The commit branch *is*
exercised today. The true, narrower gap is this: **no existing test exercises
that branch through the real router and real git** — every test that sets
`auto_commit=True` today does so against `FakeCoordCommitRouter`, an in-memory
double that records a call was made and returns a canned `CommitArtifactResult`
without ever invoking `git`. A regression that deletes the actual `commit_artifact`
call inside the production code path would still pass every one of those tests,
because the fake's `artifact_calls` list is populated by test setup expectations,
not by observing real git state.

**If left unstated, the false "everything only tests `--no-auto-commit`" framing
licenses discharging this WP with another fake-router test** — which would satisfy
the letter of "add a durability test" while adding zero real coverage. This WP
exists specifically to close that gap: at least one cell of the matrix must run
against the real `CoordCommitRouter` implementation and a real, initialized git
repository, so that deleting the production commit call is provably observable.

`FakeCoordCommitRouter.artifact_result` (`tests/specify_cli/cli/commands/agent/test_tasks_ports.py:118`)
is **already** a configurable constructor field:

```python
artifact_result: CommitArtifactResult = CommitArtifactResult(
    status="committed", placement_ref="primary", commit_hash="0" * 40
)
```

Making the fake return a different `status` (e.g. `"no_op_wrong_surface"` or
`"error"`) per test case is zero lines of new production or fixture code — it is
passing a different value to an existing field. Do not present that as a
deliverable; it already exists. The actual work is building the matrix and the
real-router/real-git leg.

## Context & Constraints

Read in full before starting:

- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/spec.md` — User Story 1
  Acceptance Scenario 9 (FR-015), FR-013 (the `--no-auto-commit` `--json` key,
  delivered by WP11 — this WP only needs to *cover* it in the matrix, not
  implement it).
- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/plan.md` — IC-11's Risks
  paragraph, source of the false-claim correction above.
- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/quickstart.md` — no
  direct section for this WP, but its "Before anything: the baseline" invocation
  is the affected-suites list this WP's new file must not regress.
- `tests/specify_cli/cli/commands/agent/test_tasks_ports.py` — read
  `FakeCoordCommitRouter` in full (it is the DI double every existing CLI test
  uses) before writing any fixture; do not build a second fake with a different
  shape.
- `tests/specify_cli/cli/commands/agent/test_move_task_approval_body_collision.py:139`
  — the existing `auto_commit=True` call site, to confirm what it does and does
  not cover before claiming this WP closes a gap it already closes.

**Binding constraint**: the matrix dimensions are **verdict × target lane ×
topology × auto-commit**, exactly as named in FR-015 — not a subset chosen for
convenience. Verdict: `approved` / `rejected` / arbiter override (WP12's
`ReviewOverride` path). Target lane: at minimum `approved`, `done`, and the
rejection-only `planned` rollback path. Topology: `SINGLE_BRANCH` and a
coordination topology (`LANES` or the coord fixture WP04/WP07 already exercise
elsewhere) — the write side's `REVIEW_CYCLE` kind routing (WP04) means topology is
not incidental here, it changes which surface the commit lands on. Auto-commit:
`True` and `False` (`--no-auto-commit`).

## Subtask T067 — Exercise the durability matrix through the real command surface

- **Purpose**: Build the parametrized matrix itself, calling the actual
  `move-task` command path (not a hand-assembled call to an internal helper),
  so the coverage is representative of what an operator actually runs.
- **Steps**:
  1. Create `tests/integration/test_review_durability_matrix.py`. Structure it as
     a single parametrized test (or a small family sharing one fixture) over the
     four dimensions named above, using `pytest.mark.parametrize` with explicit
     ids so a failing cell names itself clearly in CI output (e.g.
     `approved-done-single_branch-auto_commit`).
  2. For each cell, drive the real CLI entry point
     (`spec_kitty_cli.cli.commands.agent.tasks_move_task._do_move_task`, the same
     function `test_move_task_approval_body_collision.py` calls) with the
     dimension's parameters, using `FakeCoordCommitRouter` for the cells that
     are not the real-router leg (T069 covers that leg separately) and the
     `TasksPorts` DI bundle the existing test suite already establishes as the
     house pattern (per plan.md's Technical Context: "Fault injection uses the
     existing `TasksPorts` DI bundle").
  3. For the auto-commit dimension, assert the FR-013 `--json` key (delivered by
     WP11) is present and correctly valued for `auto_commit=False` cells, and
     absent or falsy for `auto_commit=True` cells that actually committed.
  4. For the topology dimension, use whatever coord-topology fixture WP04/WP07's
     tests already established (grep `tests/` for the existing coord-topology
     conftest fixture before building a new one — likely
     `coord_topology_mission` per `tests/integration/test_two_partition_preview.py`)
     rather than hand-rolling a second coord fixture.
  5. For the verdict dimension's arbiter-override cell, drive it through
     whatever override-creation path WP12 establishes (`--skip-review-artifact-check`
     with `--note`, or the direct `create_arbiter_decision`/`persist_arbiter_decision`
     call WP12's tests already use) rather than reconstructing override state by
     hand.
- **Files**: `tests/integration/test_review_durability_matrix.py`
- **Validation checklist**:
  - [ ] Every cell in the four-dimension matrix has at least one test id, and
        the total count matches the product of the dimension sizes (document
        the count in the module docstring so a future dimension addition is
        visible as a count change).
  - [ ] Each cell's assertion is specific to that cell (not one shared
        assertion that happens to pass for the wrong reason across cells).
  - [ ] The FR-013 `--json` key is asserted for every `auto_commit=False` cell.
- **Edge Cases**: a rejection cell under `--no-auto-commit` followed immediately
  by an approval attempt on the same WP — confirm the uncommitted rejection is
  still visible to the approval path's "latest verdict" check (this exercises
  the interaction between FR-013's sanctioned non-durable state and the
  ordinary reject→approve flow WP01's reference WP already covers elsewhere;
  do not re-derive that logic here, only confirm the matrix cell reflects it).

## Subtask T068 — Prove each cell reds when the commit call is deleted, via a committed automated mutation test

- **Purpose**: A durability matrix that would still pass if the production
  commit call were deleted proves nothing. FR-015's own acceptance criterion is
  "removing the commit call turns each cell red" — this subtask is the mutation
  check that makes that claim auditable rather than asserted. **The automated
  form is required, not optional.** An Activity-Log narrative describing a
  manual, reverted removal is evidence of a one-time exercise; it proves
  nothing about the NEXT regression that deletes the commit call, because
  nothing in the committed diff re-checks it. A committed meta-test is the
  only form that keeps this guarantee alive after this WP merges.
- **Steps**:
  1. Identify the exact production call site(s) that perform the durable commit
     for a review-cycle verdict — by this point in the mission (after WP06's
     extraction, WP10's atomicity work, WP11's ordering work), this should be a
     small, named set of calls inside `src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py`
     and/or `review/cycle.py`'s `_commit_review_cycle_artifact`. Do not guess —
     read WP06/WP10/WP11's final diffs to confirm the current call site(s)
     before proceeding.
  2. Add a committed meta-test, `test_matrix_is_sensitive_to_commit_removal`,
     to `tests/integration/test_review_durability_matrix.py`: monkeypatch
     `commit_artifact` (on the real `CoordCommitRouter`/`FakeCoordCommitRouter`,
     whichever the cell under test wires through `TasksPorts`) to a no-op that
     returns `CommitArtifactResult(status="unchanged", ...)` without
     performing any commit, then re-run every `auto_commit=True` cell from
     T067's matrix against that monkeypatched router and assert **each one
     fails**. This is the mutation proof as executable code, not a manual
     exercise — it runs on every future CI invocation of this file, not once
     at review time.
  3. If any `auto_commit=True` cell does **not** fail under the monkeypatched
     no-op, that cell's assertion is insufficiently specific — strengthen it
     (e.g. assert on git state directly for the real-router leg, or assert the
     fake's call log entry's `status` field matches what a real commit would
     have produced, not merely that a call was made) until it does fail under
     `test_matrix_is_sensitive_to_commit_removal`.
  4. Additionally perform the one-time manual verification (temporarily
     commenting out the production commit call, re-running T067's matrix,
     recording which cells failed) as a cross-check that the monkeypatch-based
     meta-test's result agrees with an actual code-level removal — record this
     cross-check in the Activity Log, then revert the temporary change. This
     manual pass is corroborating evidence for the committed meta-test, not a
     substitute for it.
- **Files**: `tests/integration/test_review_durability_matrix.py`
- **Validation checklist**:
  - [ ] `test_matrix_is_sensitive_to_commit_removal` exists, is committed, and
        monkeypatches `commit_artifact` to a no-op returning
        `status="unchanged"`.
  - [ ] Every `auto_commit=True` cell fails under that monkeypatch, proven by
        actually running the meta-test (not asserted).
  - [ ] The one-time manual cross-check (temporary code-level removal) is
        recorded in the Activity Log and its result agrees with the committed
        meta-test's result; no production code changes remain from that
        manual exercise.
- **Edge Cases**: a cell whose assertion is on the `--json` output only (e.g.
  the `--no-auto-commit` cells) — confirm the monkeypatch does not accidentally
  make an unrelated `auto_commit=False` cell's assertion fail too, which would
  indicate the test is not isolating the dimension it claims to.

## Subtask T069 — Cover the real-router, real-git path — including the `SIGKILL` cell

- **Purpose**: Close the actual gap IC-11's risk note identifies — at least one
  matrix cell must run against the real `CoordCommitRouter` and a real,
  initialized git repository, not `FakeCoordCommitRouter`. **This subtask also
  owns the subprocess+`SIGKILL` cell SC-003 names explicitly.** WP10's own
  crash-orphan reproduction (T044) is licensed to substitute a
  directly-asserted state simulation when a true subprocess+signal harness is
  "disproportionate for this test's fixture budget" — that substitution is
  correct for WP10's unit-level scope, but it cannot demonstrate SC-003's
  named `SIGKILL` case end-to-end. This WP owns real-git integration
  specifically so that gap does not go uncovered by any WP.
- **Steps**:
  1. Identify the real `CoordCommitRouter` implementation (the port
     `FakeCoordCommitRouter` in `test_tasks_ports.py` stands in for) and confirm
     what it needs to construct against a real repo — likely a real
     `main_repo_root` pointing at a git-initialized `tmp_path` fixture, mirroring
     the pattern `tests/coordination/test_analysis_report_rehome.py` uses for
     asserting commit state after a review-cycle write (cited in the predecessor
     WP01's own Notes as the house idiom for git-state assertions).
  2. Write at least one test in `tests/integration/test_review_durability_matrix.py`
     that constructs a real git repository fixture (matching the #2990
     stray-`.git` hazard guidance already established elsewhere in this
     mission — WP10's Notes on "review fixtures need a real initialized repo" —
     do not build this fixture on a bare `tmp_path` root without initializing
     git first), drives `_do_move_task` with the real router wired through
     `TasksPorts`, and asserts real git state afterward: `git log` shows a
     commit containing the review-cycle artifact path, `git status --porcelain`
     shows no untracked/modified marker for it immediately after.
  3. Confirm this real-router test is included in T068's mutation check — it is
     the cell most likely to actually catch a deleted commit call, since a fake
     can be configured to report success regardless of whether a call happened,
     but real git state cannot lie about whether a commit exists.
  4. **Add the subprocess+`SIGKILL` cell**: a test that spawns
     `create_rejected_review_cycle`/the real `move-task` writer path in a
     child process against a real, git-initialized repo, signals readiness
     after the write lands but before the commit completes (matching WP10's
     T044 instrumentation approach — a file/pipe readiness signal, not a
     timing guess), sends `SIGKILL` (or the platform equivalent) to the child
     at that point, then invokes the identical command again from the parent
     process and asserts it exits zero **and** records the correct verdict —
     the literal SC-003 acceptance criterion, exercised through the real
     command surface and real git, not a directly-asserted state simulation.
  5. If `feature_status_lock`'s real-lock behavior (WP10's new test seam — a
     real lock spawning `git rev-parse` in what were previously unit tests with
     `_null_lock` patches) interacts with this fixture, confirm this test either
     uses the new seam correctly or explicitly documents why it does not need
     to.
- **Files**: `tests/integration/test_review_durability_matrix.py`,
  `tests/specify_cli/cli/commands/agent/test_tasks_ports.py` (only if a shared
  fixture helper needs to move there for reuse — do not duplicate
  `FakeCoordCommitRouter`'s shape, extend it if a new configuration is needed)
- **Validation checklist**:
  - [ ] At least one test uses the real `CoordCommitRouter` against a real,
        git-initialized repository — not `FakeCoordCommitRouter`.
  - [ ] That test asserts on actual `git log`/`git status` output, not on a
        fake's call-log list.
  - [ ] A dedicated subprocess+`SIGKILL` test exists, kills the writer between
        write and commit against a real repo, and asserts the identical retry
        both exits zero and records the correct verdict.
  - [ ] T068's mutation check confirms the real-router test (and, where
        feasible, the `SIGKILL` cell) fails when the production commit call is
        removed.
- **Edge Cases**: a CI environment without a real `git` binary available (should
  not occur, but confirm the test skips gracefully with a clear reason rather
  than failing opaquely if it does); a repo fixture where `git config user.*`
  is unset (commits may fail without author identity — set it in the fixture
  setup, matching whatever existing real-git test fixtures in this repo already
  do); a platform without `SIGKILL` (Windows) — confirm the test uses the
  documented platform equivalent or skips with a clear reason rather than
  failing opaquely.

## Branch Strategy

Planning artifacts for this mission were generated on
`pr/review-verdict-write-integrity-01KZ1CGF`. During `/spec-kitty.implement` this
WP may branch from a dependency-specific base (WP05, WP10, WP11 and WP12 must be
merged into whatever base this WP branches from), but completed changes must
merge back into `pr/review-verdict-write-integrity-01KZ1CGF` unless the human
explicitly redirects the landing branch.

## Definition of Done

- [ ] T067: the matrix exists, covers verdict × target lane × topology ×
      auto-commit, and every cell's assertion is specific to that cell.
- [ ] T068: a committed `test_matrix_is_sensitive_to_commit_removal` meta-test
      exists, monkeypatches `commit_artifact` to a no-op returning
      `status="unchanged"`, and asserts every `auto_commit=True` cell fails
      under it; a corroborating manual code-level removal is recorded in the
      Activity Log and agrees with the meta-test, with no permanent code
      removal remaining.
- [ ] T069: at least one cell runs the real `CoordCommitRouter` against a real
      git repository and asserts real git state, and that cell is confirmed
      sensitive to the commit call's removal. A dedicated subprocess+`SIGKILL`
      cell exists against a real repo, demonstrating SC-003's named case
      end-to-end (a substitute state-simulation, as WP10's T044 uses at unit
      scope, does not discharge this bullet).
- [ ] `FakeCoordCommitRouter`'s existing `artifact_result` field is reused for
      varying fake-router outcomes, not duplicated.
- [ ] `ruff` and `mypy --strict` clean on every touched file, zero new
      suppressions (NFR-003).
- [ ] `PWHEADLESS=1 uv run pytest tests/integration/test_review_durability_matrix.py -v`
      passes in full, and the affected-suites regression run
      (`tests/review/ tests/status/ tests/post_merge/
      tests/specify_cli/cli/commands/agent/`) shows no new failures beyond
      `research/baseline-8466727eb.md`'s two rows (NFR-001).
- [ ] **NFR-002** — every function this WP touches ends at cyclomatic complexity ≤15: `uv run ruff check --select C901 <touched files>` is clean. Extract helpers rather than leaving a function at 16+.

## Risks & Mitigations

- **Fake-router discharge risk**: the single biggest risk this WP exists to
  prevent is discharging FR-015 with only fake-router cells. Mitigate by
  treating T069's real-git cell as non-negotiable, not an optional enhancement.
- **Assertion-specificity risk**: a matrix cell whose assertion only checks
  "no exception was raised" or "the fake's call log has one entry" would pass
  even with the production commit call deleted. Mitigate via T068's explicit
  mutation exercise on every cell class, not only the real-git one.
- **Fixture duplication risk**: building a second coord-topology fixture or a
  second real-git fixture when one already exists elsewhere in the test suite
  fragments house patterns. Mitigate by grepping `tests/integration/` and
  `tests/coordination/` for existing fixtures before writing new ones.
- **Real-git flakiness risk**: real subprocess-backed git tests are slower and
  can be more environment-sensitive than fake-router tests. Mitigate by
  keeping the real-git leg to the minimum cell count that proves the gap is
  closed (one or two cells, plus the dedicated `SIGKILL` cell), not the full
  matrix duplicated against real git.
- **Manual-only mutation-proof risk**: an Activity-Log narrative describing a
  temporary, reverted removal proves the matrix was sensitive once, not that
  it stays sensitive after this WP merges. Mitigate by treating the committed
  `test_matrix_is_sensitive_to_commit_removal` meta-test as the acceptance
  evidence, and the manual removal as a one-time corroborating cross-check
  only.
- **Substitute-SIGKILL risk**: WP10's unit-level crash-orphan reproduction is
  licensed to substitute a state simulation for a true subprocess+signal
  harness; that licence does not transfer to this WP. Mitigate by treating
  T069's subprocess+`SIGKILL` cell as non-negotiable, matching SC-003's named
  case literally.

## Reviewer Guidance

- Confirm `test_matrix_is_sensitive_to_commit_removal` exists as a committed
  test (not only an Activity-Log narrative), monkeypatches `commit_artifact`
  to a no-op, and actually fails every `auto_commit=True` cell when run.
- Confirm at least one test genuinely constructs a real git repository and
  asserts on `git log`/`git status` output — not on `FakeCoordCommitRouter`'s
  in-memory call log dressed up to look real.
- Confirm a dedicated subprocess+`SIGKILL` test exists against a real
  git-initialized repo and asserts the identical retry both exits zero and
  records the correct verdict — not a directly-asserted state simulation.
- Confirm the Activity Log contains T068's corroborating manual-removal
  evidence, naming which cells failed and which did not when the commit call
  was temporarily removed — and confirm no trace of that removal remains in
  the final diff.
- Confirm the matrix's cell count matches the stated product of dimension
  sizes in the module docstring — a matrix silently missing a dimension
  combination discharges FR-015's letter, not its substance.
- Confirm `FakeCoordCommitRouter.artifact_result` was reused, not duplicated
  into a second constructor field or a second fake class.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-08-03T08:13:56Z – system – lane=planned – Prompt created.

- 2026-08-04T00:00:00Z – claude – lane=in_progress – Built the 12-cell durability
  matrix (`tests/integration/test_review_durability_matrix.py`: T067), the
  committed automated mutation proof (T068), the arbiter-override sub-matrix
  (event-sourced durability, separate from `commit_artifact`), the real-router/
  real-git leg + dedicated SIGKILL cell, and the real 50-iteration/2-process
  SC-004 harness (T069). Quality gates (`ruff`, `ruff --select C901`,
  `mypy --strict`) clean on both touched files; `test_tasks_ports.py` was NOT
  edited (no new fake-router configuration was needed — `FakeCoordCommitRouter`'s
  existing `artifact_result`/instance-level `commit_artifact` override sufficed).
- 2026-08-04T00:00:00Z – claude – lane=in_progress – **T068 step 4 manual
  cross-check** (one-time, corroborating the committed meta-test, never merged):
  copied the worktree to a scratch dir (`/home/stijn/.claude/jobs/c55ec787/tmp/
  wp15-probe/`, per the "never mutate a tracked file to observe a red" rule),
  and in that COPY ONLY, deleted the production commit call inside
  `review/cycle.py::_commit_review_cycle_artifact` (replaced the
  `commit_router.commit_artifact(...)` invocation with an unconditional early
  `return`, so the writer reports success without ever calling the port).
  Re-ran the matrix against the mutated copy via
  `PYTHONPATH=<scratch>/src <real venv python> -m pytest
  tests/integration/test_review_durability_matrix.py -k "durability_matrix_cell
  or sensitive_to_commit_removal or never_invoke_commit_artifact"`.
  Result: exactly the 3 durable cells (`{rejected_planned,approved_approved,
  approved_done}-single_branch-auto_commit`) went red in BOTH
  `test_durability_matrix_cell` (via `assert len(router.artifact_calls) == 1`,
  which failed with `got []` — the call-site deletion is what this assertion
  catches) AND `test_matrix_is_sensitive_to_commit_removal` (via
  `DID NOT RAISE typer.Exit` — the dedicated meta-test's own router-level
  patch became moot once the call site itself never reached the port, which is
  the expected, coherent interaction of the two independent mutation shapes).
  The other 9 base cells and 9 insulation cells were unaffected, exactly as
  documented (they never call `commit_artifact` regardless of this mutation).
  **Caveat surfaced by this exercise, recorded honestly**: with the call site
  deleted this way, `_mt_output`'s `verdict_durably_persisted` JSON key still
  reported `true` (it reflects config intent -- `auto_commit and not
  skip_target_branch_commit` -- computed before the commit attempt, not a
  post-hoc verification that a commit actually landed) -- so a consumer relying
  on that key ALONE would not detect this specific mutation shape; the
  `router.artifact_calls`/git-state assertions are what actually catch it. This
  is reported as a finding, not fixed (test-only WP; the signal's own
  computation timing is production code, out of scope). Scratch copy deleted
  immediately after the run; `git status` on the real worktree confirmed only
  the new test file is present -- no tracked file was touched.
- 2026-08-04T00:00:00Z – claude – lane=in_progress – **SC-004 finding**: the
  real 2-process/50-iteration harness (`test_sc004_two_concurrent_processes_
  never_clobber_a_verdict_over_50_iterations`) demonstrates SC-004 is NOT met:
  a genuine commit-phase race (outside `feature_status_lock`, per NFR-006)
  intermittently loses/leaves-uncommitted a review-cycle record under real
  OS-process concurrency. No production fix attempted (test-only WP mandate).
  Test committed unweakened, not `xfail`/`skip`ped, per "never retry-to-green"
  — it may show red under any invocation shape, which is the honest signal
  spec.md's own SC-004 row anticipates ("Asserted to lose one record today;
  the probe is owed before the fix"). **Correction (post adversarial review)**:
  an earlier version of this entry characterized the race as "passes 5/5
  alone, fails 4/4 preceded by another test" — an independent re-run
  contradicted both halves (1/7 red alone; 2/2 green when preceded by 31 tests
  serially; red under `-n auto`). The honest characterization is a
  **load-window race**: reds under parallel contention, occasionally reds
  alone, with no reliable "run it alone and it passes" heuristic. Both the
  module docstring and this test's own docstring have been corrected to match
  — the probe, its 50-iteration/2-process shape, and its UNMET verdict are
  unchanged; only the characterization of when it reproduces was wrong and is
  now fixed.
- 2026-08-04T00:00:00Z – claude – lane=in_progress – **Adversarial-review
  finding, addressed**: the reviewer found the `"topology"` axis in the
  12-cell matrix is a directly-patched `_skip_target_branch_commit` boolean —
  every one of those 12 cells runs against a plain single-branch repo, so
  FR-015's topology dimension (load-bearing per WP04's `REVIEW_CYCLE` routing:
  topology changes which git REF a commit lands on) had zero genuine coverage.
  Added a real coord-topology section (T069c) built on the canonical
  `tests/integration/coord_topology_fixture.py` (`_build_coord_topology`) — no
  second coord fixture hand-rolled:
  `test_real_coord_topology_review_cycle_commits_to_coord_ref_not_primary`
  (asserts `git show <coord-ref>:<path>` succeeds, `git show main:<path>`
  fails), `test_real_coord_topology_cell_reds_when_commit_artifact_is_
  neutered` (same commit-removal mutation sensitivity as the single_branch
  cells, proven via real-git assertions), and `test_real_coord_topology_
  revert_deletes_and_commits_on_coord_ref` — the WP13 durability-matrix
  witness (DM-01KZ75GBNXC73Q38M43GBH38W7): drives a transition-emit failure
  after a coord-topology write already landed, and confirms
  `revert_committed_verdict_write` deletes-and-commits the deletion on the
  COORD ref (via `_resolve_revert_commit_worktree` + `kind=REVIEW_CYCLE`),
  not primary — the exact live bug WP13 fixed (WP11's own tests never caught
  it; they exercised only a single_branch fixture). All three pass; **no
  product defect surfaced beyond what WP13's fix already covers**. The false
  "reserved for T069's real-git leg" module-docstring claim (the coord
  fixture was in fact imported nowhere before this addition) is corrected to
  describe the topology axis honestly, both before and after this fix.
---

### Updating Lane Status

Use: `spec-kitty agent tasks move-task WP15 --to <lane> --note "message"`

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
