# Mission Specification: Decompose the `merge.py` God-Module

**Mission Branch**: `prog/2057-merge`
**Created**: 2026-06-24
**Status**: Approved
**Input**: Issue #2057 — decompose `src/specify_cli/cli/commands/merge.py` (3383 LOC, maxCC ~102) into cohesive, independently-testable seams plus a thin command-registration shim, preserving the public `spec-kitty merge` CLI surface byte-for-byte.

## Overview

`src/specify_cli/cli/commands/merge.py` is a god-module: **3383 lines of code** with a
**maximum cyclomatic complexity of ~102** concentrated in a single 706-LOC procedure
(`_run_lane_based_merge_locked`). It hosts 64 top-level functions plus the `merge`
Typer command, mixing nine distinct concerns: slug/state resolution, target-branch
preflight, dry-run forecasting, lane-merge execution, mission-number baking,
done-bookkeeping, status-surface snapshot/restore projection, baseline-ordering
invariants, and command registration.

This mission is a **strictly behavior-preserving refactor**. It decomposes the module
into cohesive seams under the established `src/specify_cli/merge/` sibling package
(extending it, not reinventing it — the `baseline_merge_commit` cluster was already
extracted there under epic #2026, proving the one-way-import seam pattern is
cycle-free). The `spec-kitty merge` CLI surface — every flag, default, help string,
exit code, error message, and the dry-run JSON schema — must remain **byte-for-byte
identical**. No functional change ships.

The work is gated on first capturing a **golden CLI characterization test** against
the pre-refactor module, because the existing suite exercises internal functions
heavily but barely touches the CLI surface itself (only `--abort` is invoked via
`CliRunner` today). That golden test is the byte-identity proof for the entire mission.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Operator runs `spec-kitty merge` unchanged (Priority: P1)

An operator (or an orchestrator, or CI) invokes `spec-kitty merge` with any
combination of flags — `--strategy`, `--dry-run`, `--json`, `--mission`, the hidden
`--feature` alias, `--resume`, `--abort`, `--push`, `--yes`, etc. After the refactor,
every invocation behaves exactly as before: same parsing, same help text, same exit
codes, same human and JSON output, same side effects.

**Why this priority**: The mission's entire success criterion is "public surface
preserved byte-for-byte." If an operator observes any behavioral drift, the mission
has failed regardless of internal cleanliness.

**Independent Test**: A golden CLI characterization test (Typer `CliRunner` against
the fully registered app) snapshots `merge --help`, all flag/default parsing, the
dry-run JSON payload schema, the `--json`-without-`--dry-run` error string, and the
headline error/exit-code paths. Captured on the pre-refactor module, it must pass
unchanged after every seam extraction.

**Acceptance Scenarios**:

1. **Given** the pre-refactor module, **When** the golden CLI test captures the
   contract, **Then** `merge --help` output, every flag/default, and the dry-run JSON
   key set are recorded as the frozen baseline.
2. **Given** the fully refactored module set, **When** the golden CLI test runs,
   **Then** it passes byte-for-byte against the captured baseline.
3. **Given** `spec-kitty merge --json` without `--dry-run`, **When** invoked,
   **Then** it prints `{"spec_kitty_version", "error": "--json is currently supported with --dry-run only."}` and exits 1 — unchanged.
4. **Given** `spec-kitty merge --dry-run --json`, **When** invoked, **Then** the JSON
   payload carries exactly the keys `spec_kitty_version, mission_slug, target_branch,
   strategy, delete_branch, remove_worktree, push, mission_branch, lanes,
   would_assign_mission_number` — unchanged.

---

### User Story 2 - Maintainer fixes a seam in isolation (Priority: P2)

A maintainer needs to fix a bug in (say) the dry-run forecast or the done-bookkeeping
projection. After the refactor, that concern lives in its own focused module with its
own focused tests, so the maintainer can reason about and test it in isolation rather
than navigating a 3383-LOC file with a CC-102 procedure.

