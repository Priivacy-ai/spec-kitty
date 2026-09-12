# Mission Specification: Coord/primary partition-authority residuals — out-of-loop read+write routing

**Mission Branch**: `fix/partition-authority-residuals`
**Created**: 2026-08-15
**Status**: Draft
**Input**: Epic #2160 residuals. Verified by research mission `coord-primary-partition-residuals-01M01YTK`
(see its `research/synthesis.md` + `evidence-log.csv`), which confirmed the fold/defer set against
`upstream/main`.

## Context & Root Cause

Under coordination topology, Spec Kitty has one canonical partition authority —
`mission_runtime.artifacts` (`_PRIMARY_ARTIFACT_KINDS` / `_PLACEMENT_ARTIFACT_KINDS`, resolved via
`placement_seam(...).read_dir(<kind>)` / `artifact_home_for`, with **INV-5** read/write symmetry).
PLANNING/identity kinds (SPEC, TASKS_INDEX, WORK_PACKAGE_TASK, LANE_STATE, PRIMARY_METADATA) live on
PRIMARY; lifecycle kinds (STATUS_STATE, ISSUE_MATRIX, ACCEPTANCE_MATRIX, DECISION_LOG, REVIEW_CYCLE)
live on COORD. Mission #2160 closed the in-loop implement/review readers; #2214 closed the
parameter-passed cross-function arm; PR #3437 fixed `implement._resolve_lanes_dir` and recorded an
in-code C-009 deferral for the rest. **This mission finishes the residual out-of-loop / cross-function
callers** that still resolve the wrong surface — reading a PRIMARY kind off the `-coord` husk, or
writing PRIMARY/lifecycle evidence to the wrong partition — which degrades silently or deadlocks.

Every partition fix is a **caller reroute to the existing SSOT** — no predicate fork, no new legacy
resolver path, no partition-membership change.

**This mission spans two related scope areas** (operator-directed):

