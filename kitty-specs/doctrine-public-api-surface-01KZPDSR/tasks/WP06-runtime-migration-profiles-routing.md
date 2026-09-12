---
work_package_id: WP06
title: 'Runtime migration: profiles + routing cluster'
dependencies:
- WP03
- WP04
requirement_refs:
- FR-004
planning_base_branch: feat/doctrine-public-api-surface
merge_target_branch: feat/doctrine-public-api-surface
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-public-api-surface. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-public-api-surface unless the human explicitly redirects the landing branch.
subtasks:
- T028
- T029
- T030
- T031
- T032
phase: Phase 3 - Migration
history:
- timestamp: '2026-08-10T18:39:50Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/invocation/
create_intent: []
execution_mode: code_change
mission_id: 01KZPDSR40YTNZ9HPWV3V9V3YA
owned_files:
- src/specify_cli/invocation/executor.py
- src/specify_cli/cli/commands/profiles_cmd.py
- src/specify_cli/cli/commands/agent/tasks_status_cmd.py
- src/specify_cli/review/gate_bindings.py
- src/specify_cli/cli/commands/charter/_synthesis.py
- src/specify_cli/charter_runtime/lint/_drg.py
- src/specify_cli/cli/commands/dispatch.py
- src/specify_cli/cli/commands/agent/workflow.py
role: implementer
tags: []
tracker_refs: []
wp_code: WP06
---

# Work Package Prompt: WP06 — Runtime migration: profiles + routing cluster

## ⚡ Do This First: Load Agent Profile

Run `/ad-hoc-profile-load implementer-ivan` and apply its initialization, boundaries, directives,
and tactics. State which you applied.

## Objective

Migrate the agent-profile, model-routing, and drg-model consumers onto `charter.profiles`,
`charter.model_routing`, and `charter.drg` — converting whole-module routing access to symbol
imports (FR-004). Behavior-preserving.

## Context & Constraints

- Consumes WP03 doors + WP04 ratchet (baseline shrinks per file).
- **`invocation/executor.py`** uses `doctrine.model_task_routing.evaluator`/`loader` as **whole
  modules** (`routing_loader.load()`, `routing_evaluator.evaluate()`). Convert to symbol imports
  `from charter.model_routing import load, evaluate, RoutingRecommendation`.
- **`charter_runtime/lint/_drg.py`** wraps its import in `try/except` for graceful degradation —
  keep that shape; only change the target to `charter.drg` (the ratchet forbids `doctrine.*`, not
  laziness).

## Subtasks

### T028 — Migrate `invocation/executor.py`
- `agent_profiles.profile` (`Role`) + `agent_profiles.capabilities` (`DEFAULT_ROLE_CAPABILITIES`)
  → `charter.profiles`; `model_task_routing.*` → `charter.model_routing` (symbol imports, drop
  the whole-module access).

### T029 — Migrate `profiles_cmd.py`, `agent/tasks_status_cmd.py`  [P]
- `agent_profiles.profile`/`repository`/`capabilities` → `charter.profiles`.

### T030 — Migrate `review/gate_bindings.py`, `cli/commands/charter/_synthesis.py`  [P]
- `drg.models` (`DRGGraph`, `Relation`) → `charter.drg`; `step_contracts.GateBinding` →
  `charter.mission_steps`.

### T031 — Migrate `charter_runtime/lint/_drg.py` (keep try/except)  [P]
- `drg.loader` (`DRGLoadError`, `load_built_in_graph`) → `charter.drg`, preserving the
  `try/except` graceful-degradation shape.

### T032 — Migrate `dispatch.py`, `agent/workflow.py` (model_routing)  [P]
- `model_task_routing.evaluator`/`loader` → `charter.model_routing` symbol imports.

## Branch Strategy

Base + merge target `feat/doctrine-public-api-surface`; worktree per lane. Implement via
`spec-kitty agent action implement WP06 --agent <name>` (after WP03, WP04).

## Definition of Done

- [ ] All 8 files import doctrine only via `charter.*`; ratchet baseline shrinks for them.
- [ ] Whole-module routing access converted to symbol imports.
- [ ] `_drg.py` retains its try/except graceful degradation. No behavior change.

## Risks & Reviewer Guidance

- **Risk**: leaving a whole-module `charter.model_routing` import (defeats curation). Reviewer:
  confirm symbol imports.
- **Reviewer**: confirm `_drg.py` still degrades gracefully when doctrine is unimportable.
