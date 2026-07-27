# Software-Dev Mission Composition Rewrite

**Mission ID:** `01KQ26CYMMB4SZP2RKVH74RRB5`
**Mission slug:** `software-dev-composition-rewrite-01KQ26CY`
**Tracker:** [#503] Phase 6 / WP6.2 — Rewrite software-dev mission as profile-invocation composition
**Parent epic:** #468 · **Umbrella:** #461
**Target / merge branch:** `main`
**Created:** 2026-04-25

## Overview

Phases 0–5 of the composition substrate landed (most recently `#501`/PR `#778`). `StepContractExecutor` exists and composes `ProfileInvocationExecutor` calls, but the built-in `software-dev` mission still drives its live path through the legacy v2.1.0 runtime DAG in `mission-runtime.yaml`. This mission rewrites the built-in `software-dev` mission so that `/specify`, `/plan`, `/tasks`, `/implement`, and `/review` execute as profile-invocation composition on top of `StepContractExecutor` — proving the composition architecture on the live path before custom missions are exposed in `#505`.

## User Scenarios & Testing

### Primary flow — operator drives software-dev end-to-end

1. Operator runs `/spec-kitty.specify <description>`.
2. The runtime bridge resolves the mission as `software-dev` and dispatches the `specify` action through `StepContractExecutor`, which loads the `specify` step contract, walks its declarative steps, and routes each step through `ProfileInvocationExecutor` with the `(software-dev, specify)` action context (researcher profile by default, action-scoped governance slice).
3. Operator runs `/spec-kitty.plan`. Same composition path, `(software-dev, plan)` action context, architect profile by default.
4. Operator runs `/spec-kitty.tasks`. The single public action expands internally to outline → packages → finalize sub-steps inside the `tasks` step contract; each sub-step is routed through composition. Existing artifact outputs (`tasks.md`, `tasks/WP##.md`) and finalize-tasks dependency validation behavior remain intact.
5. Operator runs `/spec-kitty.implement WP##`. Each step in the implement contract (workspace, execute, quality_gate, commit, status_transition) flows through composition with the implementer profile and implement-scoped governance.
6. Operator runs `/spec-kitty.review`. Composition routes the review action to the reviewer profile with review-scoped governance.

### Acceptance scenarios

- **AS-1:** Running the full software-dev lifecycle on a sample mission produces the same on-disk artifact set as the legacy DAG path: `spec.md`, `plan.md`, `tasks.md`, `tasks/WP##.md`, lane-state events, trail entries, glossary checks. No artifact regressions.
- **AS-2:** For each of the five public actions (`specify`/`plan`/`tasks`/`implement`/`review`), the resolved invocation carries action-scoped governance context (the directives/tactics declared in `actions/<action>/index.yaml`), not the union of all action contexts. Verified by inspecting the resolved context per invocation.
- **AS-3:** Default profile per action matches the action surface calibration table:
  - `specify` → `researcher-robbie`
  - `plan` → `architect-alphonso`
  - `tasks` → `architect-alphonso` (planning lineage; see assumption A-2)
  - `implement` → `implementer-ivan`
  - `review` → `reviewer-renata`
- **AS-4:** Lane-state transitions during `implement` and `review` continue to use the typed status substrate (`emit_status_transition`); no raw string-literal lane handling is reintroduced.
- **AS-5:** Trail / event emission remains coherent: every composed step produces an invocation payload with a stable `invocation_id`, and the existing event-log writer captures one logical entry per action invocation.
- **AS-6:** A regression test exercises the live software-dev path for at least one action (recommended: `specify`) end-to-end through composition rather than only through executor unit tests.

### Edge cases

- **EC-1:** `tasks` action invoked when `plan.md` is missing. Composition must fail through the same CLI guard pathway that the legacy bridge uses (`_check_step_guards`), surfacing the same operator-facing error.
- **EC-2:** `implement` action invoked with no work packages in a startable lane. Composition must surface the same "no advance" condition, not silently no-op.
- **EC-3:** Profile hint passed explicitly via CLI overrides the action default (existing `_resolve_profile_hint` behavior preserved).
- **EC-4:** Mission step contract for a given action is missing. Composition must raise `StepContractExecutionError` with a clear message; the runtime bridge must propagate it as a non-zero exit / structured CLI error rather than crashing.
- **EC-5:** Legacy v0/v1 fields in `mission.yaml` (state machine, agent_context, task_metadata) remain readable; nothing outside this mission's scope depends on them, but removing them is out of scope for this slice.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The built-in `software-dev` mission's `specify`/`plan`/`tasks`/`implement`/`review` actions MUST execute through `StepContractExecutor` composing `ProfileInvocationExecutor` invocations on the live runtime path. | Active |
| FR-002 | A `tasks` step contract (or equivalent composition surface) MUST exist for the `software-dev` mission and internally cover the legacy `tasks_outline` → `tasks_packages` → `tasks_finalize` substructure. The `tasks` action remains the single public composition step (see assumption A-1). | Active |
| FR-003 | The runtime bridge MUST stop directly invoking the legacy `mission-runtime.yaml` step IDs (`specify`, `plan`, `tasks_outline`, `tasks_packages`, `tasks_finalize`, `implement`, `review`) for the built-in `software-dev` mission and instead delegate to composition for those actions. | Active |
| FR-004 | Existing CLI-level step guards (`_check_step_guards` in `runtime_bridge.py`) for the affected step IDs MUST continue to fire equivalently before each composed action completes (or be migrated into the composition pipeline with equivalent semantics). | Active |
| FR-005 | Action-surface calibration MUST be preserved: each action invokes through its own `(software-dev, <action>)` resolved context using `actions/<action>/index.yaml` as the governance scope. `specify` MUST NOT inherit implement-only directives; `implement` MUST keep its TDD/quality-gate slice; `review` MUST stay review-calibrated. | Active |
| FR-006 | Default profile-per-action mapping MUST match the calibration table in AS-3, sourced from `_ACTION_PROFILE_DEFAULTS` (extended with the `tasks` entry). Operator-supplied `--profile` MUST continue to override defaults. | Active |
| FR-007 | Lane-state transitions in `implement` and `review` MUST continue to use the typed status substrate (`emit_status_transition`, the 9-lane state machine). No raw string-literal lane writes may be reintroduced. | Active |
| FR-008 | Each composed action MUST emit a stable invocation payload that downstream event/trail writers can consume; the `invocation_id` chain MUST remain well-formed. | Active |
| FR-009 | When a step contract is missing for a `(software-dev, action)` pair on the live path, the runtime bridge MUST surface a structured CLI error (non-zero exit, clear message), NOT crash. | Active |
| FR-010 | The legacy `mission-runtime.yaml` v2.1.0 file MAY remain on disk as a transitional reference but MUST NOT be the authoritative source for action dispatch on the built-in `software-dev` mission once this slice lands. The plan MUST decide whether to delete it, mark it deprecated, or keep it as a read-only fallback. | Active |
| FR-011 | The legacy v0/v1 sections of `mission.yaml` (state machine, workflow.phases, commands.* prompts, task_metadata) MAY remain untouched in this slice. Cleanup is out of scope. | Active |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Live-path performance MUST NOT regress measurably for any of the five composed actions. | Per-action wall-clock within ±15% of pre-rewrite baseline measured on a single sample mission. | Active |
| NFR-002 | Test suite coverage for the rewrite MUST include at least one dedicated test exercising the `software-dev` mission through composition (not just executor unit tests). | One or more tests under `tests/specify_cli/` directly named for the software-dev composition rewrite. | Active |
| NFR-003 | Existing executor / runtime-bridge / agent-commands tests MUST continue to pass. | `tests/specify_cli/mission_step_contracts/test_executor.py`, `tests/specify_cli/next/test_runtime_bridge.py`, `tests/specify_cli/runtime/test_agent_commands_routing.py` all green. | Active |
| NFR-004 | The change MUST be reviewable as a contained slice. | Diff scoped to runtime bridge integration, software-dev mission step contracts, profile-defaults table, and dedicated tests. No incidental refactor of unrelated subsystems. | Active |

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | `StepContractExecutor` MUST remain a composer over `ProfileInvocationExecutor`. It MUST NOT be turned into a model-calling engine, shell runner, or LLM driver. | Active |
| C-002 | The host LLM / harness owns reading and generation. Spec Kitty owns routing, governance context assembly, validation, glossary checks, trail writing, provenance, and orchestration/composition. This boundary MUST NOT shift. | Active |
| C-003 | The typed status / lane substrate (the 9-lane state model and `emit_status_transition`) MUST be used. Raw string-literal lane handling MUST NOT be reintroduced anywhere this slice touches. | Active |
| C-004 | Custom mission loading (`#505`) is out of scope. No code path enabling user-defined missions may be added in this slice. | Active |
| C-005 | Retrospective gating, retrospective schema, synthesizer handoff, and cross-mission retrospective views (`#506`/`#507`/`#508`/`#509`/`#511`) are out of scope. None may be implemented here. | Active |
| C-006 | Phase 4 and Phase 5 work MUST NOT be reopened. `spec-kitty explain` and other deferred follow-ons stay deferred. | Active |
| C-007 | Fixing the `spec-kitty-events` package structure or the libraries-vs-`charter.md` alignment is out of scope. A concurrent agent owns that work; this slice MUST NOT touch those surfaces to avoid merge conflicts and ownership confusion. | Active |
| C-008 | The built-in `software-dev` mission is the live-path consumer for this slice. No second mission may be touched. | Active |

## Success Criteria

- **SC-1:** A real operator running `/spec-kitty.specify` → `/spec-kitty.plan` → `/spec-kitty.tasks` → `/spec-kitty.implement` → `/spec-kitty.review` against a sample mission produces the same artifact set and lane-state transitions as the pre-rewrite path, with composition (not the legacy DAG) doing the routing.
- **SC-2:** For each of the five public actions, the resolved governance context inspected on the wire matches the action-scoped `index.yaml` declarations (verifiable in tests via the `ResolvedContext` returned by `resolve_context`).
- **SC-3:** `tests/specify_cli/mission_step_contracts/`, `tests/specify_cli/next/`, and `tests/specify_cli/runtime/` plus a new dedicated software-dev-composition test suite all pass.
- **SC-4:** No regressions in `spec-kitty next`, `spec-kitty agent action`, or `spec-kitty agent tasks` for the built-in software-dev mission.

## Key Entities

- **`StepContractExecutor`** (`src/specify_cli/mission_step_contracts/executor.py`) — the composer. Loads a `MissionStepContract` for a `(mission, action)` pair, resolves the action context via the merged DRG, and routes each step through `ProfileInvocationExecutor`.
- **`MissionStepContract` / shipped contracts** (`src/doctrine/mission_step_contracts/shipped/<action>.step-contract.yaml`) — declarative step lists per action. Currently shipped: `specify`, `plan`, `implement`, `review`. **Missing:** `tasks`.
- **Action index** (`src/doctrine/missions/software-dev/actions/<action>/index.yaml`) — action-scoped governance declarations (directives, tactics, styleguides, toolguides, procedures).
- **Runtime bridge** (`src/specify_cli/next/runtime_bridge.py`) — the integration seam. Currently dispatches via `mission-runtime.yaml` step IDs and runs CLI guards in `_check_step_guards`. This slice rewires it to delegate to composition for the built-in `software-dev` mission.
- **Profile defaults table** (`_ACTION_PROFILE_DEFAULTS` in `executor.py`) — already covers `specify`/`plan`/`implement`/`review`; needs a `tasks` entry.
- **Legacy runtime template** (`src/doctrine/missions/software-dev/mission-runtime.yaml`) — v2.1.0 DAG with separate `tasks_outline`/`tasks_packages`/`tasks_finalize` steps. To be deprecated as the live-path source for action dispatch.

## Assumptions

- **A-1 (tasks-phase mapping decision):** `tasks` becomes the single public composition step. The legacy `tasks_outline` → `tasks_packages` → `tasks_finalize` split survives as **internal substructure** inside one `tasks.step-contract.yaml`. Rationale: preserves a 1:1 mapping with the public CLI surface (`/spec-kitty.tasks`), keeps substructure as a routing implementation detail, mirrors how `specify`/`plan`/`implement`/`review` are each one composition step, and avoids inflating the public action surface. **If the user prefers exposing all three sub-actions publicly, flip this in plan review.**
- **A-2 (tasks profile default):** `architect-alphonso` is reused as the `tasks` default profile, on the grounds that task decomposition is planning-adjacent. **If a dedicated `planner-*` profile exists or is preferred, swap in plan review.**
- **A-3 (legacy file disposition):** `mission.yaml` v0/v1 fields and `mission-runtime.yaml` are not deleted in this slice. The plan will pick: keep / mark deprecated / delete. Default leaning: **mark deprecated with a header comment**, leave files in place to minimize blast radius for parallel work and downstream pinning.
- **A-4 (events package boundary):** Anything related to fixing `spec-kitty-events` package layout or library-vs-`charter.md` alignment is owned by a concurrent agent and is excluded from this slice (C-007).

## Dependencies

- Composition substrate landed (`#501`/PR `#778`/commit `607a39d1ab7b8203274f3886e4d3d857a40b0c97`). ✅
- Typed status / lane substrate landed (9-lane model, `emit_status_transition`). ✅
- Per-action `index.yaml` files exist for all five actions. ✅ (verified)
- Shipped step contracts exist for `specify`, `plan`, `implement`, `review`. ✅
- Shipped step contract for `tasks` does NOT yet exist. Will be authored in this slice.

## Open Questions

None blocking; assumption table above captures the main fork. Plan phase will lock the tasks-mapping decision (A-1), tasks profile default (A-2), and legacy-file disposition (A-3) before writing the implementation plan.
