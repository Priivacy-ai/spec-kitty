# Mission Specification: 3.2.6 P0 reliability triad

**Mission Branch**: `fix/p0-reliability-triad`
**Created**: 2026-08-26
**Status**: Draft
**Input**: Fix three confirmed 3.2.6 release-blocking reliability defects (#3282, #3579, #3281) as one themed mission of three independent, non-overlapping work packages.

## Intent Summary

Three P0 defects each leave a project in a **broken-but-"healthy"-reporting** state during a core workflow, and each blocks a shippable 3.2.6:

- **#3282 (upgrade → charter activation):** after `spec-kitty upgrade`, a project using a *pointer-based* charter ends up with **no mission-type activations**, because upgrade writes activations to `config.yaml` while pointer-charter projects read them from the pointed-at `charter.yaml`. Downstream, `mission create` / `setup-plan` fail closed with "Unknown mission type".
- **#3579 (merge → stale-lane recovery):** the `merge` stale-lane halt hands the operator a raw `git checkout … && git merge …` remedy that produces a `status.json` conflict git cannot reconcile, and the halt text names **neither** of the tool's own remedies (the semantic merge-driver family, which deliberately excludes `status.json`; and `spec-kitty agent status materialize`, which rebuilds `status.json` from the event log). The guidance is a dead end.
- **#3281 (implement → lane allocation):** when lane allocation hits a recorded-planning-commit merge conflict and the operator retries, dependency propagation is **skipped**, because `ensure_workspace_materialized` early-returns on `workspace.exists` (bare `.git` presence treated as "allocation complete") and never re-enters the allocator's idempotent self-heal. Compounded by non-atomic fresh-path allocation (leftover worktree) and an ancestry-blind claim gate, a WP can be claimed against a lane missing its dependencies' code.

These are batched into one mission for release tracking. The three fixes touch **disjoint files** and proceed independently; there is no ordering dependency between them.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Upgrade heals pointer-based charter activations (Priority: P1)

An operator runs `spec-kitty upgrade` on an existing project whose `.kittify/config.yaml` carries a `charter:` pointer to a `charter.yaml`. Today, upgrade reports success but the project cannot create a mission afterward because mission-type activations landed in the wrong file. This story makes upgrade provision activations to the *effective* activation authority so the project is immediately usable.

**Why this priority**: Silent, universal breakage of the very next workflow (mission creation) for every pointer-charter project on 3.2.6; cleanest, most isolated fix. Release-blocking (P0-severity).

**Independent Test**: On a pointer-charter fixture with no `mission_type_activations`, run the `upgrade` CLI, then assert `PackContext.from_config(project).activated_mission_types` is non-empty **and** the key landed in `charter.yaml` (not `config.yaml`), and that `mission create` / `setup-plan` succeed.

**Acceptance Scenarios**:

1. **Given** a pointer-based charter project whose `charter.yaml` lacks `mission_type_activations`, **When** `spec-kitty upgrade` runs, **Then** the default mission-type activations are written to `charter.yaml` and the effective registry is non-empty.
2. **Given** the same project, **When** upgrade's dry-run / `--json pending_provisioning` predicate runs, **Then** it reports provisioning as *pending* (not a false "not pending") by inspecting the resolved write target.
3. **Given** a pointer-charter project whose `charter.yaml` already declares an explicitly authored empty activation list, **When** upgrade runs, **Then** that authored intent is preserved (not overwritten).

---

### User Story 2 - Merge stale-lane halt points to a reachable remedy (Priority: P2)

An operator running `spec-kitty merge` hits a stale planning-lane halt whose only guidance is raw `git`, which creates a `status.json` conflict git cannot resolve. This story makes the halt name the tool's own recovery so the operator can actually complete the merge without hand-editing a generated file.

**Why this priority**: Turns a dead-end into a followable recovery on a core git workflow; mechanical fix. Release-blocking (P0-severity).

**Independent Test**: Drive `check_lane_staleness()` → `_stale_remediation()` for a planning lane and assert the remediation names `spec-kitty agent status materialize` (a reachable tool remedy), not merely raw `git`.

**Acceptance Scenarios**:

1. **Given** a stale planning lane with a `status.json` conflict, **When** the merge halt emits remediation, **Then** the remediation names `spec-kitty agent status materialize --mission <id>` (regenerate from the event log) followed by `git add`, giving a reachable resolution.
2. **Given** the same halt, **When** the remediation is inspected, **Then** it names only tool commands (no hand-edit of a tool-generated file) and introduces no `status.json` merge driver. (The minimal fix is the remediation text; end-to-end merge completion is Out of Scope — see SC-002.)

---

### User Story 3 - Lane-allocation retry does not skip dependency propagation (Priority: P3)

An operator re-runs `spec-kitty implement WP##` after a recorded-planning-commit merge conflict left a partially-allocated lane. Today the retry short-circuits and the WP proceeds against a lane missing its dependencies' code. This story makes the retry re-enter the idempotent allocator self-heal, makes fresh-path allocation atomic, and makes the claim gate ancestry-aware.

**Why this priority**: Highest-severity data-integrity failure (WP built on incomplete code) but the heaviest and requires coordination with the assignee (robertDouglass) and #3432 at the shared lane-compute boundary. Release-blocking (P0-severity).

**Independent Test**: With a leftover lane worktree that `exists` but lacks the recorded planning SHA / an approved dependency tip, drive `_ensure_workspace_materialized` and assert it re-enters allocator self-heal (the reuse-path merges run) rather than early-returning; and drive `allocate_lane_worktree` with a conflicting `planning_commit_sha` and assert no registered worktree remains.

**Acceptance Scenarios**:

1. **Given** a leftover lane worktree missing the recorded planning SHA, **When** implement is retried, **Then** the allocator self-heal re-runs the planning-commit and dependency-tip merges instead of short-circuiting on `workspace.exists`.
2. **Given** a fresh-path allocation whose `_merge_recorded_planning_commit` conflicts, **When** the error is raised, **Then** no registered worktree is left on disk (atomic rollback).
3. **Given** a WP whose approved dependency lane tip is not a git ancestor of the workspace HEAD, **When** the claim/dependency gate runs, **Then** the claim is refused until ancestry holds (status-lane approval alone is insufficient).
4. **Given** a leftover worktree that is already on correct ancestry, **When** implement is retried, **Then** it is a no-op resume (not re-gated).

### Edge Cases

- Pointer-charter project whose `charter.yaml` already has an authored empty activation list → preserve, do not overwrite (#3282).
- `status.json` conflict where the append-only event log also has a driver-managed conflict → driver reconciles the log, then `materialize` rebuilds `status.json` (#3579).
- Retry where the leftover worktree exists and is already correct → no-op resume, not re-gated (#3281).
- Second `allocate_lane_worktree` caller on the `orchestrator_api` path must observe the same atomicity/ancestry invariants (#3281).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Provision activations to the effective authority | As an operator upgrading a pointer-based charter project, I want `upgrade` to write mission-type activations to the pointed-at `charter.yaml` so that mission creation works immediately afterward. (Source: #3282) | High | Open |
| FR-002 | Accurate provisioning-pending predicate | As an operator, I want the upgrade dry-run / `--json` predicate to report provisioning as pending by inspecting the resolved write target, so the preview is truthful for pointer projects. (Source: #3282) | High | Open |
| FR-003 | Halt names a reachable status.json remedy | As an operator hitting a merge stale-lane halt, I want the remediation to name `spec-kitty agent status materialize` so I can resolve the `status.json` conflict with tool commands. (Source: #3579) | High | Open |
| FR-004 | No hand-edit / no new driver | As an operator, I want the remediation to require no hand-edit of a generated file and introduce no `status.json` merge driver, so recovery stays within the tool's contract. (Source: #3579) | High | Open |
| FR-005 | Retry re-enters idempotent self-heal | As an operator retrying `implement` after a planning-commit merge conflict, I want allocation to re-enter the idempotent self-heal (re-run planning-commit + dependency-tip merges) instead of short-circuiting on `workspace.exists`. (Source: #3281) | High | Open |
| FR-006 | Atomic fresh-path allocation | As an operator, I want a failed planning-commit merge during fresh allocation to leave no registered worktree, so a retry starts clean. (Source: #3281) | High | Open |
| FR-007 | Ancestry-aware claim gate (post-materialize, both paths) | As an operator, I want a **post-materialize** ancestry check — evaluated after self-heal (FR-005) has re-run the planning-commit and dependency-tip merges, keyed on the *merged* tip — to refuse `claimed` only when self-heal cannot make the recorded planning SHA and every approved dependency tip ancestors of workspace HEAD, so a WP is never claimed against a lane missing its dependencies **without** deadlocking a legitimately-approved same-mission dependency. The check must live at a seam both the CLI and `orchestrator_api` claim paths cross. FR-005 and FR-007 land together. (Source: #3281) | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Red-first regression proof | Each of the three fixes ships a regression test driving the **pre-existing public entry point**, demonstrably RED on pre-fix code and GREEN after (100% of the three defects covered). | Reliability | High | Open |
| NFR-002 | Zero-suppression quality | New/changed code passes `ruff` and `mypy` with zero issues and zero new suppressions; no function exceeds cyclomatic complexity 15. | Maintainability | High | Open |
| NFR-003 | Migration-free, semantics-preserving upgrade fix | The #3282 fix requires no new migration (runs via the existing rc-tolerant finalizer) and preserves additive / idempotent / authored-empty-`[]` activation semantics. | Compatibility | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Disjoint ownership across WPs | The three WPs must touch disjoint files (ownership no-overlap). WP02/#3579 and WP03/#3281 both sit in `src/specify_cli/lanes/` but in different files with no cross-import; a reviewer confirms no cross-effect on `status.json` merge behavior. | Technical | High | Open |
| C-002 | No `status.json` merge driver | #3579 must NOT register a `status.json` merge driver — `status.json` is in `_NON_DIVERGENT_CANONICAL_ARTIFACTS` (defined in `tests/architectural/test_merge_reconciliation_class_guard.py`, not `merge.py`) and a driver would fail the T013 completeness guard. `status.json` is a derived projection, rematerialized not reconciled. | Technical | High | Open |
| C-003 | Coordinate #3281; scope-fence it | #3281 is assigned to robertDouglass — coordinate, do not reassign. It shares the lane-compute boundary with #3432 (closed; #3432 owns compute, #3281 owns allocator + claim gate) and reshapes the same fresh-path allocation surface as #2570 friction #1 (allocator serialization) — coordinate, do not fold. Scope-fence to the allocator retry invariant + ancestry gate; do not absorb adjacent runtime-selection / evidence-commit symptoms. | Technical | High | Open |
| C-004 | Do not touch shared activation resolver | #3282 must not modify the shared `charter.pack_manager.resolve_activation_write_target` (consumed by interview/generate/org_charter). Scope the fix to the upgrade helper, routing through the existing pointer-aware writer; the predicate must keep a defined, non-crashing dry-run contract when the resolver raises `CharterPackConfigError` on a dangling pointer. | Technical | High | Open |
| C-005 | Ancestry check is post-materialize, both-paths | The FR-007 ancestry assertion must run AFTER `_ensure_workspace_materialized`/self-heal (never at the pre-materialize status-lane gate, which stays as fail-fast), and must sit at a seam both the CLI (`workflow_executor`) and `orchestrator_api` claim paths cross, so the invariant is not CLI-only. Coupled to self-heal: on failure, route back into self-heal; hard-refuse only if ancestry still cannot be established. | Technical | High | Open |
| C-006 | Reconcile the #1832/#1833 single-resolution invariant | WP03's exists-branch re-entry must invoke a dedicated idempotent self-heal, NOT break the landed invariant that `_create`/re-resolution does not run when the workspace exists (`test_implement_single_resolution.py`, #1832/#1833). Update that invariant test's semantics with an explicit rationale rather than silently inverting it. | Technical | High | Open |

### Key Entities

- **Mission-type activation authority**: the file a project's activations are read from — `config.yaml` for legacy projects, the pointed-at `charter.yaml` for pointer-based charters. The write side must resolve to the same authority as the read side (#3282).
- **`status.json`**: a derived projection of the append-only `status.events.jsonl`; deliberately driver-exempt, rebuilt via `spec-kitty agent status materialize` (#3579).
- **Lane worktree + `planning_commit_sha`**: an execution lane's materialized worktree and the recorded planning commit that must be merged into it, plus every approved dependency lane tip that must be a git ancestor before claim (#3281).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After `spec-kitty upgrade` on a pointer-based charter project, mission creation and `setup-plan` succeed (effective activation registry non-empty) — from 0% today to 100% of pointer-charter projects. (#3282)
- **SC-002**: On a merge stale-lane halt with a `status.json` conflict, the emitted remediation names a reachable tool remedy (`spec-kitty agent status materialize`) and no raw-`git`-only dead end — verified by asserting the remediation text through `_stale_remediation`, with zero hand-edits of tool-generated files instructed. (End-to-end merge completion is Out of Scope.) (#3579)
- **SC-003**: After a planning-commit merge conflict during lane allocation, re-running `implement` yields a workspace containing all approved dependency-lane code (dependency propagation not skipped), and a WP cannot be claimed against a lane missing its dependencies' tips. (#3281)
- **SC-004**: Each of the three defects has a regression test that is RED on pre-fix code and GREEN after, verified through the pre-existing public entry point. (NFR-001)

## Assumptions

- The three defects are addressed as three independent work packages under one mission; no sequencing dependency exists between them (architecture-lens verdict: ONE-THEMED-3WP).
- #3282 could be peeled into its own mission (architect recommendation); it is retained here per explicit operator direction to batch all three release-blocking P0s together.
- Fix directions follow the pre-spec investigation dossier; exact code shapes are settled during `/spec-kitty.plan` and `/spec-kitty.tasks`.

## Out of Scope

- Adding a doctor/upgrade health check that flags an empty effective mission-type registry (optional follow-up to #3282, not required to unblock missions).
- The "incorporate + rematerialize inside `consolidate_lane_into_mission`" variant of #3579 beyond naming the remedy (may be considered at plan time, but the minimal fix is the remediation text).
- Adjacent #3281 comment-thread symptoms (`move-task` blocking on committed evidence, `next` selection) — split out, not absorbed.
- Any `status.json` merge-driver / `.gitattributes` change (explicitly rejected, C-002).