**Why this priority**: Maintainability is the reason for the mission, but it is
subordinate to byte-identity (P1) — a clean decomposition that breaks the surface is
worthless.

**Independent Test**: Each extracted seam module imports cleanly, owns a focused test
file with ≥90% coverage of the moved code, and every function in it measures ≤15
cyclomatic complexity (radon / ruff C901 / Sonar S3776).

**Acceptance Scenarios**:

1. **Given** a refactored seam module, **When** `radon cc` / `ruff` runs, **Then**
   every function reports CC ≤ 15.
2. **Given** a seam's focused test file, **When** coverage runs, **Then** the moved
   code reports ≥90% coverage.
3. **Given** a seam module, **When** import order is analyzed, **Then** it imports
   only leaf/sibling packages and never `cli.commands.merge`.

---

### User Story 3 - #1827 baseline-ordering invariant preserved (Priority: P1)

The #1827 fix established a strict ordering: the target baseline SHA is recorded after
the target merge but before the bookkeeping commit, then asserted after the commit
lands, with a restore-on-`BaselineMergeCommitError` rollback. The decomposition of the
CC-102 procedure must preserve this exact ordering and rollback across the new
phase-helper boundaries.

**Why this priority**: A regression here reintroduces the #1827 circular-failure /
data-loss class. It is as critical as the CLI surface.

**Independent Test**: A phase-boundary regression test asserts baseline record →
bookkeeping safe_commit → baseline assert ordering, and that a
`BaselineMergeCommitError` triggers the snapshot restore-then-reraise path.

**Acceptance Scenarios**:

1. **Given** the executor decomposition, **When** the merge flow runs, **Then**
   baseline is recorded post-target-merge / pre-bookkeeping-commit and asserted
   post-commit — same call ordering as pre-refactor.
2. **Given** a `BaselineMergeCommitError` at assert time, **When** raised, **Then**
   `_restore_final_bookkeeping_snapshots` runs and the error re-raises — same
   exception scoping as pre-refactor.

### Edge Cases

- `spec-kitty merge --resume` with no interrupted merge → "No interrupted merge to
  resume." exit 1 — unchanged.
- Unresolved mission slug → "Mission slug could not be resolved. Use --mission
  <slug>." exit 1 — unchanged.
- `--abort` cleanup sequence (state clear, global lock unlink, legacy
  `merge-state.json` unlink, git-merge abort, coordination teardown) — unchanged order
  and side effects.
- Dry-run review-artifact gate emits `REJECTED_REVIEW_ARTIFACT_CONFLICT` in both human
  and JSON output — unchanged.
