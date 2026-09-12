---
work_package_id: WP03
title: Gate Execution Context + total resolvers
dependencies:
- WP02
requirement_refs:
- C-004
- FR-001
- NFR-001
- NFR-003
planning_base_branch: remediation/coord-lifecycle-gates
merge_target_branch: remediation/coord-lifecycle-gates
branch_strategy: Planning artifacts for this mission were generated on remediation/coord-lifecycle-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/coord-lifecycle-gates unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
- T018
- T019
phase: Phase 3 - Gate Execution Context
history:
- at: '2026-07-23T18:50:04Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/acceptance/gates_core.py
create_intent:
- src/specify_cli/acceptance/execution_context.py
- tests/acceptance/test_gate_execution_context.py
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- src/specify_cli/acceptance/gates_core.py
- src/specify_cli/acceptance/execution_context.py
- tests/acceptance/test_gate_execution_context.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – Gate Execution Context + total resolvers

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` to load `python-pedro` (role `implementer`, agent `claude`) before reading further.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

Introduce the `(surface, ref, phase)` value a gate is **handed and cannot derive**, the *cannot-evaluate* outcome, the `LifecyclePhase` enum, and make the resolvers **total** (four `CoordState` answers). Every verdict names its surface. This converts #1834 from a site fix into a property of every gate.

**Done** = the behavioural contract `gate-execution-context.md` C1–C7 pass on realistic fixtures; the ambient-derivation mutant dies behaviourally.

## Context & Constraints

- Contract `gate-execution-context.md` (C1–C7). data-model.md `GateExecutionContext` (GEC-1..GEC-5), `LifecyclePhase` (PH-1).
- **C1 (behavioural)**: given a gate handed a context whose `surface` differs from **both** `repo_root` and cwd, all three seeded with **different** answers, the verdict reflects the answer at `context.surface`. Reuse the decoy-marker idiom in `tests/integration/coord_topology_fixture.py` and `test_placement_partition_golden_path.py::test_cwd_independence_resolves_identical_authority`. Do NOT assert a single construction site (that is the code-shape form NFR-008 forbids).
- **GEC-5** — a stamp is not permission: a gate asked to judge a COORD-homed kind against a PRIMARY-stamped surface returns cannot-evaluate (C2), **not** a verdict. Without this, the create-window reproduces #2885 with an honest label.
- **C-004 / C7**: identical defect condition on coord and flat missions → identical outcome. Must not be named/shaped around coordination topology; must not read `flattened`.

## Branch Strategy

- **Planning base branch**: `remediation/coord-lifecycle-gates`
- **Merge target branch**: `remediation/coord-lifecycle-gates`

## Subtasks & Detailed Guidance

### Subtask T014 – `GateExecutionContext` value object

- **Steps**: Create `acceptance/execution_context.py` with the immutable `GateExecutionContext(surface, surface_kind, ref, phase, mission_slug)`. GEC-1: a gate receives this; it may not construct one from `repo_root`/`os.getcwd()`/a bare dir.

### Subtask T015 – `LifecyclePhase` + PH-1

- **Steps**: Ordered enum `REVIEW` < `ACCEPT` < `POST_CONSOLIDATION`. PH-1: a gate invoked below its declared minimum phase returns `NOT_APPLICABLE_IN_PHASE`, not pass/fail. (Whether `IMPLEMENT` needs representation is an IC-01 finding — check WP01's record.)

### Subtask T016 – cannot-evaluate + GEC-5

- **Steps**: Add the distinguishable *cannot-evaluate* outcome (C2) naming the reason; wire GEC-5 (COORD-homed kind on PRIMARY-stamped surface → cannot-evaluate).

### Subtask T017 – Total resolution (four `CoordState` answers)

- **Steps**: In `gates_core.py`, consume the WP02 seam so resolution is total: `DELETED` → raise `CoordinationBranchDeleted` (`error_code = "COORDINATION_BRANCH_DELETED"`), does **not** read primary; `EMPTY` + `UNMATERIALIZED` → resolve primary + stamp `surface_kind = PRIMARY`; `MATERIALIZED` → coord. GEC-2 ref-agreement: `surface` not at `ref` → raise (C5). Do not re-derive EMPTY's loud/quiet topology behaviour — consume the existing resolver's.

### Subtask T018 – C6 + C7

- **Steps**: Every verdict/recorded judgement carries a resolvable surface+ref identifier (C6/NFR-003). Add the topology-neutrality test (C7): identical defect condition coord vs flat → identical outcome, reusing the decoy-marker + cwd-independence idioms.

### Subtask T019 – C-005 compat golden

- **Steps**: If a new symbol lands on the task-command compat surface, register it and update the golden (from 156, or from 157 if WP02 already moved it). Otherwise note none exported.

## Test Strategy

- New: `tests/acceptance/test_gate_execution_context.py` (C1–C7, behavioural, on realistic fixtures — no code-shape scans).
- Note: `tests/acceptance/` may be created first by WP06; if this WP creates it, register both gate-coverage baselines deliberately (C-006).

## Risks & Mitigations

- Do not shape around coord topology (C-004). Do not add new `flattened` dependence.
- Leeway: `mission_runtime/artifacts.py` (resolver totality only; owned WP02) — touch only if strictly needed, with rationale.

## Review Guidance

- Confirm C1 kills the ambient-derivation mutant **behaviourally** (three seeded answers, verdict follows `context.surface`).
- Confirm GEC-5 returns cannot-evaluate (not a verdict) for a COORD-homed kind on a PRIMARY stamp.

## Activity Log

- 2026-07-23T18:50:04Z – system – Prompt created.
