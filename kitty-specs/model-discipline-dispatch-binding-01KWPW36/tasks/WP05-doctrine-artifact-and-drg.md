---
work_package_id: WP05
title: Doctrine artifact + DRG resolution + catalog data
dependencies: []
requirement_refs:
- FR-006
- FR-007
- FR-008
- C-002
tracker_refs:
- '2364'
planning_base_branch: design/model-discipline-dispatch-2364
merge_target_branch: design/model-discipline-dispatch-2364
branch_strategy: Planning artifacts for this mission were generated on design/model-discipline-dispatch-2364. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/model-discipline-dispatch-2364 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-model-discipline-dispatch-binding-01KWPW36
base_commit: 4053c73530e864fadad988c37be9822ad7dff2b7
created_at: '2026-07-04T17:21:21.359862+00:00'
subtasks:
- T023
- T024
- T025
- T026
- T027
- T028
- T029
phase: Phase 1 - Implementation
assignee: ''
agent: "claude"
shell_pid: '553107'
history:
- at: '2026-07-04T15:30:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/
create_intent:
- src/doctrine/tactics/built-in/model-task-routing.tactic.yaml
- src/doctrine/model_task_routing/catalog/model-to-task_type.yaml
- tests/charter/test_model_task_routing_resolves.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/tactics/built-in/model-task-routing.tactic.yaml
- src/doctrine/graph.yaml
- .kittify/charter/charter.md
- src/doctrine/model_task_routing/catalog/model-to-task_type.yaml
- tests/charter/test_model_task_routing_resolves.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – Doctrine artifact + DRG resolution + catalog data

## Load Agent Profile (python-pedro)

Use the `/ad-hoc-profile-load` skill to load the `python-pedro` agent profile (role: `implementer`) before doing any work, and behave according to its guidance while executing this prompt.

## Objectives & Success Criteria

- Make the charter's model-discipline reference real activated doctrine, DRG-driven: `charter context` surfaces the `model-task-routing` tactic guidance.
- The repointed `model-task-routing` token AND the sibling `autonomous-operation-protocol` both resolve in the regenerated `references.yaml` via directive-reachability (SC-003).
- Ship a populated `model-to-task_type` catalog instance that validates against the schema (feeds WP01/WP02/WP03 with real data).
- No dependencies for authoring; WP06's invariant goes green once this WP's edges land.

## Context & Constraints

- Source of truth: `kitty-specs/model-discipline-dispatch-binding-01KWPW36/spec.md` FR-006, FR-007, FR-008, C-002; `plan.md` IC-05; `tasks.md` WP05 section; `adversarial-review.md` Round 2 fold #3/#4.
- **Load-bearing trap — DRG-driven resolution, not manual rows**: resolution goes through the DRG (`suggests` edges in `graph.yaml`) → generated `references.yaml`. A `references.yaml` row with no inbound `suggests` edge still dangles even if the string is present. Do not hand-add a `references.yaml` row directly.
- **Load-bearing trap — repoint, don't mint**: repoint the existing charter prose token from snake_case `model_task_routing` to kebab `model-task-routing` in `.kittify/charter/charter.md`. Do NOT mint a new snake_case artifact — the kind is confirmed as **tactic**, matching the pattern of `DIRECTIVE_043/044/045`.
- **Load-bearing trap — bundle regeneration is a generated-lockfile step**: after adding the tactic + edges, regenerate `references.yaml` AND the `_LIBRARY`/synthesis-manifest bundle. Skipping this step reds CI (it is a lockfile, not hand-editable).
- FR-007 is a one-line addition only: `autonomous-operation-protocol`'s tactic file already exists (`src/doctrine/tactics/built-in/autonomous-operation-protocol.tactic.yaml`, `graph.yaml:367`) — it just needs an activated-directive → `tactic:autonomous-operation-protocol` `suggests` edge.
- The populated catalog must include `models` + `task_fit` + `objective: quality_first` + `override_policy: advisory` + `freshness_policy`, and validate against `src/doctrine/schemas/model-to-task_type.schema.yaml`.
- **Shared contract with WP01**: the catalog lands at exactly `src/doctrine/model_task_routing/catalog/model-to-task_type.yaml` (shipped as package data via pyproject `src/doctrine/**/*.yaml`); WP01's loader default path resolves to exactly this via `importlib.resources.files('doctrine.model_task_routing')/'catalog'/'model-to-task_type.yaml'`.
- Run the terminology guard and `ruff`/`mypy` clean given charter/doctrine prose is touched.

## Subtasks

- [ ] T023 [red-first] `tests/charter/test_model_task_routing_resolves.py`: the `model-task-routing` tactic loads via DRG traversal (not just string-present) + `charter context` surfaces its body; `autonomous-operation-protocol` resolves. RECORD pre-fix RED (both dangle).
- [ ] T024 [FR-006] `src/doctrine/tactics/built-in/model-task-routing.tactic.yaml` (kebab) — routing guidance + catalog pointer; schema-valid.
- [ ] T025 [FR-006] `src/doctrine/graph.yaml`: add `tactic:model-task-routing` node + an activated-directive → `tactic:model-task-routing` `suggests` edge (pattern of DIRECTIVE_043/044/045).
- [ ] T026 [FR-006] repoint the charter prose token in `.kittify/charter/charter.md` from `model_task_routing` → `model-task-routing`.
- [ ] T027 [FR-007] one-line activated-directive → `tactic:autonomous-operation-protocol` `suggests` edge in `graph.yaml` (tactic already exists).
- [ ] T028 [FR-008] populated `model-to-task_type` catalog instance at exactly `src/doctrine/model_task_routing/catalog/model-to-task_type.yaml` (package data — WP01's loader default path via `importlib.resources.files('doctrine.model_task_routing')/'catalog'/'model-to-task_type.yaml'` resolves to this) (models + task_fit + `objective: quality_first` + `override_policy: advisory` + `freshness_policy`); validate against the schema.
- [ ] T029 [C-002] regenerate `references.yaml` + the `_LIBRARY`/synthesis-manifest bundle (generated-lockfile step); `ruff`/`mypy`/terminology-guard clean.

## Branch Strategy

- **Strategy**: Planning artifacts are generated on design/model-discipline-dispatch-2364; completed changes merge back there.
- **Planning base branch**: `design/model-discipline-dispatch-2364`
- **Merge target branch**: `design/model-discipline-dispatch-2364`

## Definition of Done

- [ ] T023 recorded RED pre-fix (both tokens dangle), GREEN post-implementation.
- [ ] `model-task-routing.tactic.yaml` exists, schema-valid, with a `graph.yaml` node + inbound directive `suggests` edge.
- [ ] Charter token repointed from `model_task_routing` to `model-task-routing`; no new snake_case artifact minted.
- [ ] `autonomous-operation-protocol` has an inbound directive `suggests` edge in `graph.yaml`.
- [ ] Populated catalog instance at `src/doctrine/model_task_routing/catalog/model-to-task_type.yaml` validates against `model-to-task_type.schema.yaml` and matches WP01's `importlib.resources` default path.
- [ ] `references.yaml` and the `_LIBRARY`/synthesis-manifest bundle regenerated (not hand-edited).
- [ ] `ruff`/`mypy`/terminology-guard clean.
- [ ] No changes outside `owned_files`.

## Activity Log

- 2026-07-04T18:13:11Z – claude – shell_pid=553107 – Moved to for_review
- 2026-07-04T18:13:22Z – user – shell_pid=553107 – APPROVE (opus, uv-run): red-first genuine; see adversarial-review.