- **Scope A — Partition-authority residuals (epic #2160)** — US1–US6, the out-of-loop read/write
  routing folds.
- **Scope B — Mission-state discovery & diagnostic output fidelity (epic #2720)** — US7–US11, the
  adjacent read-surface/output-fidelity folds (false inventories, writer-schema drift, mission
  discovery anchored on the wrong root, false-Healthy over blanked slots, repair quarantining legacy
  transitions). These share this mission's read-surface theme; the fix pattern is *source diagnostics
  from the canonical writer schema and the canonical `kitty-specs/*` mission-instance discovery*,
  mirroring "route reads through the canonical seam."

**#2720 close-path** — completing Scope B (US7–US11: #2692, #2696, #2717, #2960, #3066) resolves all
of #2720's in-class fidelity children. Two #2720 children are **out of scope** and reparented out:
**#2704** (net-new cross-repo preparation infra → epic #1193) and **#2973** (net-new persisted
fault-event stream → observability home). #2754 is already fixed/closed. Once Scope B lands and the
two reparents are recorded, #2720 can close.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Coord mission with a rejected review can still merge (Priority: P1) — #2959

An operator runs a coord-topology mission; one WP takes a review rejection, is fixed, and re-approved.
Today the merge deadlocks: the `ReviewOverride` annotation is written to a PRIMARY-derived
`feature_dir` while the merge review-artifact gate reads the COORD `STATUS_STATE` home, so the
override the gate exists to consume is structurally unreachable — and `spec-kitty merge` offers no
override escape hatch. The mission becomes unmergeable.

**Why this priority**: This is a P0-class **merge deadlock** with no workaround — the highest-severity
item in the cluster.

**Independent Test**: On a multi-WP coord mission, drive a WP through for_review → (reject) → fix →
approve → `merge`; assert the merge succeeds and the override is honored. Separately assert the new
`merge --skip-review-artifact-check --note "<reason>"` escape hatch merges and records evidence.

**Acceptance Scenarios**:

1. **Given** a coord mission whose WP recorded a review rejection then re-approval, **When**
   `_persist_review_artifact_override` runs, **Then** it is **changed at the caller** to resolve the
   coord `STATUS_STATE` surface via `placement_seam(...).read_dir(STATUS_STATE)` and pass that dir into
   the generic `emit_inner_state_changed` (which stays partition-agnostic — no edit to the shared
   function), landing on the same surface `review_artifact_consistency.py` reads, and `merge` proceeds
   without a deadlock. *(Follows the proven per-leg reroute pattern in `tasks_dependency_graph.py:120-135`.)*
2. **Given** a coord mission the gate still refuses, **When** the operator runs
   `merge --skip-review-artifact-check --note "<reason>"`, **Then** the merge completes and the
   override/skip is recorded as evidence (parity with `move-task`).

---

### User Story 2 - Merge risk & dependency gates evaluate real data on coord missions (Priority: P1) — #3439

The merge risk gate and dependency gate (and the bulk-edit diff base) read `lanes.json` / `tasks/`
directly off the coord `feature_dir`. On a coord mission those PRIMARY kinds are absent on the husk,
so the risk gate silently **SKIPs** and the dependency gate sees an **empty graph** (dependencies
falsely satisfied) — gates that exist to protect the merge quietly do nothing.

**Why this priority**: Silent safety-gate degradation at merge time; same module/locus as US1, so
they must be fixed in one coherent pass.

**Independent Test**: On a coord mission with a real risk-flagged WP and a real dependency edge, run
the merge preflight; assert the risk gate fires (not SKIP) and the dependency gate sees the true
graph.

**Acceptance Scenarios**:

1. **Given** a coord mission with `lanes.json`, **When** `_evaluate_risk_gate` runs, **Then** it
   resolves LANE_STATE via `placement_seam(...).read_dir(LANE_STATE)` and evaluates real data
   (no false SKIP).
2. **Given** a coord mission with dependency edges, **When** `_evaluate_dependency_gate` runs,
   **Then** it resolves WORK_PACKAGE_TASK via the seam (real graph) while keeping the STATUS_STATE
   event read on coord.
3. **Given** a coord mission bulk edit, **When** `_enforce_bulk_edit_diff_compliance` computes its
   base ref, **Then** it resolves `lanes.json` via the seam (no silent fallback to `target_branch`).
4. **Given** the in-code C-009 deferral at `tasks_dependency_graph.py:132`, **When** this mission
   lands, **Then** the pin is lifted and the note removed.

---

### User Story 3 - Review handoff shows real per-WP lane state on coord missions (Priority: P2) — #2698

The generated review handoff embeds work-package topology whose per-WP lane is read from the PRIMARY
`LANE_STATE` dir instead of the coord-aware `STATUS_STATE` surface. On a multi-WP coord mission every
WP renders back as stale `planned`, misleading the reviewer.

**Why this priority**: Correctness/UX defect on the review path; localized. (The cited fix PR #2766
was closed and never merged, so main is still broken.)

**Independent Test**: On a multi-WP coord mission with WPs in mixed lanes, generate the review
handoff; assert the rendered per-WP statuses match the coord `STATUS_STATE`, not `planned`.

**Acceptance Scenarios**:

1. **Given** a coord mission with a WP in `in_progress`, **When** `worktree_topology` renders the
   handoff, **Then** the per-WP lane is resolved via the coord-aware STATUS_STATE surface while
   identity/lanes/tasks continue to resolve from the PRIMARY dir.

---

### User Story 4 - move-task leaves a clean tree after a rejected review (Priority: P2) — #2939

After a rejected-review transition, the post-transition `InnerStateChanged` annotation (subtask
reset / claim release / note) is written and materialized to the correct coord surface but **never
committed**, leaving `status.events.jsonl` / `status.json` dirty when `move-task` returns.

**Why this priority**: Durability asymmetry (write-not-committed) that dirties the tree; shares the
`emit_inner_state_changed` locus with US1, so coordinate the two.

**Independent Test**: On a coord mission, reject a WP review; assert `move-task` returns with a clean
git tree (the annotation is committed atomically with the transition).

**Acceptance Scenarios**:

1. **Given** a rejected-review `move-task`, **When** the post-transition annotation is emitted,
   **Then** it is gathered into the same bookkeeping transaction (or a second atomic status commit)
   so no dirty status file remains.

---

### User Story 5 - The 4th write-target sibling routes through the shared helper (Priority: P2) — #2966 (part-2)

Three of four write-target committers route through the shared `resolve_write_target_or_degrade`
(with its pre-gate + caught-set); the 4th — `safe_commit_cmd._resolve_mission_aware_target` — still
calls `mission_runtime.resolve_placement_only` directly, an inconsistency in the write-target
contract.

**Why this priority**: Self-contained consolidation that aligns the last committer with its siblings;
cheap, no new behavior.

**Independent Test**: Unit-test `_resolve_mission_aware_target` routes through
`resolve_write_target_or_degrade` with the same caught-set/pre-gate as the three siblings.

**Acceptance Scenarios**:

1. **Given** a mission-aware safe commit, **When** `_resolve_mission_aware_target` resolves its
   target, **Then** it uses `resolve_write_target_or_degrade` (parity with
   `status_transition.py`, `decision_log.py`, `bookkeeping_commit.py`) **while preserving the existing
   refusal contract** — `CONSOLIDATED_CONTENT_ABSENT` still raises `MissionAwareCommitRefused`, and
   benign `FileNotFoundError`/`ValueError` still degrade to the `None` fallback (assert refusal-parity,
   not just that the helper is called).

---

### User Story 6 - finalize checkpoints wps.yaml (Priority: P3) — #2937 *(gated on C-004)*

`finalize-tasks` reads `wps.yaml` (regenerating `tasks.md` from it) but never commits it, so the
"finalized" checkpoint cannot reproduce its own state (INV-5 broken for `wps.yaml`).

**Why this priority**: Real omission but lowest severity, and it depends on an operator ruling
(C-004) on whether `wps.yaml` should be versioned at all.

**Independent Test**: After the ruling, if `wps.yaml` is versioned: run finalize on a mission with a
`wps.yaml`; assert it is committed to the PRIMARY surface and the tree is clean.

**Acceptance Scenarios**:

1. **Given** the C-004 ruling that `wps.yaml` is versioned, **When** finalize runs, **Then**
   `feature_dir/"wps.yaml"` is added to `_collect_finalize_artifacts` and routed to the PRIMARY leg
   (a `wps.yaml → TASKS_INDEX` classifier entry).

---

### User Story 7 - check-prerequisites reports a truthful planning-artifact inventory (Priority: P2) — #2692

`check-prerequisites` inventories only `spec.md` / `plan.md` / `tasks.md` (hardcoded), omitting
`research.md`, `data-model.md`, `quickstart.md`, `contracts/`, `traces/` that mission writers
actually produce — and its `research_dir` carries wrong file-vs-dir semantics. Operators and agents
reading readiness see a false inventory.

**Why this priority**: Read-only readiness command emitting a false inventory; agents trust it before
acting. (Scope B / epic #2720.)

**Independent Test**: On a mission whose writer produced `research.md` + `data-model.md`, run
`check-prerequisites --json`; assert the inventory includes them (sourced from the mission `artifacts`
metadata, not a hardcoded list).

**Acceptance Scenarios**:

1. **Given** a mission with non-core planning artifacts present, **When** `validate_feature_structure`
   builds `available_docs`, **Then** the inventory is derived from the canonical mission writer
   metadata (mission.yaml `artifacts`), and the two behavior-locking assertions in
   `tests/git_ops/test_worktree.py:465,487` are updated to the truthful inventory.

---

### User Story 8 - Mission doctors validate against the canonical writer schema and scope to one mission (Priority: P2) — #2696

`doctor` flags writer-canonical `meta.json` keys (`coordination_branch`, `topology`, `flattened`,
`pr_bound`) as `UNKNOWN_SHAPE` because the audit key registry is a hand-rolled frozenset that drifted
from the writer TypedDicts; and `doctor coordination` cannot scope to a single mission.

**Why this priority**: False schema findings + missing per-mission scoping undermine trust in the
diagnostic surface. (Scope B / epic #2720.)

**Independent Test**: Run the meta audit on a coord mission; assert zero false `UNKNOWN_SHAPE` on
writer keys. Run `doctor coordination --mission <handle>`; assert it scopes to one mission.

**Acceptance Scenarios**:

1. **Given** a coord mission `meta.json`, **When** the shape audit runs, **Then** the known-key set is
   derived from the canonical writer schema (`MissionMetaRequired` + `MissionMetaOptional` +
   coordination-written keys), with a regression test asserting every writer key is a known audit key.
2. **Given** many missions, **When** `doctor coordination --mission <handle>` runs, **Then** it filters
   through the same resolver as `mission-state` (MissionNotFound / AmbiguousHandle parity).

---

### User Story 9 - Diagnostics discover missions under the canonical kitty-specs root (Priority: P2) — #2717

`retrospect summary` anchors mission discovery on `.kittify/missions/` (a support/registry root)
instead of `kitty-specs/*` where records live, so it scans support modules as missions and omits the
real retrospective record — producing false missing counts.

**Why this priority**: False aggregate cross-mission counts; the record reader already relocated but
discovery didn't. (Scope B / epic #2720.)

**Independent Test**: With a mission carrying a real `retrospective.yaml` under `kitty-specs/*`, run
`retrospect summary`; assert the real record is found and support dirs are not counted as missions.

**Acceptance Scenarios**:

1. **Given** the two discovery sites (`summary.py:296-303`, `retrospect.py:1003-1005`), **When**
   discovery runs, **Then** both route through a single canonical `kitty-specs/*` mission-instance
   iterator (excluding `.kittify` support dirs) so fixing one does not leave the other empty.

---

### User Story 10 - status doctor must not report Healthy over blanked runtime attribution (Priority: P2) — #2960

An annotation with `agent: ""` silently blanks recorded agent attribution because the reducer guards
`is not None` rather than truthiness, so `""` clobbers a real value; `status doctor` then reports
Healthy over the corrupt state. Operators trust a false "Healthy".

**Why this priority**: A read-only diagnostic emitting a false "Healthy" over corrupt canonical state
— #2720's exact charter. (Scope B / epic #2720.)

**Independent Test**: Fold an `agent: ""` delta over `agent: "claude"`; assert the real value survives
(write-boundary normalization) and that `status doctor` flags the empty slot rather than reporting
Healthy.

**Acceptance Scenarios**:

1. **Given** an annotation carrying `agent: ""`, **When** the reducer folds it (`reducer.py:262-264`
   replace-slot and `:185` claim arm), **Then** the empty string is treated as no-op (truthiness/
   `""`→`None` normalization at the `WPInnerStateDelta` write boundary), so prior attribution survives.
2. **Given** a WP with a blanked runtime slot, **When** `status doctor` runs, **Then** a check flags it
   (no false Healthy), with a regression test pinning `agent:""`-over-`agent:"claude"` survival.

---

### User Story 11 - mission-state repair must not quarantine legacy WPStatusChanged transitions (Priority: P1) — #3066

`doctor mission-state --fix` quarantines legacy `WPStatusChanged` lane-transition rows (the repair
classifier's `_is_preserved_non_lane_row` omits `WPStatusChanged`, contradicting the mission's own
`WPStatusChanged` writer), so a **mutating** repair regenerates `status.json` with zero WPs — it
destroys runnable state.

**Why this priority**: **P1 / data-destroying** — a repair that wipes lane history is more severe than
a false read-only report. The classifier ignores the canonical mission *writer* schema (#2720's exact
remedy pattern). An existing PR (#3067) carries the fix but is stale (462 behind, CI-red).

**Independent Test**: Run the repair classifier over an event log containing a legacy
`WPStatusChanged` row with `wp_id`/`from_lane`/`to_lane`; assert it is preserved (passthrough), not
quarantined, and `status.json` retains the WPs.

**Acceptance Scenarios**:

1. **Given** a legacy `WPStatusChanged` row (with `wp_id`/`from_lane`/`to_lane`), **When**
   `_rule_reject_non_status_event` runs, **Then** a `_is_legacy_typed_lane_transition` passthrough at
   the head of the rule preserves it (adopting PR #3067's diff), while TeamSpace-envelope and
   `DecisionPointOpened` rows stay quarantined. Red-first migration test included.

---

### Edge Cases

- **Non-coord missions** (SINGLE_BRANCH / LANES route everything to PRIMARY): every fix MUST be a
  no-op there — status/lanes/tasks already resolve to PRIMARY, so the reroutes must not change
  behavior. Tests MUST include a non-coord control.
- **Single-lane coord missions**: US2/US3 may not manifest without multiple WPs / stacking; tests
  MUST use multi-WP coord missions.
- **Deleted or unregistered coord worktree**: `canonicalize_feature_dir` rewrites an unregistered
  coord path back to PRIMARY — tests MUST register the coord worktree so the STATUS_STATE surface is
  the coord branch, not the primary checkout.
- **Shared loci**: US1+US2 share `merge_gates.py` / the merge review-artifact gate family; US1+US4
  share `emit_inner_state_changed` (`emit.py:971-1041`). Land shared-locus changes coherently to
  avoid divergent per-leg resolution.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Reroute review-override write to coord STATUS_STATE | US1 (#2959) | High | Open |
| FR-002 | Add `merge --skip-review-artifact-check`/`--note` escape hatch (parity w/ move-task) | US1 (#2959) | High | Open |
| FR-003 | Merge risk + dependency gates resolve LANE_STATE/WORK_PACKAGE_TASK via seam; STATUS_STATE stays coord | US2 (#3439) | High | Open |
| FR-004 | Bulk-edit diff base resolves lanes.json via seam (no silent target_branch fallback) | US2 (#3439) | High | Open |
| FR-005 | Lift the C-009 pin at `tasks_dependency_graph.py:132` | US2 (#3439) | High | Open |
| FR-006 | Review handoff resolves per-WP lane via coord-aware STATUS_STATE surface | US3 (#2698) | Medium | Open |
| FR-007 | Commit post-transition InnerStateChanged annotation atomically (no dirty tree) | US4 (#2939) | Medium | Open |
| FR-008 | Route `safe_commit_cmd._resolve_mission_aware_target` through `resolve_write_target_or_degrade` | US5 (#2966 p2) | Medium | Open |
| FR-009 | finalize commits `wps.yaml` to PRIMARY (C-004 ruling resolved in-mission) | US6 (#2937) | Low | Open |
| FR-010 | check-prerequisites inventory sourced from canonical mission writer metadata (not hardcoded); fix `research_dir` semantics | US7 (#2692) | Medium | Open |
| FR-011 | Audit shape registry for `meta.json` derived from canonical writer schema (no drift) + regression test | US8 (#2696) | Medium | Open |
| FR-012 | Add `--mission` selector to `doctor coordination` (resolver parity with mission-state) | US8 (#2696) | Medium | Open |
| FR-013 | Route both diagnostic discovery sites through one canonical `kitty-specs/*` instance iterator | US9 (#2717) | Medium | Open |
| FR-014 | Reducer treats empty-string replace-slots as no-op (`""`→`None` at write boundary) + doctor check for blanked slots | US10 (#2960) | Medium | Open |
| FR-015 | mission-state repair passthrough for legacy `WPStatusChanged` transitions (adopt PR #3067) | US11 (#3066) | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Live coord e2e per fix (Scope A) | Each of FR-001…FR-008 carries a coord-topology end-to-end test (create→finalize→implement→review→merge as applicable) that is **red before, green after** the fix. Unit reads alone are insufficient (the #3437 straggler lesson). **Scope B (FR-010…FR-013) and FR-009 are intentionally OUTSIDE this coord-e2e set** — Scope B is topology-agnostic (guarded by NFR-004 instead); FR-009 is a finalize/commit-set change. This omission is deliberate, not a coverage gap. | Reliability | High | Open |
| NFR-002 | No regression of closed arms | Placement-stability guard (#2198) and in-loop routing (#2160/#2214) stay green; zero STATUS-partition reads over-corrected to PRIMARY. | Reliability | High | Open |
| NFR-003 | Clean static gates | New code passes `ruff` + `mypy` with zero issues; cyclomatic complexity ≤15; no new `# noqa`/`# type: ignore`/per-file ignores. | Maintainability | High | Open |
| NFR-004 | Scope-B fidelity guarded by regression tests | FR-010/FR-011/FR-013 derive from a single canonical source (writer metadata / `kitty-specs/*` iterator), each with a regression test that goes red if the source re-drifts (no two-copy trap). FR-014 (`agent:""` survival) and FR-015 (legacy `WPStatusChanged` passthrough) each carry a red-first regression/migration test. Scope B is topology-agnostic — these guards, not NFR-001's coord-e2e, are its safety net. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | SSOT is `mission_runtime.artifacts` | All fixes are caller reroutes to the existing predicate; never fork the predicate or add a legacy resolver path. No partition-membership change is expected; if one is ever required, flip it in the SSOT only. | Technical | High | Open |
| C-002 | Do not over-correct | STATUS-partition reads (status.events.jsonl, matrices) stay on COORD; only PRIMARY-kind reads move back to PRIMARY and mis-partitioned writes align. | Technical | High | Open |
| C-003 | Second-order gates stay green | cutover-guard (mission `status_phase`), diff-coverage critical-paths, compat-surface superset, and completeness baselines must remain green. | Technical | High | Open |
| C-004 | `wps.yaml` lifecycle ruling (D-001) | FR-009 needs a ruling: commit `wps.yaml` (operator-authored planning input) vs explicitly document it as non-versioned. Resolve this **within the mission** (Decision Moment D-001 during plan/tasks); it does not drop FR-009 from scope. | Business | Medium | Open |
| C-005 | Canonical discovery/schema sources (Scope B) | Scope B fixes MUST consume the canonical mission writer schema and a single canonical `kitty-specs/*` mission-instance discovery helper — no hand-rolled key set, no ad-hoc discovery glob, no second copy. Same design PRINCIPLE as C-001 (derive from a canonical source) but applied to DIFFERENT, multiple canonical sources (mission `artifacts` metadata; `MissionMeta*` TypedDicts; a `kitty-specs/*` iterator) in DIFFERENT modules — NOT the single `mission_runtime.artifacts` SSOT, and does not share Scope A's seam. | Technical | High | Open |
| C-007 | Scope-A/Scope-B WP separability | No single WP/lane may mix a Scope-A partition reroute with a Scope-B schema/discovery fix — disjoint modules, different canonical sources, different test families (NFR-001 coord-e2e vs NFR-004 schema-drift guards). Decompose into separate WPs. | Technical | High | Open |

### Key Entities

- **Partition kinds**: LANE_STATE, WORK_PACKAGE_TASK, TASKS_INDEX (PRIMARY); STATUS_STATE,
  REVIEW_CYCLE, DECISION_LOG (COORD) — membership owned by `mission_runtime.artifacts`.
- **Placement seam**: `placement_seam(root, mission_slug).read_dir(<kind>)` / `artifact_home_for` —
  the single kind-aware resolver both reads and writes must go through (INV-5).
- **Merge review-artifact gate family**: `merge_gates.py`, `merge/preflight.py`, `merge/forecast.py`,
  `post_merge/review_artifact_consistency.py` — the shared locus of US1 + US2.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A multi-WP coord mission that took a review rejection can be merged (override honored),
  and the `merge` escape hatch merges with recorded evidence — the #2959 deadlock is eliminated
  (proven by e2e).
- **SC-002**: On a coord mission, the merge risk and dependency gates evaluate real `lanes.json` /
  `tasks/` (no SKIP, no empty graph); the bulk-edit diff base resolves a real base ref (proven by e2e).
- **SC-003**: The review handoff on a multi-WP coord mission renders true per-WP lane states, never a
  blanket stale `planned`.
- **SC-004**: `move-task` (rejected review) and `finalize` return with a clean git tree on coord
  missions — no uncommitted status or `wps.yaml` residue.
- **SC-005**: The full targeted test suite and `tests/architectural/` guards are green; a guard test
  asserts no predicate fork / no new legacy resolver path was introduced; non-coord missions show
  identical behavior (control).
- **SC-006** *(Scope B)*: `check-prerequisites` reports the true planning-artifact inventory, and the
  meta audit raises zero false `UNKNOWN_SHAPE` on writer-canonical keys — both proven by tests that
  fail if the writer schema drifts again.
- **SC-007** *(Scope B)*: `retrospect summary` (and the per-mission table) find real records under
  `kitty-specs/*` and never count `.kittify` support dirs as missions; `doctor coordination` scopes to
  a single mission via `--mission`.
- **SC-008** *(Scope B)*: an `agent: ""` annotation never blanks recorded attribution, and `status
  doctor` flags a blanked slot instead of reporting Healthy (#2960).
- **SC-009** *(Scope B)*: `doctor mission-state --fix` preserves legacy `WPStatusChanged` lane
  transitions (no zero-WP `status.json` regeneration) (#3066).
- **SC-010**: #2720 is closable — all its in-class fidelity children (#2692, #2696, #2717, #2960,
  #3066) are resolved and its out-of-class children (#2704, #2973) are reparented out.

## Out of Scope / Deferred (with rationale)

- **#3071** — the write-seam *adoption* residual is blocked on a **different** lift than this mission
  performs (#2160 write-authority unification + the literal-ref unification guard); its `status/emit.py`
  port fully overlaps #2966 part-3 and should be consolidated and spec'd there. The functional
  wrong-surface defect it named is already fixed by #3437.
- **#2739** — the partition slice is already fixed (#2090); the live residuals are CLI-hint text,
  result-schema, and create-guardrail concerns — a separate governed spec-commit UX bundle
  (#2740/#2745), not this SSOT seam.
- **#2966 part-3 (emit.py port)** → consolidate under #3071. **#2966 part-4** (retrospective schema
  field) → separate small addition.
- **#3433** — an additive `status doctor` reconciliation (event-log WP set vs `tasks/`). It is a
  *detector*, not a read/write seam-symmetry fix, and INV-5 already holds for the kinds involved.
  **Deferred** to keep this mission scoped to routing symmetry; recommend a follow-up if the operator
  wants the detection half (it is cheap and would reuse this mission's seam primitives).
- **#2704** (#2720 child) — reparented out of #2720 to epic #1193 (program-orchestration /
  multi-repo-preparation); out of this mission's scope.
- **#2973** (#2720 child) — reparented out of #2720 to an observability / fault-event home (net-new
  persisted diagnostic stream, gated on an event-schema/shared-package-boundary decision); out of scope.
- **#2754** (#2720 child) — already fixed and closed (PR #2754); no action.

## Decisions (resolve during plan/tasks)

- **D-001** (#2937 / C-004): Is `wps.yaml` a versioned artifact (commit it in finalize) or an
  operator-authored non-versioned input (document + skip)? Default lean: version it (FR-009 as written).

## Traceability

| FR | Issue | Primary loci (verified on main) |
|----|-------|--------------------------------|
| FR-001 | #2959 | `tasks_materialization.py:78-90` (`_persist_review_artifact_override`), `emit.py:971-1041` |
| FR-002 | #2959 | `cli/commands/merge.py:420-446`; pattern from `tasks_transition_core.py:414-418` |
| FR-003 | #3439 | `policy/merge_gates.py:86/194/242` |
| FR-004 | #3439 | `cli/commands/agent/workflow.py:202` |
| FR-005 | #3439 | `cli/commands/agent/tasks_dependency_graph.py:132` |
| FR-006 | #2698 | `core/worktree_topology.py:147-149/207`, `status/lane_reader.py:51-76` |
| FR-007 | #2939 | `tasks_move_task.py:2190-2318`, `emit.py:971-1041` |
| FR-008 | #2966 | `cli/commands/safe_commit_cmd.py:278-307` |
| FR-009 | #2937 | `cli/commands/agent/mission_finalize.py:187-216/449-461` |
| FR-010 | #2692 | `core/worktree.py:661-706/718-721`; tests `git_ops/test_worktree.py:465,487` |
| FR-011 | #2696 | `audit/shape_registry.py:31-47/299-314`, `audit/classifiers/meta.py:110`; schema `mission_metadata.py:47-87` |
| FR-012 | #2696 | `cli/commands/doctor.py:1258` (`coordination_health`); pattern at `doctor.py:1022` |
| FR-013 | #2717 | `retrospective/summary.py:296-303`, `cli/commands/retrospect.py:1003-1005` |
| FR-014 | #2960 | `status/reducer.py:262-264/185`, `status/models.py:460+` (`WPInnerStateDelta`), `status/doctor.py` |
| FR-015 | #3066 | `migration/mission_state.py:1583-1667` (`_rule_reject_non_status_event`); adopt PR #3067 |
