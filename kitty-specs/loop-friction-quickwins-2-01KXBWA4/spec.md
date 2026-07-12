# Mission Specification: Implement-Loop Friction Quick-Wins II

**Mission Branch**: `feat/loop-friction-quickwins-2`
**Created**: 2026-07-12
**Status**: Draft
**Input**: Friction cluster #2555 / #2566 / #2493 / #2570 / #2589, investigated by a 4-lens pre-spec research squad (self-writing guards / authority-split+dedup / gate-subprocess / papercuts) against fresh `upstream/main`.
**Parents**: #2017 (workflow-guard friction — primary) + #2093 (runtime-state authority) + #2160 (coord-topology authority — adjacent).
**Successor of**: `loop-friction-fastfollow` (unmerged quick-wins I: #2581 / #2573 skip-flag+progress / #2549 facet B / #2577).

## Summary

The implement→review loop's lifecycle guards and gates repeatedly block legitimate in-flight
actions by tripping on artifacts they themselves just wrote, or by returning inconclusive verdicts
that force an operator to `--force`. Each is worked around manually, which inflates `force_count`,
hollows guard signal, and trains agents into off-workflow habits — the durable defect class #2017
exists to eliminate. This mission clears the highest-friction, lowest-risk points as the successor
slice to the loop-friction fast-follow, without touching the harder coord-authority redesign.

The binding invariant: **every fix removes a false positive while preserving the guard's real
protective signal.** Substantive spec/plan/task changes must still stale the analysis-report;
genuine bulk edits must still trip; the pre-review gate must still enforce by default. Each fix
ships with a red-first regression proving the true-positive still fires.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Guards are no-op-stable against their own runtime writes (Priority: P1)

An agent batch-allocates lane worktrees for a multi-WP mission, and hands WPs off with
`mark-status`. Neither the allocator's own runtime-frontmatter write nor a status-marker write
should cause the *next* guard to refuse a legitimate action.

**Why this priority**: This friction compounds per-WP across every mission (a 6-lane mission forced
a manual commit between all six allocations; `mark-status` re-staled the analysis-report after
nearly every WP handoff). It is the highest-frequency pain in the cluster.

**Independent Test**: Allocate N lanes in sequence with `auto_commit=False` and assert zero manual
commits are required between allocations; run `mark-status` on a pipe-table `tasks.md` then an
`implement` claim and assert no `stale_analysis_report`.

**Acceptance Scenarios**:

1. **Given** a mission whose only uncommitted change is a WP file's runtime frontmatter
   (`shell_pid`/`shell_pid_created_at`/`base_branch`/`base_commit`) written by a prior claim,
   **When** the allocator runs the uncommitted-artifact check for the next lane, **Then** it does
   not block on that runtime-only diff (mirroring the shipped `_drop_vcs_lock_only_meta` seam).
2. **Given** a substantive edit to `spec.md`/`plan.md` or a task-definition row, **When** the
   allocator check runs, **Then** it still blocks (true-positive preserved).
3. **Given** a pipe-table `tasks.md` whose only change is `[ ]`→`[D]`/`[P]` status-cell churn from
   `mark-status`, **When** the next `implement` claim runs the analysis-report freshness check,
   **Then** the report is considered current (no `stale_analysis_report`).
4. **Given** a substantive change to a `tasks.md` row's text, **When** the freshness check runs,
   **Then** the report is correctly reported stale.

### User Story 2 — The pre-review gate returns real verdicts, never a spurious `--force` (Priority: P1)

An agent runs `move-task --to for_review` in a `uv`-managed checkout whose interpreter lacks the
test-only `pytest` extra, possibly with sibling lanes running shards concurrently. The gate must
find the test runner and return a real pass/fail, not an inconclusive `no_coverage` that forces a
`--force` on a green tree.

**Why this priority**: A spurious `--force` on a passing tree hollows the gate's entire purpose and
is the most corrosive friction to guard trust. The current real-subprocess tests run under a
pytest-equipped interpreter and actively **mask** this bug.

**Independent Test**: Invoke the gate under an interpreter with no `pytest` on its path but with a
green `uv run pytest`, and assert a real verdict (not `no_coverage`); run two gate invocations
concurrently and assert neither reports a false timeout.

**Acceptance Scenarios**:

1. **Given** a spec-kitty checkout where `sys.executable -m pytest` fails with `No module named
   pytest` but `uv run pytest` is green, **When** the pre-review gate runs, **Then** it resolves
   the runner via the project interpreter (`uv run`) and returns a real verdict.
2. **Given** `uv` is not on PATH, **When** the gate runs, **Then** it falls back to `sys.executable`
   without a crash (documented fallback).
3. **Given** multiple lane agents run scoped gate subprocesses simultaneously, **When** the gate
   runs under contention, **Then** it does not emit a false timeout-driven `no_coverage`.
4. **Given** a dispatched implement/review sub-agent hits a multi-minute gate, **When** it follows
   the documented contract, **Then** the expected poll-or-handback behavior is defined and testable.

### User Story 3 — Committed state is portable and diagnostics are legible (Priority: P2)

A maintainer works across machines/clones and occasionally hits a malformed artifact. Running
`spec-kitty upgrade` on a second machine must not dirty the tree, a malformed issue-matrix column
must be named in the error, and ordinary refactor prose must not trip the bulk-edit block.

**Why this priority**: Self-contained papercuts — each a permanent, recurring annoyance with a small,
low-risk fix and obvious regression tests. High cumulative value, low blast radius.

**Independent Test**: Run `upgrade` on a second path and assert zero manifest diff; feed a matrix
with a non-canonical column and assert the error names it; score an ordinary-refactor spec and
assert `triggered is False` while a genuine bulk-edit spec asserts `triggered is True`.

**Acceptance Scenarios**:

1. **Given** a committed manifest with repo-relative `output_path`, **When** `upgrade` runs on a
   different machine/path, **Then** the manifest produces zero diff.
2. **Given** a legacy manifest with absolute `output_path` loaded under a different `project_root`,
   **When** it is read, **Then** the reconstructed live path still resolves (`.exists()`), no
   migration required.
3. **Given** an issue-matrix whose mandatory column header is spelled non-canonically, **When** the
   approval gate reports, **Then** it leads with schema-drift naming the offending/normalized column,
   not "Missing rows: #A, #B, …".
4. **Given** a spec containing ordinary refactor verbs ("refactor", "update", "change") plus a single
   "rename" on a non-bulk mechanism change, **When** bulk-edit inference runs, **Then** it does not
   trip the block; **and Given** "rename all occurrences … across the codebase", **Then** it still trips.

### User Story 4 — plan/specify do not report `blocked` on the happy path (Priority: P2)

A maintainer runs `/spec-kitty.plan` or `/spec-kitty.specify` for the first time on a clean mission.
The first scaffold write must not read as an error/`blocked`.

**Why this priority**: Every mission plan/specify pays one guaranteed extra round-trip and a
write-then-discard artifact today. Removing it smooths the very front door of the workflow.

**Independent Test**: Run `setup-plan` (and the specify equivalent) once on a freshly-scaffolded
mission and assert the `result` is a distinct non-error state, not `blocked`; assert a populated but
insufficient plan still returns `blocked`.

**Acceptance Scenarios**:

1. **Given** a brand-new mission with only a freshly-written template scaffold, **When** `setup-plan`
   runs, **Then** `result` is a distinct non-error state (e.g. `scaffolded`/`awaiting_content`), not
   `blocked`.
2. **Given** a plan populated with real-but-insufficient content, **When** `setup-plan` runs, **Then**
   it still returns `blocked` (the commit-boundary guard's real signal is preserved).
3. **Given** a substantive committed plan, **When** `setup-plan` runs, **Then** it commits and
   advances as today.

### User Story 5 — move-task on a coord-topology lane self-heals its recovery (Priority: P2)

An agent moves a WP (even a zero-code-diff one) to `for_review` on a coord-topology mission. The move
must not require a brittle multi-step `git restore` + guard-blocked-commit dance.

**Why this priority**: A 0-diff WP needed six `move-task` attempts. Real, unowned residual — but it
sits on the move-task staging / commit-guard surface shared with in-flight coord-authority work, so
it is scoped as an isolated, coordination-aware WP.

**Independent Test**: Drive a `move-task --to for_review` on a coord-topology lane with untracked
planning artifacts on primary and assert a single self-healing path (no manual `git restore`
sequence), with STATUS_STATE placement semantics unchanged.

**Acceptance Scenarios**:

1. **Given** untracked planning artifacts on the primary repo and a coord-topology lane, **When**
   `move-task --to for_review` runs, **Then** it resolves the planning-artifact staging through the
   established authority path without asking the lane branch to commit `kitty-specs/`.
2. **Given** the fix, **When** the existing coord authority semantics run (merged #168 placement),
   **Then** STATUS_STATE placement is byte-for-byte unchanged (no second split-brain).

### Edge Cases

- A `tasks.md` mixing bullet-checkbox markers and pipe-table status cells — both must normalize under freshness hashing.
- A profile whose `output_path` is genuinely out-of-tree (not under `project_root`) — serializer falls back to absolute, mirroring `source_path`.
- Legacy 6-field absolute manifest re-serialized once — lands as 8-field + relative, clean thereafter.
- `uv` present but the project has no `pyproject.toml` at the resolved root — interpreter resolver falls back safely.
- A genuinely-bulk spec that omits explicit "all/everywhere" scale words but renames across many files — inference must still catch it via HIGH-weight phrases (guard against under-detection).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Allocator (and move-task) exclude their own runtime frontmatter from the uncommitted-artifact check | As an implementing agent, I want lane allocation to ignore the `shell_pid`/`base_*` fields the claim itself wrote (sourced from the canonical `WP_FIELD_ORDER`) so I can batch-allocate lanes without a commit between each; a change to the WP body must still block. (#2570.1, folds #2580) | High | Open |
| FR-002 | Analysis-report freshness ignores pipe-table status-marker churn | As an implementing agent, I want `mark-status`'s `[D]`/`[P]` table-cell writes to not re-stale the analysis-report so my next claim is not falsely blocked. (#2493.1) | High | Open |
| FR-003 | Pre-review gate resolves the test runner via the project interpreter | As a reviewing agent, I want the gate to run `pytest` via `uv run` (falling back to `sys.executable`) so a uv-managed checkout returns a real verdict instead of `no_coverage`. (#2570.3) | High | Open |
| FR-004 | Pre-review gate is contention-safe under concurrent lanes | As a reviewing agent, I want the gate to not emit a false timeout-driven `no_coverage` when sibling lanes run shards concurrently. (#2493.3) | Medium | Open |
| FR-005 | Documented sub-agent long-gate contract | As an orchestrating agent, I want a defined contract (poll-to-completion vs. orchestrator hand-back) for a dispatched sub-agent that hits a long/background gate. (#2555.4) | Medium | Open |
| FR-006 | Manifest `output_path` stored repo-relative | As a maintainer, I want the committed `agent_profiles_manifest.json` to store `output_path` repo-relative (like `source_path` already is) so `upgrade` is deterministic cross-machine, while the reader tolerates legacy absolute values. (#2589) | Medium | Open |
| FR-007 | Issue-matrix errors name the schema drift / offending column | As an operator, I want the issue-matrix approval blocker to lead with the offending/normalized column when a header is malformed, not a misleading "Missing rows" list. (#2555.5) | Medium | Open |
| FR-008 | Bulk-edit inference does not trip on ordinary refactor verbs | As a spec author, I want low-weight refactor verbs to be descriptive context, not evidence that pushes a non-bulk change over the blocking threshold, while genuine bulk edits still trip. (#2555.3) | Medium | Open |
| FR-009 | plan first scaffold write returns a distinct non-error result | As a maintainer, I want the first happy-path `setup-plan` scaffold write to return a distinct non-error state (a net-new pristine-vs-insufficient predicate), not `blocked`; the specify side already returns `scaffold_only: success` so only the plan side + named consumers (source prompts, agent-copy regen, `next` engine result-switch) change. (#2566) | Medium | Open |
| FR-010 | move-task coord-lane recovery routes staging through the authority path | As an implementing agent, I want `move-task` on a coord-topology lane to resolve planning-artifact staging through the established authority path (`commit_router`/`resolve_planning_artifact_staging`) so no manual `git restore` is ever needed — with NO `commit_guard` exemption and STATUS_STATE placement byte-unchanged. (#2555.1) | Medium | Open |
| FR-011 | Solo PR-bound coord mission routes empty-coord surface cleanly to primary | As a maintainer, I want a solo PR-bound `--start-branch` mission whose coord worktree is legitimately empty to resolve its status surface cleanly to PRIMARY (no split-brain warning, no manual flatten), with the read surface proven to match the write placement — fixing the CONSEQUENCE while the `pr_bound⇒coord` derivation stays (revisited in a follow-up). (#2533) | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Zero inter-allocation commits | After FR-001, batch-allocating N lanes requires 0 manual commits between allocations (was N−1), verified by a sequential-allocation test. | Reliability | High | Open |
| NFR-002 | Zero spurious staleness on status churn | After FR-002, a `mark-status`→`implement` cycle on a pipe-table `tasks.md` yields 0 `stale_analysis_report` results, verified by a pipe-table regression test. | Reliability | High | Open |
| NFR-003 | Zero interpreter-caused forced `--force` | After FR-003, in a checkout where `uv run pytest` is green the gate returns a real verdict; forced `--force` attributable to interpreter selection = 0, proven by a pytest-lacking-interpreter test. | Correctness | High | Open |
| NFR-004 | Manifest backward-compatibility | After FR-006, the reader accepts both absolute (legacy) and relative `output_path` with 0 migration required; in-tree entries re-serialize to relative and round-trip losslessly. | Compatibility | High | Open |
| NFR-005 | Guard true-positive preservation | Every guard fix (FR-001/002/003/008/009) preserves its real signal, each pinned by a red-first regression asserting the true-positive still fires (substantive change stales; genuine bulk trips; insufficient plan blocks; gate enforces by default). | Correctness | High | Open |
| NFR-006 | Diagnostic clarity | After FR-007, the issue-matrix schema-drift error names the offending/normalized column(s), verified by a malformed-column test asserting the message content. | Usability | Medium | Open |
| NFR-007 | Test coverage & complexity | Every new branch/helper carries a focused test in the same WP; new/changed functions stay at cyclomatic complexity ≤15; ruff + mypy pass with zero issues. | Maintainability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Remove false positives only | No fix may weaken a guard's protective purpose; each pairs with a red-first regression proving the true-positive still fires (charter red-first discipline). | Technical | High | Open |
| C-002 | Coord-adjacency coordination (FR-010) | IC-07 (#2555.1) routes move-task planning-artifact staging through the authority path (`commit_router`/`resolve_planning_artifact_staging`/`skip_target_commit`). The coord line it once feared already MERGED into base (partition-lock #168; `implement-loop-coord-authority-completion` #2194; `coord-authority-trio-degod` #2545) — so this is "do not regress the shipped partition-lock #168 invariants", NOT sequence-with-in-flight. MUST NOT add a `commit_guard.block_mission_specs` exemption (WP-file commits already route to primary) and MUST NOT touch STATUS_STATE placement (`_mt_resolve_status_placement_ref`/`_collect_status_artifacts`/`_primary_bundle_status_artifacts`). Coordinate with gate-registration refactors #2596/#2598; cross-ref #2300. **WP07↔WP08 boundary (SSOT):** WP07 owns the WRITE placement (frozen) + kitty-specs staging leg; WP08 owns the READ surface (`resolve_status_surface_with_anchor` `CoordState.EMPTY` arm only) and must not touch `tasks_move_task.py`; their agreement (read surface == write placement == PRIMARY for the solo-empty case) is pinned by WP08's same-path regression — the split-brain is killed by construction, not masked. | Technical | High | Open |
| C-003 | Scope exclusions | OUT of scope: #2493.2 (review-cycle canonical write — already shipped via `create_rejected_review_cycle`, verified; residual is agent-bypass = doctrine); coord-authority status-placement (#2570.2/#2549 facet A) and status-display (#2570.4/#2334) items; #2583 (issue-matrix gate-timing / first-approval scope-conflation — same file as FR-007 but a distinct approve-gate-semantics defect, treat separately per fast-follow precedent); the pre-review-gate async redesign (deferred on #2573). | Technical | High | Open |
| C-004 | Interpreter fix must not be self-masked | FR-003 MUST add a regression under a pytest-lacking interpreter; the existing real-subprocess gate tests run under a pytest-equipped interpreter and would otherwise mask the bug (update those two masking tests). | Technical | High | Open |
| C-005 | Successor, not re-tread | Complements the **merged** `loop-friction-fastfollow` (all four surfaces on upstream/main: #2581 `ec3e2c528`, #2573 skip-flag `35f3a2206`, #2549B `8612ee788`, #2577 `266d757f5`); FR-003/004 build ON the shipped #2573 gate, do not re-touch it. | Technical | Medium | Open |
| C-006 | Canonical sources & gates | Use canonical doctrine templates/CLI; new prose passes `tests/architectural/test_no_legacy_terminology.py`; no `# noqa`/`# type: ignore` to pass gates. | Technical | Medium | Open |

### Key Entities *(include if feature involves data)*

- **WP runtime frontmatter**: the dynamic fields (`shell_pid`, `shell_pid_created_at`, `base_branch`, `base_commit`) written into `tasks/WP##.md` by a claim; must be excludable from the uncommitted-artifact check (FR-001; #2093 lineage).
- **Analysis-report hash inputs**: the normalized digest of `spec.md`/`plan.md`/`tasks.md` used for freshness; the `tasks.md` normalizer must canonicalize pipe-table status cells, not only bullet checkboxes (FR-002).
- **Pre-review gate verdict**: the pass/fail/`no_coverage` outcome; must derive from a runner invoked via the resolved project interpreter and be contention-tolerant (FR-003/004).
- **`agent_profiles_manifest.json` entry**: per-profile record whose `output_path` must serialize repo-relative while the in-memory representation stays absolute (FR-006).
- **Issue-matrix approval blocker**: the operator-facing message that must name schema drift / offending column (FR-007).
- **Bulk-edit inference score**: the weighted keyword score whose low-weight refactor verbs must not push a non-bulk change over the blocking threshold (FR-008).

## Issue Matrix

| Item | Issue | Surface (verify at plan) | Verdict | Linkage |
|------|-------|--------------------------|---------|---------|
| Allocator blocks on its own runtime frontmatter write | #2570.1 | `cli/commands/implement.py` (uncommitted-artifact check + shell_pid write), `implement_cores.py` (`resolve_planning_artifact_staging`), `frontmatter.py::WP_FIELD_ORDER` | in-mission | Advances #2570; mirrors #2222; child of #2093 |
| 4th `shell_pid` writer bypasses claim/liveness | #2580 | `tasks_move_task.py::_mt_persist_wp_file` | in-mission (fold into IC-01) | Closes #2580; same self-write class as #2570.1 |
| `mark-status` `[D]`/`[P]` churn re-stales analysis-report | #2493.1 | `analysis_report.py` (`_normalize_tasks_md`), `tasks_materialization.py` (pipe-table writers) | in-mission | Advances #2493; extends #1764; closes-by #1862 |
| Pre-review gate uses wrong interpreter → spurious `--force` | #2570.3 | `review/pre_review_gate.py` (runner interpreter selection) | in-mission | Advances #2570; distinct from #2534 |
| Pre-review gate false timeout under lane contention | #2493.3 | `review/pre_review_gate.py`, `tasks_move_task.py::_mt_run_pre_review_gate` | in-mission | Advances #2493 |
| Sub-agent long-gate contract undefined | #2555.4 | doctrine/skill (`spk-run-implement-review`) | in-mission | Advances #2555 §4 |
| `upgrade` writes machine-absolute manifest paths | #2589 | `tool_surface/profiles/manifest.py`, `projection.py` (`_manifest_source_path` prior art) | in-mission | Closes #2589 |
| Issue-matrix "Missing rows" hides schema-drift column | #2555.5 | `agent/tasks_parsing_validation.py`, `review/_issue_matrix.py` | in-mission | Advances #2555 §5; family of #1738/#1742 |
| Bulk-edit inference trips on ordinary refactor verbs | #2555.3 | `bulk_edit/inference.py` | in-mission | Advances #2555 §3; distinct from #1257/#2229 |
| plan scaffold→block→rewrite→rerun on happy path | #2566 | `agent/mission_setup_plan.py` (plan side; specify already `scaffold_only: success`), new pristine predicate, consumers (source prompts + `next` engine switch) | in-mission | Closes #2566; child #2017 (root #846 closed) |
| move-task coord-lane recovery cascade (0-diff → 6 attempts) | #2555.1 | `tasks_move_task.py` staging via `coordination/commit_router.py` + `resolve_planning_artifact_staging` (NOT `commit_guard`) | in-mission (coordination-aware) | Advances #2555 §1; child #2160 — coord line #168/#2194/#2545 MERGED; coordinate #2596/#2598/#2300 |
| Solo PR-bound coord mission strands empty coord husk → split-brain fallback | #2533 | `coordination/surface_resolver.py` `resolve_status_surface_with_anchor` `CoordState.EMPTY` arm (READ surface only; NOT the derivation) | in-mission (consequence-only) | Advances #2533; child #2160; **derivation revisit = separate follow-up** (keeps #2581 `pr_bound⇒coord`) |
| Review-cycle canonical write | #2493.2 | — | **EXCLUDED — already shipped (verified)** | `create_rejected_review_cycle` on both reject legs |
| Coord/lane status placement + display | #2570.2/#2570.4/#2334/#2549A | — | **EXCLUDED — coord line (pin owners before merge)** | merged #168/#2194/#2545 |
| Issue-matrix gate-timing / first-approval scope-conflation | #2583 | — | **EXCLUDED — distinct approve-gate defect** | same file as FR-007; treat separately (fast-follow precedent) |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A 6-lane mission allocates all lanes with **zero** manual commits between allocations (was one per lane).
- **SC-002**: A full happy-path mission run (create→plan→N WP move-tasks) produces **zero** `--force` invocations forced by interpreter-selection, status-marker staleness, or lane-contention causes.
- **SC-003**: Running `spec-kitty upgrade` on a second machine/clone produces **zero** manifest diff (was 152 insertions / 34 deletions of pure path/schema churn).
- **SC-004**: The first `/spec-kitty.plan` (and `/spec-kitty.specify`) invocation on a clean mission returns a **non-blocked** result on the happy path — zero write-then-discard artifacts required to advance.
- **SC-005**: An operator facing a malformed issue-matrix column identifies the offending column **from the error message alone**, without reading validator source.
- **SC-006**: Full quality gate green; all guard true-positive regressions (NFR-005) pass; epics #2017 / #2093 / #2160 stay open with their children updated to reference this mission.

## Assumptions

- `uv` is the canonical dev toolchain for spec-kitty checkouts (per charter Tools), so `uv run` is the correct interpreter resolution with `sys.executable` as the documented fallback.
- The manifest reader can derive `project_root` from the manifest path (`<root>/.kittify/agent_profiles_manifest.json`), so no new configuration is needed for FR-006.
- The coord-authority in-flight work (draft `implement-loop-coord-authority-completion`) will land independently; FR-010 is scoped to the staging/recovery path only and is deliberately sequenced to avoid overlapping STATUS_STATE placement (C-002).
- Coverage/quality-gate deltas are indicative; new tests target the changed branches directly rather than padding for a number.
