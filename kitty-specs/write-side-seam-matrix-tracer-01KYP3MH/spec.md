# Mission Specification: Write-Side Seam: Matrix & Tracer Writers

**Mission Branch**: `feat/write-side-seam-matrix-tracer`
**Created**: 2026-07-29
**Status**: Draft
**Input**: Follow-up to PR #3060 (read-side placement-seam closure, **MERGED** `e6806f184`). Close the write/gate side of the same seam so consumer missions stop losing matrix and tracer state and stop burning inference to hand-edit matrices.

> **Pre-planning note (2026-07-29):** A profile-loaded squad (paula/architect/priti) surveyed the code post-#3060-merge. Findings and the full change rationale live in [`pre-planning-ledger.md`](./pre-planning-ledger.md). Headline: this is an **adoption** mission (route existing writers/call-sites through the existing write seam), not a construction mission. This spec has been corrected accordingly.

## Context & Motivation *(informative)*

PR #3060 unified the **read** side of the artifact placement seam and deleted the `primary_feature_dir_for_mission` wrapper. Crucially, the squad confirmed the **write** seam already exists and predates the read side: `PlacementSeam.write_target(kind)` (`src/mission_runtime/resolution.py:1430`) → `resolve_placement_only(...)`, landed in ADR `2026-06-24-1`, which **explicitly rejects building a second, write-only resolver (C-006)**. #3060 caught the *read* side up to that write seam; this mission catches the *write call sites* up — an **adoption**, not a build.

Three consumer-facing pains all trace to the write side of the seam not being uniformly **adopted** (~80 seam-routed reads vs ~3 seam-routed writes today):

1. **Matrix edits are inference-heavy.** No *command* fronts the acceptance-matrix writer, so an agent reads product source to learn the file shape, computed fields, and negative-invariant semantics, then hand-edits JSON — burning tokens and getting it wrong.
2. **Lanes cannot cleanly record findings.** `TRACER_FILE` is classified coord-partition but has **only a reader, no writer**; agents append into the lane worktree's `kitty-specs/`, which the lane guards warn-then-block.
3. **Consolidation drops writes.** Execution lanes are branched off a base minted *before* planning artifacts exist, so lane writes have no common ancestor with the consolidation base and are silently reverted at merge.

The unifying move: **deterministic write commands (and converged call sites) that route lane-origin writes to the correct partition surface through the existing `write_target`/`commit_for_mission` seam** — the same way status transitions already materialize lane-origin events to the coord surface. Agents stop hand-committing artifacts; the seam owns placement.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Record an acceptance-matrix verdict with one deterministic command (Priority: P1)

An implementing or reviewing agent has just finished verifying a work package. It needs to record the outcome in the acceptance-matrix (per requirement / Definition-of-Done). Today it reads product source to reconstruct the file shape and hand-edits JSON. In the target state it runs a single command that sets the verdict; the command fronts the existing writer, owns the destination surface and commit, and keeps the *computed* verdict authoritative.

