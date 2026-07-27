# Implementation Plan: Implement-Loop Commit & Move-Task Hardening

**Branch**: `mission/2533-pr-bound-coord-claim-precondition` | **Date**: 2026-07-15 | **Spec**: [spec.md](./spec.md)
**Input**: `kitty-specs/implement-loop-commit-hardening-01KXJ1ZX/spec.md`
**Tracker**: closes #2647, #2648, #2649, #2650 (sub-issues of #2160). Stacks on the merged #2533.

## Summary

Close four #2533 follow-ups: fix `move-task` from a lane-worktree cwd (#2647), delete the
silent protected-branch coord-divert and fail-close the narrow-triple `placement_ref is
None` state (#2648, NOT bare `None` — that stays the legit strangler path), pay down the
Sonar S3776/S107 debt in `implement.py`/`tasks_move_task.py` (#2649, folds #2604), and
consolidate the three partition-decision sites onto the existing residue predicate (#2650).
Brownfield paradigm active —
structural moves are gated on captured understanding (characterization-first), and the
consolidation is pinned to the #2533-safe direction (`kind=None`→PRIMARY, C-007) so it
cannot regress the bug #2533 just closed.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Typer, rich / CliConsole, ruamel.yaml, internal `mission_runtime` + `coordination` packages
**Storage**: Git refs (status surface, coordination vs primary branches); no database
**Testing**: `pytest` — characterization tests (pin implicit invariants before extraction), red-first bug repros through the real `move-task` / write-side entry points, structural test for the single partition authority; `-n auto --dist loadfile`
**Target Platform**: Spec Kitty CLI (Linux/macOS dev)
**Project Type**: single (Python CLI monorepo)
**Performance Goals**: N/A (correctness + maintainability)
**Constraints**: `ruff` C901 ≤ 15, params ≤ 13; `mypy --strict` zero new issues; no net-new public API (C-008); `kind=None`→PRIMARY (C-007); preserve #2576 dual-handler (C-001) and Lane-A→B symbol contracts (C-006)
**Scale/Scope**: 7 WPs, 3 lanes (final, per tasks.md); ~4 source files (implement.py, implement_cores.py, commit_router.py, tasks_move_task.py) + tests

## Charter Check

*GATE: Must pass before Phase 0. Re-check after Phase 1.*

Charter present; `charter context --action plan` = compact. **Brownfield-onboarding
paradigm ACTIVE** — its discipline governs this mission:

- **DM-D (document-then-refactor) / characterization-first** — FR-006 characterization
  gate precedes the FR-005 swap; FR-003/FR-004 pin implicit invariants before extraction
  (NFR-002 floor). ✅
- **Chesterton's fence** — the degod targets with load-bearing invariants
  (`_resolve_bookkeeping_transaction_identifiers` cascade+raise; `_json_safe_output`
  `_file=None` reset; `_mt_uncheck_rollback_subtasks` dual-handler) are pinned, not
  guessed. ✅ (C-001)
- **ATDD / red-first (DIRECTIVE_041)** — the two bugs (WP01/WP05) repro red-first through
  real entry points. ✅ (C-002)
- **Single canonical authority** — FR-005 collapses three partition sites to one; the
  consolidation direction is #2533-safe (C-007). ✅
- **No legacy resolver paths / no silent fallback** — the `kind=None`→caller-partition
  fallback (the #2533 hole) is explicitly forbidden by C-007. ✅
- **DIR-013** — any pre-existing unrelated test failure → open an issue before treating as baseline.

No Charter Check violations → **Complexity Tracking not required.**

## Project Structure

### Documentation (this mission)

```
kitty-specs/implement-loop-commit-hardening-01KXJ1ZX/
├── plan.md, research.md, data-model.md, quickstart.md, contracts/
├── traces/            # tracer files (seeded; append during implement)
└── tasks.md           # /spec-kitty.tasks output (NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/cli/commands/
├── implement.py              # Lane A — _partition_files_for_commit (write site), _commit_planning_artifacts_transaction
│                             #   (protected-branch fallback + warning, FR-002), _json_safe_output / _resolve_bookkeeping_transaction_identifiers
│                             #   / _run_recover_mode (degod, FR-003)
├── implement_cores.py        # Lane A — resolve_precondition_ref (read site + "HEAD"; FR-005)
└── agent/tasks_move_task.py  # Lane B — status-surface resolution (FR-001), _mt_commit_wp_file /
                              #   _do_move_task / _mt_uncheck_rollback_subtasks (degod, FR-004)

src/specify_cli/coordination/
└── commit_router.py          # Lane A — _group_files_by_partition (write site; kind classifier) → consolidated (FR-005)

src/mission_runtime/
└── artifacts.py              # READ-ONLY — partition authority (is_coordination_artifact_residue_path etc.)
```

**Structure Decision**: Single project. Three file-linearized lanes (final): Lane A owns
`implement.py` + `implement_cores.py`, Lane B owns `commit_router.py`, Lane C owns
`tasks_move_task.py`. `mission_runtime` read-only.

## Complexity Tracking

*Not applicable — no Charter Check violations.*

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Delete the `767` divert; NARROW-triple fail-close (#2648, FR-002)

- **Purpose**: Remove the silent `767-789` coord-divert (a #2533-introduced guard) and make
  the artifact-commit half fail-closed (`PlacementResolutionRequired`, same message as the
  status half) on the **narrow triple** — `placement_ref is None` AND meta `coord_branch`
  truthy AND `is_protected(planning_branch)` — which is EXACTLY the `767` precondition and
  EXACTLY where the status half (`_resolve_claim_commit_target`, `implement_cores.py:608`)
  already fails closed. So both halves agree on that state.
- **CRITICAL scoping (squad BLOCKER-1)**: do NOT fail-close on bare `placement_ref is None`.
  `None` is the C-004 strangler signal (`_resolve_placement_ref` returns `None` on
  ActionContextError OR `artifact_placement is None`). The legacy/flat `755` arm and the
  coord-non-protected `790` arm MUST stay green — three write-side tests
  (`test_implement_writeside.py:192/231/285`) + the #2533 regression (`test_implement.py:283`)
  drive `placement_ref=None` expecting SUCCESS. An unconditional raise reds all of them.
- **Implementation choice (resolve the plan's old "and/or")**: raise explicitly at the
  narrow-triple arm (Option B — mirror `_resolve_claim_commit_target`'s `PlacementResolutionRequired`
  + message). Do NOT rely on deleting `767` and letting the `790` else-path hit
  BookkeepingTransaction's generic `typer.Exit(1)` (Option A) — that raises the WRONG type
  and fails SC-002's "same precondition + message" requirement.
- **Requirements**: FR-002; NFR-001; guards C-002 (red-first), C-009 (narrow fail-closed, no
  primary/coord default), C-004 (the fail-closed pin is enduring for IC-04).
- **Surfaces**: `implement.py::_commit_planning_artifacts_transaction` (replace the `767`
  arm body with the raise; place the guard after the `if not files_to_commit: return`
  short-circuit). New red-first test using the `_seeded_coord_mission` harness with
  `planning_branch="main"` (protected) + `placement_ref=None`: RED = silent divert to coord;
  GREEN = `pytest.raises(PlacementResolutionRequired)`. Acceptance MUST also re-run the 3 write-side `None` tests + `TestSoloPrBoundCoordMissionClaimPrecondition` green.
- **Sequencing**: none (first in Lane A). Its fail-closed behavior is a **dependency of
  IC-04** (the consolidation must keep both halves fail-closed on one authority).
- **Risks**: the narrow triple is confirmed by WP03's characterization gate (does a real
  flat/legacy mission ever reach this seam with `None`?), not guessed. Do NOT re-add a
  warn-and-degrade; do NOT broaden to bare `None`.

### IC-02 — implement.py degod, characterization-first (#2649, FR-003) — carves into WP02a + WP02b

- **Purpose**: Reduce S3776 cognitive complexity on `_json_safe_output` (≈33),
  `_resolve_bookkeeping_transaction_identifiers` (≈16), `_run_recover_mode` (≈24),
  preserving implicit invariants. NOTE: all three already pass `ruff C901` (cyclomatic
  4-10) — S3776 is the target metric (not ruff-measurable), so the local done-condition is
  the extraction + per-helper tests + behavior preservation; S3776 confirmation is
  advisory-post-merge.
- **Carve-out (squad)**: **WP02a** = `_resolve_bookkeeping_transaction_identifiers` alone
  (the C-006 5-tuple symbol) with a signature-freeze + a consumer-side import-contract test;
  **WP02b** = `_json_safe_output` + `_run_recover_mode`. This lands the C-006 edge at Lane-A
  unit 2 and keeps the heavy S3776 work off the critical coupling.
- **Requirements**: FR-003; NFR-001, NFR-002, NFR-004; C-008.
- **Surfaces**: `implement.py` (those functions + extracted private helpers + tests).
- **Sequencing**: depends IC-01 (same file, serialized). **WP06 (Lane B degod) depends_on
  WP02a** — declared hard edge (C-006), not "preserve OR sequence".
- **Characterization floor (expanded — renata)**: pin BEFORE extraction — for
  `_resolve_bookkeeping_transaction_identifiers`: cascade order, ambiguous-handle RAISE, the
  `legacy-<slug>` mission-id fallback, and the mid8 precedence (meta-mid8 > `resolve_mid8` >
  `None`); for `_json_safe_output`: `console._file=None` reset, `console.quiet` save/restore,
  the dual exception arms (`typer.Exit` re-raised verbatim vs bare `Exception` → `typer.Exit(1)`),
  and the exit_code-0 payload suppression + last-20-non-blank summary.

### IC-03 — Partition-consolidation characterization gate (#2650, FR-006)

- **Purpose**: Document-first — enumerate the three sites + the `kind=None` disagreement
  set and pin the intended unified placement (`kind=None`→PRIMARY) before any swap.
- **Requirements**: FR-006; NFR-003; C-007.
- **Surfaces**: new characterization tests over `implement.py::_partition_files_for_commit`,
  `commit_router::_group_files_by_partition`, `implement_cores.py::resolve_precondition_ref`.
- **Sequencing**: depends IC-02 (Lane A serialization).
- **Risks**: the suites currently encode BOTH fallback directions — the gate makes the
  intended contract explicit so IC-04 is a documented move, not a guess.

### IC-04 — Partition-classifier consolidation + ref unification (#2650, FR-005) — carves into WP04a + WP04b

- **Purpose**: Route the three sites' PRIMARY-vs-COORD partition through ONE authority and
  unify the read/write primary-ref expression; keep #2648 + #2533 regressions green.
- **Scope correction (squad RISK-3, boundary)**: the authority ALREADY exists —
  `mission_runtime.is_coordination_artifact_residue_path` (two sites already call it;
  `implement.py:600`, `implement_cores.py:268`). FR-005 = swap `commit_router:404`'s
  divergent `kind_for_mission_file(file) or kind` classifier onto it. **Classifier-only**:
  keep `resolve_placement_only` for `commit_router`'s actual COORD ref (`other_ref`); do NOT
  add a cli-side `partition_of` wrapper (redundant + inverts `cli → coordination` layering,
  C-008); do NOT edit `mission_runtime` (read-only). No net-new symbol needed → satisfies
  SC-004 against the existing predicate.
- **Carve-out (squad)**: **WP04a** = the classifier swap (`commit_router:404`) + structural
  test that the three sites resolve partition through the one predicate AND `commit_router`
  no longer consults `is_primary_artifact_kind(kind_for_mission_file(...))` for the split.
  **WP04b** = the read (`"HEAD"`) / write (`planning_branch`) primary-ref unification —
  cli-local (Lane A), does NOT touch `commit_router`; own structural test + its own
  regression surface (detached-HEAD / off-target). Two authorities, two tests.
- **Requirements**: FR-005; SC-004; guards C-007 (kind=None→PRIMARY), C-004 (#2648 green).
- **Surfaces**: WP04a: `commit_router.py` (+ the residue predicate call). WP04b:
  `implement.py`, `implement_cores.py`. Structural tests per WP.
- **Sequencing**: depends IC-03 (characterization) → IC-02 → IC-01.
- **Risks**: **the #2533 regression** — consolidating onto the kind-classifier's
  caller-fallback would misroute `meta.json`→COORD; C-007 forbids it. Structural test must
  assert the kind-classifier is dropped for the split, not merely that meta.json routes
  PRIMARY (else a future coord-kind caller re-diverges past the test — squad RISK-4).

### IC-05 — move-task cwd-independent status surface (#2647, FR-001)

- **Purpose**: `move-task` resolves the mission status surface from the canonical mission
  root regardless of cwd; works from a lane worktree AND from repo root.
- **Requirements**: FR-001; NFR-001; C-002 (red-first).
- **Surfaces**: `tasks_move_task.py` status-read path. **Localization caveat (squad RISK-4)**:
  `_read_transactional_wp_lane` at `:308` ALREADY reads with `repo_root=st.main_repo_root`
  (mission root) — it is NOT the taint. The cwd taint enters upstream at `locate_project_root()`
  (`:244`) and `locate_work_package(repo_root, …)` (`:306`). The red-first test MUST FIRST
  locate which read returns the stale lane before extracting; if no fixture can make the
  currently-named seam go RED, the seam is misidentified — escalate before the fix.
- **Sequencing**: none (first in Lane B). Independent of Lane A.
- **Risks / test shape**: drive a REAL `git worktree` fixture with `monkeypatch.chdir(worktree)`
  so `is_worktree_context(cwd)` (`:223-224`) is genuinely true; RED asserts the concrete
  "Illegal transition" error string (not merely "succeeds after"); pair with an explicit
  repo-root-cwd no-regression assertion (FR-001).

### IC-06 — tasks_move_task.py degod, characterization-first (#2649, FR-004) — folds #2604

- **Purpose**: Decompose `_mt_commit_wp_file` (S3776≈19), `_do_move_task` (**21 params** →
  param-object), `_mt_uncheck_rollback_subtasks` (S8572). Folds
  [#2604](https://github.com/Priivacy-ai/spec-kitty/issues/2604) (same `_mt_commit_wp_file`).
- **Gate re-anchor (brownfield check)**: the S3776 reductions are advisory-post-merge; the
  ONE locally-hard gate is `_do_move_task` **parameters ≤ 13** (from 21, via param-object) —
  this is the concrete acceptance. Do NOT assert success via `ruff C901` (already green).
- **Requirements**: FR-004; NFR-001, NFR-002, NFR-004; C-001 (#2576 dual-handler), C-005 (#2639), C-008.
- **Surfaces**: `tasks_move_task.py` (those functions + private helpers + tests).
- **Sequencing**: depends IC-05 (same file). **Declared hard C-006 edge: WP06 depends_on
  WP02a** (the runtime call at `:1392` consumes the 5-tuple regardless of ordering — the
  guard is the dep edge + WP02a's consumer contract test, not "reconcile if changed").
  Landing note C-005 — rebase after PR #2639.
- **Risks**: do NOT merge the #2576 dual-handler / swap to `logging.exception` (C-001);
  keep the degrade-never-crash discipline; param-object so #2639's added arg stays ≤13.

## Work-Package Shape (FINAL — as finalized by /spec-kitty.tasks; tasks.md is authoritative)

> The IC map above used provisional `WP02a/WP04a` a/b labels. `/spec-kitty.tasks` consolidated
> them into a strict `WP\d+` numbering (the finalizer collapses alphabetic suffixes) and, to
> break a lane cycle, folded the FR-006 characterization gate into the cli-side ref-unification
> WP. Final shape: **7 WPs / 3 file-linearized lanes** (post-tasks squad-reviewed).

- **Lane A — `implement.py` + `implement_cores.py` (serial):**
  - **WP01** — #2648 delete `767` + **narrow-triple** fail-close (NOT bare `None`; preserve the
    `755`/`790` strangler arms).
  - **WP02** — degod `_resolve_bookkeeping_transaction_identifiers` (the C-006 5-tuple symbol),
    signature-frozen + consumer-side import-contract test.
  - **WP03** — degod `_json_safe_output` + `_run_recover_mode` (the heavy S3776).
  - **WP04** — FR-006 characterization gate **+** FR-005 cli-side read/write ref-unification.
    The gate is folded here (not a separate test-only lane) so it isn't a mid-chain island that
    would cycle the lane graph. Does NOT touch `commit_router`.
- **Lane B — `coordination/commit_router.py`:** **WP05** — FR-005 classifier-only swap of
  `commit_router:404` onto the existing residue predicate. `depends_on WP04`.
- **Lane C — `agent/tasks_move_task.py` (serial):** **WP06** (#2647 move-task cwd) → **WP07**
  (#2649 move-task degod + `_do_move_task` param-object; folds #2604).
- **C-006 is a declared hard dependency edge:** **WP07 `depends_on` WP02** (the runtime call at
  `tasks_move_task.py:1392` reads `_resolve_bookkeeping_transaction_identifiers`' return the
  moment WP02 reshapes it, regardless of lane parallelism). Lane graph: Lane B → Lane A and
  Lane C → Lane A, acyclic; Lane A independent.
- **Parallelism (corrected — the earlier "zero critical-path" claim was wrong):** WP06 (#2647,
  P1 bug) has **no** WP-level dependencies and should be claimable immediately, in parallel with
  Lane A — do NOT let it be withheld behind Lane A. It shares Lane C's file with WP07 (which
  `depends_on WP02`), so the allocator marks the whole lane `depends_on lane-a`; that is a
  lane-granularity artifact, not a real dependency of WP06. Claim WP06 first (per-WP readiness
  gates on WP-level deps, which WP06 has none of). If the allocator can only gate per-lane, land
  WP06 as an early standalone before WP07 — the P1 fix must not wait on the tech-debt WPs.
  (Logged as a tooling gap in `traces/tooling-friction.md`.)

## Scope Fences

- **IN**: the four named issues only; consolidate the three named partition sites + unify
  the ref expression; the two named bug fixes; the six named degod functions.
- **OUT**: broader #2160 placement-seam work beyond these three sites; any behavior change
  to move-task/commit semantics beyond the two bugs; `mission_runtime/*` edits (read-only).