- Unused compat flags `--context` / `--keep-workspace` (parsed then `del`'d) still
  accepted silently — unchanged.
- The ~6 snapshot-restore-on-exception try/except sites keep identical
  exception-class scoping and ordering across phase boundaries.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Preserve `spec-kitty merge` CLI surface byte-for-byte | As an operator, I want every `spec-kitty merge` flag, default, help string, the hidden `--feature` alias, the `--json`-without-`--dry-run` error string, the dry-run JSON schema, and exit codes to be byte-identical so that no invocation changes behavior. | High | Approved |
| FR-002 | Top-of-file decomposition pointer comment | As a maintainer, I want a top-of-file comment referencing issue #2057 documenting the decomposition (matching the #2056 / #1623 convention) so that the shim's role and seam map are discoverable. | Medium | Approved |
| FR-003 | Decompose into the research-resolved seams | As a maintainer, I want the module split into the resolved seams — executor, done_bookkeeping, bookkeeping_projection, git_probes, forecast, resolve, preflight (relocation), baseline/ordering (into existing `merge/` modules), with the shim keeping only the `merge` command — so that each concern is cohesive and testable. | High | Approved |
| FR-004 | Each extracted seam carries focused tests | As a maintainer, I want every extracted seam to ship a focused test file with ≥90% coverage of the moved code so that the seam is independently verifiable. | High | Approved |
| FR-005 | Internally decompose the CC-102 driver and other >15-CC functions | As a maintainer, I want `_run_lane_based_merge_locked` (CC102) decomposed via a `_MergeRunState` dataclass threaded through ~9 phase helpers (each maxCC≤15) preserving the ~6 snapshot-restore-on-exception sites exactly, and the other offenders (`merge`, `_mark_wp_merged_done`, `_collect_hollow_review_warnings`, `_assert_merged_wps_done_on_target`) flattened to ≤15, so that no function exceeds the complexity ceiling. | High | Approved |
| FR-006 | Re-export relocated symbols from the shim | As an external consumer (orchestrator_api/commands.py, agent/mission.py, doctor.py) or one of ~41 test files, I want all relocated symbols re-exported from the shim so that imports keep working with zero churn and `__all__` ordering stays byte-stable. | High | Approved |
| FR-007 | Preserve #1827 baseline record/assert ordering (INV-5) | As an operator, I want the baseline record (post-target-merge, pre-bookkeeping-commit) → bookkeeping commit → baseline assert (post-commit) ordering and the restore-on-`BaselineMergeCommitError` rollback preserved exactly, with a phase-boundary regression test, so that the #1827 data-loss class cannot recur. | High | Approved |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Complexity ceiling | Every function in every resulting module measures cyclomatic complexity ≤ 15 (radon cc / ruff C901 / Sonar S3776 aligned). | Maintainability | High | Approved |
| NFR-002 | New-code coverage | New / moved code reports ≥ 90% line coverage via focused tests in the same WP. | Reliability | High | Approved |
| NFR-003 | Clean static gates | `ruff check` and `mypy --strict` report zero issues and zero new suppressions (no new `# noqa` / `# type: ignore` / Sonar suppressions). | Code Quality | High | Approved |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | No command/flag changes | No command, flag, short option, default, or help-text change to the `spec-kitty merge` surface. | Technical | High | Approved |
| C-002 | Use existing `merge/` modules | Relocate into the existing `merge/` package modules where they exist (`baseline.py`, `ordering.py`, `preflight.py`, `push_preflight.py`, `state.py`, `workspace.py`) — do not reinvent them; add new modules only for genuinely new seams. | Technical | High | Approved |
| C-003 | Fully behavior-preserving | No functional behavior change; the refactor is a pure topology/structure change proven by the existing suite plus the golden CLI test. | Technical | High | Approved |
| C-004 | No new suppressions | No new `# noqa`, `# type: ignore`, or Sonar suppression comments to pass gates — fix the code instead. | Code Quality | High | Approved |
| C-005 | Golden-test-first verification | Verification begins by capturing a golden CLI characterization test on the pre-refactor module (WP01) before any seam moves. | Process | High | Approved |
| C-006 | One-way imports | No `merge/*` seam imports `cli.commands.merge`; the shim imports from seams, seams import only leaf/sibling packages (INV-2). | Technical | High | Approved |
| C-007 | Lazy imports stay lazy | In-function imports (`lanes.merge`, `policy.merge_gates`, `coordination.*`, `status` enums) are not hoisted to module top during the move (INV-7). | Technical | Medium | Approved |
| C-008 | Locked constants untouched | `LINEAR_HISTORY_REJECTION_TOKENS` tuple order and membership unchanged (INV-8). | Technical | Medium | Approved |

### Key Entities

- **Shim (`cli/commands/merge.py`)**: command-registration only (~120 LOC, maxCC ≤15)
  after refactor. Hosts the `merge` Typer command (decomposed into
  `_dispatch_abort` / `_dispatch_resume` / `_dispatch_dry_run` / `_run_real_merge`
  helpers) and re-exports relocated symbols to keep `__all__` and external importers
  byte-stable.
- **`merge/executor.py`** (NEW): `_run_lane_based_merge` (lock wrapper) +
  `_run_lane_based_merge_locked` decomposed into ~9 phase helpers consuming the other
  seams.
- **`_MergeRunState`** (NEW dataclass): threads the shared mutable merge state
  (snapshots, baseline SHA, mission-number meta path, done-marked flags, paths)
  through the phase helpers without closures.
- **`merge/git_probes.py`** (NEW): branch/tree/porcelain git primitives, incl.
  `path_is_under_worktrees` (public consumer symbol).
- **`merge/forecast.py`** (NEW): dry-run preview + JSON/human payload build.
- **`merge/done_bookkeeping.py`** (NEW): `_mark_wp_merged_done` (split) + done/approved
  transitions + done asserts + resume reconcile.
- **`merge/bookkeeping_projection.py`** (NEW): status-surface trust + snapshot/restore +
  projection cluster.
- **`merge/resolve.py`** (NEW or folded into `state.py`): slug/state/target resolution.
- **`merge/preflight.py`** (EXISTING, extended): git/target/mission-branch/review/hollow
  preflights relocated in.
- **`merge/baseline.py`** (EXISTING, unchanged): #1827 record/assert home.
- **`merge/ordering.py`** (EXISTING, extended): mission-number bake cluster relocated in.
- **`merge/_constants.py`** (NEW): shared literals / type aliases / logger (S1192-safe).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The golden CLI characterization test passes byte-for-byte before and
  after the refactor (FR-001, C-005).
- **SC-002**: `radon cc` reports every function in `cli/commands/merge.py` and every
  `merge/*` seam module at CC ≤ 15 (NFR-001, FR-005); the pre-refactor maxCC of ~102
  drops to ≤15.
- **SC-003**: `cli/commands/merge.py` drops from 3383 LOC to ~120 LOC (shim only).
- **SC-004**: New/moved code reports ≥90% line coverage (NFR-002, FR-004).
- **SC-005**: `ruff check` and `mypy --strict` report zero issues and zero new
  suppressions (NFR-003, C-004).
- **SC-006**: All ~41 importing test files and the 3 src consumers
  (orchestrator_api/commands.py, agent/mission.py, doctor.py) pass with zero import
  edits (FR-006).
- **SC-007**: The #1827 phase-boundary regression test passes, confirming baseline
  record→commit→assert ordering and restore-on-error rollback (FR-007, INV-5).

## Assumptions

- The existing internal-function test suite is trustworthy for seam *logic*
  regressions (recovery, resume, coord-topology, post-merge invariant, data-loss
  cases) but NOT for byte-identity of the CLI surface — hence the golden test.
- Re-export from the shim (not repointing importers) is the chosen low-risk,
  byte-stable strategy for FR-006.
- The `merge/` one-way-import discipline is already in force (verified: no `merge/*`
  module imports `cli.commands.merge`) and continues unchanged.
- No new third-party dependency is needed; the work is a topology change within the
  existing single-project layout.

## Research outcomes

This spec is grounded in
[`research.md`](research.md) and [`data-model.md`](data-model.md):

- The **9-seam resolved set** (research §3) and the target module topology
  (data-model "Target topology") drive FR-003 and the WP breakdown.
- The **mega-function finding** — `_run_lane_based_merge_locked` at CC102 / ~706 LOC
  is the core risk, with ~9 ordered phases and pervasive shared mutable state —
  drives FR-005 and the `_MergeRunState` dataclass design (data-model "Phase-state
  object").
- The **test-coverage verdict** (research §5) — the CLI surface is barely exercised,
  so a golden CLI characterization test must be captured FIRST — drives C-005 and
  WP01.
- The **#1827 baseline-ordering invariant (INV-5/INV-6)** (research §6.2,
  data-model "Invariants") drives FR-007.
- The **symbol re-export contract** (research §4, data-model "Symbol contract") drives
  FR-006.