**Why this priority**: This is the headline token-burn the mission targets and the most self-contained, live-witnessed win (#2318). It delivers value even if nothing else ships.

**Independent Test**: On a mission with a scaffolded acceptance-matrix, run the verdict command for one row and assert the row is updated, computed/derived fields are recomputed, negative-invariant provenance is preserved, and the agent read zero product-source files to do it.

**Acceptance Scenarios**:

1. **Given** a scaffolded acceptance-matrix row in `unknown`/`pending`, **When** the agent runs the acceptance-verdict command with a result and verification method, **Then** the row is updated deterministically, derived fields are recomputed, the file validates against its negative-invariant shape, and the write lands on the surface `write_target(ACCEPTANCE_MATRIX)` dictates.
2. **Given** an acceptance-matrix with recorded negative-invariant provenance, **When** the command writes a verdict, **Then** it materializes/routes the write without re-authoring the computed verdict semantics or stamping over existing invariant provenance.
3. **Given** a verdict already recorded, **When** the same command is re-run with identical inputs, **Then** it is a no-op (no duplicate row, no error).

---

### User Story 2 - Capture a finding on a lane without blocking the lane (Priority: P1)

An agent implementing a work package on a lane worktree discovers a tooling-friction, approach, or design-decision note worth retaining. It needs to record that finding during implementation. Today it cannot: `TRACER_FILE` has no writer, and appending into the lane worktree trips the warn-then-block guards. In the target state a single command appends a dated, attributed finding entry that is **routed to the mission's coordination surface** via the same materialization authority status transitions use, leaving the lane branch unblocked and clean.

**Why this priority**: Formalizing the lane-writable findings capture is a primary ask, and without it tracer files remain unusable on-lane (#2980/#2549).

**Independent Test**: From a lane worktree, run the finding-append command; assert the entry appears on the coordination surface, the lane branch has no new `kitty-specs/` commit, and a subsequent `move-task` on that lane is not blocked by the finding.

**Acceptance Scenarios**:

1. **Given** an agent on a lane worktree, **When** it appends a finding via the command, **Then** the entry is recorded on the coordination surface and no `kitty-specs/` artifact is committed to the lane branch.
2. **Given** a finding recorded from a lane, **When** the lane later runs a status transition (`move-task`), **Then** the transition is not blocked by a `kitty-specs/` divergence.
3. **Given** the same finding content submitted twice, **When** the append command runs again, **Then** no duplicate entry is created.

---

### User Story 3 - Writes land on the right surface and survive consolidation (Priority: P2)

A mission operator consolidates several lanes. Matrix verdicts, tracer findings, and status recorded during implementation must all still be present and correct after the merge — not reverted, not clobbered by a stale copy on another partition.

**Why this priority**: This is the durability guarantee that makes Stories 1 and 2 trustworthy; it depends on lanes sharing a common ancestor with the consolidation base (the #2993 P0).

**Independent Test**: Run a representative multi-lane mission that records matrix and tracer writes during implementation, then consolidate; assert every recorded write is present and correct on the consolidated branch with zero silent reversions.

**Acceptance Scenarios**:

1. **Given** an execution lane created at implement time, **When** the lane is created, **Then** its worktree branches from the planning-artifact commit so it shares a common ancestor with the consolidation base.
2. **Given** matrix/tracer writes recorded on a lane during implementation, **When** the mission consolidates, **Then** those writes are present on the consolidated branch and not reverted.
3. **Given** a stale matrix copy on a non-authoritative partition, **When** a fresher verdict is written, **Then** the write reconciles (via the artifact's dedicated merge driver) rather than being overwritten by the stale copy.

### Edge Cases

- **Coordination surface missing** (worktree/branch removed): a lane finding or matrix write returns a structured, actionable error rather than crashing or writing partially.
- **Target surface absent post-merge** (deleted `target_branch`): the routing **degrades gracefully** with a structured, recoverable result rather than hard-failing. The real post-merge write mode is fast-follow #3033 (out of scope, see C-006).
- **Unknown target**: a verdict or finding command for an unknown work package returns an actionable error, not a silent no-write.
- **Concurrent cross-lane writes** to the same coordination artifact reconcile via that artifact's **dedicated** merge driver (`spec-kitty-acceptance-matrix` / `-issue-matrix` / `-traces` / `-event-log`) — no clobber.
- **Coord-authority gate**: routing a COORD write must satisfy the coord-authority resolution gate; teaching that gate the seam idiom is in scope (FR-010), not a bypass allow-list.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Deterministic acceptance-matrix verdict command | As an implementing/reviewing agent, I want a single command that fronts the existing acceptance-matrix writer, routes through `write_target(ACCEPTANCE_MATRIX)`, and keeps the computed verdict + negative-invariant provenance authoritative, so I never read product source or hand-edit JSON. | High | Open |
| FR-002 | Issue-matrix writes route through the write-side seam (placement only) | As a maintainer, I want issue-matrix writes to resolve their COORD surface through the seam (reusing the existing single-file scaffold), so issue-matrix artifacts are never stranded on the wrong partition. The deterministic issue-matrix **verdict command** and **multi-file reference discovery** (#2583/#1738) are DEFERRED to the WP-metadata authority slice (#2093/#2400). | Medium | Open |
| FR-003 | Lane findings (tracer) append command routed to coordination surface | As an agent on a lane, I want to append a dated, attributed finding that is routed to the mission's coordination surface (via the status-transition materialization authority) without committing to the lane branch, so findings are captured without blocking the lane. | High | Open |
| FR-004 | Adopt the write-side seam across bypassing call sites | As a maintainer, I want the measured direct-caller write bypasses (~12 across 8 modules, per the placement-seam census) converged onto `write_target`/`commit_for_mission` — **extending** the existing write seam, never building a new resolver — so no call site hand-derives a write destination. Includes folding the already-isolated implement-claim write-partition split (#2663). | High | Open |
| FR-005 | Lane branches from the planning-artifact commit (common ancestor) | As an operator, I want an execution lane's worktree to branch from the planning-artifact commit so that matrix/tracer/planning writes share a common ancestor with the consolidation base and are not reverted at merge. **This is a P0 structural git-topology change (#2993), ADR-gated (see C-007), bundled in this mission's core but reviewed as its own WP with explicit merge/ancestor tests.** | High | Open |
| FR-006 | Matrix/tracer write reconciles, never clobbers a fresher cross-partition copy | As an operator, I want a matrix/tracer write to reconcile with a fresher copy on the authoritative surface (via the artifact's dedicated merge driver) rather than overwrite it, so stale partition residue cannot destroy a newer verdict (#2482). | Medium | Open |
| FR-007 | Idempotent, re-runnable writes | As an agent, I want re-running any verdict or finding command with identical inputs to be a no-op, so retries never create duplicate rows or entries. | Medium | Open |
| FR-008 | Structured machine-readable command results | As an orchestrator, I want each write command to emit structured output naming the resulting row/entry and destination surface, so I can consume the result without parsing prose. | Medium | Open |
| FR-009 | Graceful degrade + actionable errors on unroutable writes | As an agent, I want a write that cannot be routed (missing coordination surface, deleted `target_branch`, unknown target) to degrade gracefully with a structured, recoverable result — never a silent partial write or an uncaught crash — so I can recover deterministically. | Medium | Open |
| FR-010 | Teach the coord-authority gate the write-side seam idiom | As a maintainer, I want the coord-authority resolution gate to recognize the `write_target(<COORD kind>)` idiom (routing `decisions/emit.py` off the allow-list), so routing tracer/matrix COORD writes is not blocked by the gate. Enabler that unblocks FR-001/FR-003 (folds #3055). | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Zero-inference writes | A matrix or tracer write requires zero product-source reads by the agent: the documented workflow is fully specified by CLI arguments and current mission state (0 "read module X to learn the shape" steps). | Usability | High | Open |
| NFR-002 | Responsive commands | Each write command completes in under 3 seconds (p95) on a representative mission, so it never reads as a hang. | Performance | Medium | Open |
| NFR-003 | Lane-safe and idempotent | Running any write command from a lane leaves zero `kitty-specs/` commits on the lane branch and no blocked/dirty state; re-running any command is a no-op. | Reliability | High | Open |
| NFR-004 | Coverage and complexity | Every new command branch, converged call site, and the seam write path has focused unit tests executed directly; no new or modified function exceeds cyclomatic complexity 15. | Maintainability | High | Open |
| NFR-005 | No regression of shipped invariants | The read-side seam census (`test_no_read_side_bypass.py`), the C-008 architectural gates, and the coord-authority gate (`test_resolution_authority_gates.py`) remain green; event-log status remains the sole authority for lane state. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Extend the seam, never allow-list a bypass | The write path MUST reuse/extend `write_target`/`commit_for_mission`. Adding a per-command exception to the `kitty-specs/` guards, or hand-deriving a destination, is prohibited (ADR `2026-06-24-1` C-006: no parallel write resolver). | Technical | High | Open |
| C-002 | Tracer classification unchanged | `TRACER_FILE` remains coord-partition. This mission does NOT reclassify it. Lane findings reach the coordination surface via routing, not via lane-branch commits. | Technical | High | Open |
| C-003 | Do not rebuild the status engine | Status transitions are already deterministic (event-log is the sole authority). This mission only routes status writes through the seam and adds the acceptance-matrix + tracer writers — it does not re-implement transition logic (coordinate with #2966). | Technical | High | Open |
| C-004 | Terminology canon | New command names, flags, and prose use canonical Mission terminology; no `feature*` aliases and no new overloaded uses of `primary`/`merge`/`routing` without naming the sense. | Business | Medium | Open |
| C-005 | Built on merged PR #3060 | Coord topology; consolidates into `feat/write-side-seam-matrix-tracer`; PR into `upstream/main` post-consolidation. Rebased onto PR #3060 (MERGED `e6806f184`); the write path must not reference the deleted `primary_feature_dir_for_mission` wrapper. | Technical | High | Open |
| C-006 | Explicit out-of-scope boundary | OUT of core scope, filed as fast-follows: finalize-tasks commit-destination bugs (#2938/#2937/#2930/#2802/#2643); status-writer behavioural unification (#2300/#3029/#1734/#3027); review-verdict integrity P0s (#2996/#2939, epic #3044); the **post-merge write mode #3033** (FR-009 only guards against it, does not implement it); the **issue-matrix verdict command + multi-file discovery #2583/#1738**, deferred to the WP-metadata authority slice (#2093/#2400). | Business | Medium | Open |
| C-007 | ADR-gated structural changes | The FR-005 lane-base change and the write-side seam-adoption contract require ADR coverage citing `2026-06-24-1` (partition + no-parallel-resolver), `2026-06-24-2` (`target_branch` reads `meta.json` from the primary anchor), `2026-07-23-1` (surface vocabulary — COORD is not conditioned on topology), and `2026-07-23-2` (post-consolidation deferral). A new ADR is required for the FR-005 lane-origin base-ref change. | Technical | High | Open |

### Key Entities

- **Acceptance-matrix row**: a per-requirement / Definition-of-Done verdict carrying a verification method and result. Its overall verdict is a **computed property** with a `PASS_PENDING_CONSOLIDATION` value and negative-invariant provenance — a writer materializes/routes it, it does not re-author the verdict.
- **Issue-matrix row**: a per-tracked-issue traceability verdict. In this mission it is a **placement-routed artifact only**; its reference-discovery source and verdict command are owned by the WP-metadata authority slice (#2093/#2400).
- **Tracer finding entry**: a dated, actor-attributed note in one of the finding categories (tooling-friction, approach, design-decision) captured during implementation and routed to the coord surface.
- **Placement seam (write path)**: the **existing** authority (`write_target(kind)` → `resolve_placement_only`) that maps an artifact kind to its destination branch surface (coordination vs primary). This mission adopts it at bypassing call sites; it does not build a new one.
- **Execution lane**: a per-lane worktree/branch created at implement time; FR-005 changes its base to the planning-artifact commit.

## Domain Language *(canonical terms)*

- **Placement seam** — canonical. The resolver mapping artifact kind → surface (`write_target` for writes, `read_dir` for reads). Do not call it a "path helper" and do not build a second write-only resolver.
- **Coordination (coord) partition vs primary partition** — coord holds lifecycle surfaces (status, notes, trace, issue-matrix, acceptance-matrix, move-task); primary holds stable planning (spec/plan/WP outlines). Name the partition sense explicitly.
- **`TRACER_FILE`** — the artifact kind for lane findings; remains coord-partition in this mission.
- **Acceptance-matrix vs issue-matrix** — distinct artifacts. Acceptance-matrix = requirement/DoD verdicts (writer in scope); issue-matrix = tracked-issue traceability (routing only here). Never conflate.
- **Lane-origin write routing** — a write invoked from a lane worktree whose destination is materialized to the coordination surface by `commit_for_mission`, not committed to the lane branch.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An agent records an acceptance-matrix verdict with a single command and **zero product-source reads** in the documented workflow.
- **SC-002**: **100%** of lane finding writes succeed with **zero** `kitty-specs/` commits on the lane branch and without tripping the `move-task` block.
- **SC-003**: Across a representative multi-lane mission consolidation, matrix and tracer writes recorded during implementation survive with **zero silent reversions** (regression-tested).
- **SC-004**: The documented "record a work-package verdict / finding" procedure is a **fixed, bounded command sequence** whose length does not grow with mission size (contrast today's open-ended source-reading loop).
- **SC-005**: **No regression** — the read-side seam census, the C-008 architectural gates, and the coord-authority gate remain green after this mission.

## Dependencies & Traceability *(informative)*

**Built on**: PR #3060 (read-side placement-seam closure — **MERGED** `e6806f184`, closed **#2886**; **#3014 was resolved independently, not by #3060**).

**Core-scope tickets** (map to requirements):

| Ticket | Maps to | Note |
|--------|---------|------|
| #2318 | FR-001 | Acceptance-matrix marking CLI — fronts existing `write_acceptance_matrix`; keeps computed verdict authoritative (campsite #2743 negative-invariant integrity). |
| #2980, #2549 | FR-003 | Lane-write barrier resolved by routing to coord, not lane commits. Campsite #2960 (attribution-blanking) for the "attributed" guarantee. |
| #2663, #2966 (direction) | FR-004 | Fold the already-isolated implement-claim write-partition split; converge the write-bypass census onto `write_target`. |
| #2993 | FR-005 | No-common-ancestor lane snapshot — P0, ADR-gated, own WP. Blast radius: `auto_rebase`, `merge/executor`, `merge/ordering`, dependent-lane invariant #1684. |
| #2482 | FR-006 | Primary residue clobbers coord matrix; reconcile via the dedicated merge driver (confirm `spec-kitty-acceptance-matrix` is row-aware). |
| #3055 | FR-010 | Coord-authority gate must recognize the seam idiom for COORD writes (routing prerequisite, folded in). |
| #2743, #3027 (campsite) | FR-001/FR-003 | Negative-invariant semantics + mark-status roster placement dependency — in-mission campsites. |

**Governance attach points** (link via `blocks`/`blocked_by`, do NOT spawn a new epic): #2160 (coord artifact authority), #1676 (deterministic authoring), #3044 (review-verdict integrity — parents the fast-follow P0s), #2017 (block-class guards).

**Deferred / fast-follows** (explicitly out of core): issue-matrix verdict command + multi-file discovery #2583/#1738 → WP-metadata authority slice (#2093/#2400); post-merge write mode #3033; finalize-tasks commit-destination consolidation (#2938/#2937/#2930/#2802/#2643); status-writer behavioural unification (#2300/#3029/#1734/#3027); review-verdict integrity (#2996/#2939). Gate twin #3035 (issue-matrix presence gate) travels with the deferred issue-matrix slice.

## Assumptions

- Rebased onto merged PR #3060 (`e6806f184`); the write path does not depend on the deleted `primary_feature_dir_for_mission` wrapper (verified: the symbol is gone, `write_target` intact).
- Reconciliation is provided by **four dedicated merge drivers** (`spec-kitty-acceptance-matrix` / `-issue-matrix` / `-traces` / `-event-log`), **not** a generic union driver. FR-006's reconcile-not-clobber depends on `spec-kitty-acceptance-matrix` being row-aware — to be **confirmed** during plan, not assumed.
- Event-log status remains the sole authority for lane state (the runtime-mutable-state eviction shipped in #2684); this mission reuses it rather than re-deriving status.
- Governance epics #2160 / #1676 / #3044 exist; this mission attaches to them rather than creating a new epic.
- Lane→coordination routing for findings follows the existing `commit_for_mission` materialization pattern used for lane-origin status events.
- The canonical tracer directory literal is `"traces"` (`retrospective/generator.py`); confirm no `traces/`-vs-`ln/` naming drift with a `Read` during plan.
