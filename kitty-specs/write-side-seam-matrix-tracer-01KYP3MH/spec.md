# Mission Specification: Write-Side Seam: Matrix & Tracer Writers

**Mission Branch**: `feat/write-side-seam-matrix-tracer`
**Created**: 2026-07-29
**Status**: Draft
**Input**: Follow-up to PR #3060 (read-side placement-seam closure). Close the write/gate side of the same seam so consumer missions stop losing matrix and tracer state and stop burning inference to hand-edit matrices.

## Context & Motivation *(informative)*

PR #3060 unified the **read** side of the artifact placement seam: every "which surface does this artifact live on?" read now routes through one resolver, and the `primary_feature_dir_for_mission` wrapper was deleted. This mission is the **write/gate twin** of that work. Three consumer-facing pains all trace to the write side of the same seam being non-uniform:

1. **Matrix edits are inference-heavy.** No command writes acceptance-matrix or issue-matrix verdicts, so an agent must read product source to learn the file shape, discover computed fields and negative-invariant semantics, and hand-edit JSON — burning tokens and getting it wrong.
2. **Lanes cannot cleanly record findings.** Doctrine says lanes append tracer findings during implementation, but the findings artifact is coord-partition and the `kitty-specs/` lane guards warn-then-block any lane commit — so a lane physically cannot write where doctrine says to.
3. **Consolidation drops writes.** Matrix, tracer, and planning writes are snapshotted onto lanes with no common ancestor and are silently reverted at merge.

The unifying move: **deterministic write commands that route lane-origin writes to the correct partition surface through the placement seam's write path** — the same way status transitions already materialize lane-origin events to the coord surface. Agents stop hand-committing artifacts; the command owns placement.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Record a matrix verdict with one deterministic command (Priority: P1)

An implementing or reviewing agent has just finished verifying a work package. It needs to record the outcome in the acceptance-matrix (per requirement / Definition-of-Done) and the issue-matrix (per tracked issue). Today it reads product source to reconstruct the file shape and hand-edits JSON. In the target state it runs a single command that sets the verdict; the command owns the file shape, computed fields, invariant validation, destination surface, and commit.

**Why this priority**: This is the headline token-burn the mission targets and the most self-contained, live-witnessed win. It delivers value even if nothing else ships.

**Independent Test**: On a mission with a scaffolded acceptance-matrix, run the verdict command for one row and assert the row is updated, computed fields are correct, and the agent read zero product-source files to do it. Repeat for the issue-matrix with references that live in `tasks/` (not just `spec.md`).

**Acceptance Scenarios**:

1. **Given** a scaffolded acceptance-matrix row in `unknown`/`pending`, **When** the agent runs the acceptance-verdict command with a result and verification method, **Then** the row is updated deterministically, derived fields are recomputed, the file validates against its negative-invariant shape, and the write lands on the surface the seam dictates.
2. **Given** an issue referenced only in a `tasks/WP##.md` file (not `spec.md`), **When** the agent runs the issue-verdict command, **Then** the reference is discovered and the issue-matrix row is written — no false "reference missing" outcome.
3. **Given** a verdict already recorded, **When** the same command is re-run with identical inputs, **Then** it is a no-op (no duplicate row, no error).

---

### User Story 2 - Capture a finding on a lane without blocking the lane (Priority: P1)

An agent implementing a work package on a lane worktree discovers a tooling-friction, approach, or design-decision note worth retaining. It needs to record that finding during implementation. Today it cannot: writing the coord-partition tracer file from the lane trips the warn-then-block guards. In the target state a single command appends a dated, attributed finding entry that is **routed to the mission's coordination surface**, leaving the lane branch unblocked and clean.

**Why this priority**: Formalizing the lane-writable findings capture is a primary ask, and without it tracer files remain unusable on-lane.

**Independent Test**: From a lane worktree, run the finding-append command; assert the entry appears on the coordination surface, the lane branch has no new `kitty-specs/` commit, and a subsequent `move-task` on that lane is not blocked by the finding.

**Acceptance Scenarios**:

1. **Given** an agent on a lane worktree, **When** it appends a finding via the command, **Then** the entry is recorded on the coordination surface and no `kitty-specs/` artifact is committed to the lane branch.
2. **Given** a finding recorded from a lane, **When** the lane later runs a status transition (`move-task`), **Then** the transition is not blocked by a `kitty-specs/` divergence.
3. **Given** the same finding content submitted twice, **When** the append command runs again, **Then** no duplicate entry is created.

---

### User Story 3 - Writes land on the right surface and survive consolidation (Priority: P2)

A mission operator consolidates several lanes. Matrix verdicts, tracer findings, and status recorded during implementation must all still be present and correct after the merge — not reverted, not clobbered by a stale copy on another partition.

**Why this priority**: This is the durability guarantee that makes Stories 1 and 2 trustworthy; it depends on lanes sharing a common ancestor with the consolidation base.

**Independent Test**: Run a representative multi-lane mission that records matrix and tracer writes during implementation, then consolidate; assert every recorded write is present and correct on the consolidated branch with zero silent reversions.

**Acceptance Scenarios**:

1. **Given** an execution lane created at implement time, **When** the lane is created, **Then** its worktree branches from the planning-artifact commit so it shares a common ancestor with the consolidation base.
2. **Given** matrix/tracer writes recorded on a lane during implementation, **When** the mission consolidates, **Then** those writes are present on the consolidated branch and not reverted.
3. **Given** a stale matrix copy on a non-authoritative partition, **When** a fresher verdict is written, **Then** the write reconciles rather than being overwritten by the stale copy.

### Edge Cases

- **Coordination surface missing** (worktree/branch removed): a lane finding or matrix write returns a structured, actionable error rather than crashing or writing partially.
- **Unknown target**: a verdict command for an unknown work package or unrecognized issue reference returns an actionable error, not a silent no-write.
- **Concurrent cross-lane writes** to the same coordination artifact reconcile via the union merge driver — no clobber.
- **Mission with no tracked issue references**: the issue-verdict command is a legitimate no-op and does not fabricate false rows.
- **Prerequisite not yet merged**: if PR #3060 has not landed at implementation time, the write path must not assume the deleted wrapper exists; the mission rebases onto #3060.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Deterministic acceptance-matrix verdict command | As an implementing/reviewing agent, I want a single command to set an acceptance-matrix row's verdict, verification method, and result so that I never read product source or hand-edit JSON. | High | Open |
| FR-002 | Deterministic issue-matrix verdict command with multi-file reference discovery | As an agent, I want a command to set an issue-matrix row's verdict, where issue references are discovered across `spec.md`, `tasks/`, and `plan.md`, so that references outside the spec are not missed. | High | Open |
| FR-003 | Lane findings (tracer) append command routed to coordination surface | As an agent on a lane, I want to append a dated, attributed finding that is routed to the mission's coordination surface without committing to the lane branch, so that findings are captured without blocking the lane. | High | Open |
| FR-004 | Write-side placement routing through the seam | As a maintainer, I want every matrix, tracer, and status write to resolve its destination surface through the placement seam's write path (the write twin of the read path #3060 unified), so that no call site hand-derives a write destination. | High | Open |
| FR-005 | Lane branches from the planning-artifact commit (common ancestor) | As an operator, I want an execution lane's worktree to branch from the planning-artifact commit so that matrix/tracer/planning writes share a common ancestor with the consolidation base and are not reverted at merge. | High | Open |
| FR-006 | Matrix write reconciles, never clobbers a fresher cross-partition copy | As an operator, I want a matrix write to reconcile with a fresher copy on the authoritative surface rather than overwrite it, so that stale partition residue cannot destroy a newer verdict. | Medium | Open |
| FR-007 | Idempotent, re-runnable writes | As an agent, I want re-running any verdict or finding command with identical inputs to be a no-op, so that retries never create duplicate rows or entries. | Medium | Open |
| FR-008 | Structured machine-readable command results | As an orchestrator, I want each write command to emit structured output naming the resulting row/entry and destination surface, so that I can consume the result without parsing prose. | Medium | Open |
| FR-009 | Actionable errors on unroutable writes | As an agent, I want a structured, actionable error when a write cannot be routed (missing coordination surface, unknown target) instead of a silent partial write, so that I can recover deterministically. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Zero-inference writes | A matrix or tracer write requires zero product-source reads by the agent: the documented workflow is fully specified by CLI arguments and current mission state (0 "read module X to learn the shape" steps). | Usability | High | Open |
| NFR-002 | Responsive commands | Each write command completes in under 3 seconds (p95) on a representative mission, so it never reads as a hang. | Performance | Medium | Open |
| NFR-003 | Lane-safe and idempotent | Running any write command from a lane leaves zero `kitty-specs/` commits on the lane branch and no blocked/dirty state; re-running any command is a no-op. | Reliability | High | Open |
| NFR-004 | Coverage and complexity | Every new command branch and the seam write path has focused unit tests executed directly; no new or modified function exceeds cyclomatic complexity 15. | Maintainability | High | Open |
| NFR-005 | No regression of shipped invariants | The read-side seam census (PR #3060) and the C-008 architectural gates remain green; event-log status remains the sole authority for lane state. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Extend the seam, never allow-list a bypass | The write path MUST reuse/extend the placement-seam write authority. Adding a per-command exception to the `kitty-specs/` guards, or hand-deriving a destination, is prohibited. | Technical | High | Open |
| C-002 | Tracer classification unchanged | `TRACER_FILE` remains coord-partition. This mission does NOT reclassify it. Lane findings reach the coordination surface via routing, not via lane-branch commits. | Technical | High | Open |
| C-003 | Do not rebuild the status engine | Status transitions are already deterministic (event-log is the sole authority). This mission only routes status writes through the seam and adds matrix/tracer writers — it does not re-implement transition logic. | Technical | High | Open |
| C-004 | Terminology canon | New command names, flags, and prose use canonical Mission terminology; no `feature*` aliases and no new overloaded uses of `primary`/`merge`/`routing` without naming the sense. | Business | Medium | Open |
| C-005 | Dependency on PR #3060 | Coord topology; consolidates into `feat/write-side-seam-matrix-tracer`; PR into `upstream/main` post-consolidation. Depends on PR #3060 (read-side seam), treated as in-flight — rebase onto it if not yet merged at implementation time. | Technical | High | Open |
| C-006 | Explicit out-of-scope boundary | finalize-tasks commit-destination bugs (#2938/#2937/#2930/#2802/#2643), status-writer behavioural unification (#2300/#3029/#1734/#3027), and review-verdict integrity P0s (#2996/#2939, epic #3044) are OUT of core scope and filed as fast-follows. | Business | Medium | Open |

### Key Entities

- **Acceptance-matrix row**: a per-requirement / Definition-of-Done verdict carrying a verification method and result; subject to a negative-invariant shape (e.g. an unknown verification method must not silently loop `pending`).
- **Issue-matrix row**: a per-tracked-issue traceability verdict linking a tracked issue reference (discovered across spec/tasks/plan) to a work-package outcome.
- **Tracer finding entry**: a dated, actor-attributed note in one of the finding categories (tooling-friction, approach, design-decision) captured during implementation.
- **Placement seam (write path)**: the single authority that maps an artifact kind to its destination branch surface (coordination vs primary). The write twin of the read path unified by PR #3060.
- **Execution lane**: a per-lane worktree/branch created at implement time; must branch from the planning-artifact commit.

## Domain Language *(canonical terms)*

- **Placement seam** — canonical. The resolver mapping artifact kind → surface. Do not call it a "path helper."
- **Coordination (coord) partition vs primary partition** — coord holds lifecycle surfaces (status, notes, trace, issue-matrix, move-task); primary holds stable planning (spec/plan/WP outlines). Name the partition sense explicitly.
- **`TRACER_FILE`** — the artifact kind for lane findings; remains coord-partition in this mission.
- **Acceptance-matrix vs issue-matrix** — distinct artifacts. Acceptance-matrix = requirement/DoD verdicts; issue-matrix = tracked-issue traceability. Never conflate.
- **Lane-origin write routing** — a write invoked from a lane worktree whose destination is materialized to the coordination surface by the command, not committed to the lane branch.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An agent records a matrix verdict with a single command and **zero product-source reads** in the documented workflow.
- **SC-002**: **100%** of lane finding writes succeed with **zero** `kitty-specs/` commits on the lane branch and without tripping the `move-task` block.
- **SC-003**: Across a representative multi-lane mission consolidation, matrix and tracer writes recorded during implementation survive with **zero silent reversions** (regression-tested).
- **SC-004**: The documented "update a work-package verdict and matrix" procedure is a **fixed, bounded command sequence** whose length does not grow with mission size (contrast today's open-ended source-reading loop).
- **SC-005**: **No regression** — the read-side seam census (PR #3060) and the C-008 architectural gates remain green after this mission.

## Dependencies & Traceability *(informative)*

**Prerequisite**: PR #3060 (read-side placement-seam closure; closes #2886/#3014, defers #3055).

**Core-scope tickets** (map to requirements):

| Ticket | Maps to | Note |
|--------|---------|------|
| #2318 | FR-001 | Deterministic acceptance-matrix marking CLI (live-witnessed; re-weight from P2). |
| #2583, #1738 | FR-002 | Issue-matrix verdict writer + multi-file reference scanner. |
| #2980, #2549 | FR-003 | Lane-write barrier (warn-then-block) resolved by routing, not lane commits. |
| #2966 (direction), #3055 (deferred gate) | FR-004 | Write-target authority through the seam. |
| #2993 | FR-005 | No-common-ancestor lane snapshot (planning-artifact-integrity predecessor). |
| #2482 | FR-006 | Primary residue clobbers coord matrix. |
| #2743 (campsite) | FR-001 | Acceptance-matrix negative-invariant semantics — fold as in-mission campsite. |
| #3027 (campsite) | FR-002/FR-003 | mark-status roster placement dependency — fold as in-mission campsite. |

**Governance attach points** (link via `blocks`/`blocked_by`, do NOT spawn a new epic): #2160 (coord artifact authority), #1676 (deterministic authoring, the ownership boundary the writers instantiate), #3044 (review-verdict integrity — parents the fast-follow P0s), #2017 (block-class guards).

**Fast-follows** (explicitly out of core, tracked separately): finalize-tasks commit-destination consolidation (#2938/#2937/#2930/#2802/#2643); status-writer behavioural unification (#2300/#3029/#1734/#3027); review-verdict integrity (#2996/#2939).

## Assumptions

- PR #3060 lands before or during implementation; this mission rebases onto it and does not depend on the deleted `primary_feature_dir_for_mission` wrapper.
- The existing union merge driver reconciles cross-branch copies of matrix and tracer artifacts.
- Event-log status remains the sole authority for lane state (the runtime-mutable-state eviction has already shipped); this mission reuses it rather than re-deriving status.
- Governance epics #2160 / #1676 / #3044 exist; this mission attaches to them rather than creating a new epic.
- The lane→coordination routing for findings can follow the same materialization pattern already used to route lane-origin status events to the coordination surface.
