---
work_package_id: WP01
title: Full FSM ownership — edges + guards + force in WPState; no derived authority
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-012
- FR-015
- FR-021
- FR-022
tracker_refs:
- '1666'
planning_base_branch: mission/wp-lane-state-machine-fsm
merge_target_branch: mission/wp-lane-state-machine-fsm
branch_strategy: Planning artifacts for this mission were generated on mission/wp-lane-state-machine-fsm. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/wp-lane-state-machine-fsm unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Phase 1 - Foundation
assignee: ''
agent: claude
history:
- at: '2026-06-07T13:30:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/wp_state.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/status/wp_state.py
- src/specify_cli/status/transitions.py
- src/specify_cli/status/transition_context.py
- src/specify_cli/status/validate.py
- src/specify_cli/status/models.py
- src/specify_cli/status/__init__.py
- tests/specify_cli/status/test_wp_state.py
- tests/status/test_transitions.py
role: implementer
tags:
- fsm
- single-ownership
- behavior-preserving
task_type: implement
---

# Work Package Prompt: WP01 — Full FSM ownership (edges + guards + force in WPState)

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` for profile **`python-pedro`** (role: `implementer`) before reading anything else.

## Objective & Success Criteria

Make the `WPState` State objects the **single owner** of both the transition edge graph
AND the act of transitioning (guards + force). `validate_transition` becomes a thin
delegator. **No production code consults `ALLOWED_TRANSITIONS` (or any derived edge set)
as a gate.** Behavior is preserved for the nine pre-existing lanes.

- FR-001/001b/002/002b/003/012/015; NFR-001 (behavior preservation), NFR-002 (one owner), NFR-004 (lint/type clean). SC-001, SC-005.

## Context & Constraints

- Read `data-model.md` (the per-state edge+guard+force table) and `contracts/fsm-and-genesis-contracts.md` (Contract 1).
- **Operator directive**: do NOT trade one split-brain for another. A *derived* `ALLOWED_TRANSITIONS` that callers still consult via `(from,to) in …` is itself a second authority — eliminate that consumption.
- **Audit (do this early)**: `grep -rn "ALLOWED_TRANSITIONS" src/` and `grep -rn "allowed_targets()\|in ALLOWED_TRANSITIONS" src/`. Known production consumers: `transitions.py::validate_transition` (becomes the delegator) and `validate.py::validate_canonical_event:143` (`(from,to) in ALLOWED_TRANSITIONS` — migrate to the FSM). `status/__init__.py` re-exports the constant.
- **Behavior envelope**: the existing `tests/status/test_transitions.py` + `tests/specify_cli/status/test_wp_state.py` are the contract. They must stay green at every step.

## Branch Strategy

- **Planning base / merge target**: `mission/wp-lane-state-machine-fsm`. Execution worktree is the WP01 lane from `lanes.json`.
- Implement command: `spec-kitty agent action implement WP01 --agent <name>`.

## Subtasks & Detailed Guidance

### T007 (do FIRST — ATDD) — Behavior-preservation parity suite
- Author/extend a parametrized test that asserts, for the FULL historical `(from, to, ctx)` matrix (every guarded transition + force cases + terminal force-exit), the SAME `(ok, error_message)` decision as `main`/baseline. Capture the baseline truth table first. This is the RED-first envelope; keep it green through T001–T006.
- Files: `tests/status/test_transitions.py`, `tests/specify_cli/status/test_wp_state.py`.

### T001 — Guards into the State objects
- Move each guard from `transitions._GUARDED_TRANSITIONS` into the *source* state's `can_transition_to(target, ctx)`: PlannedState→claimed (actor); ClaimedState→in_progress (workspace_context); InProgressState→for_review (subtasks_complete_or_force) and →approved (reviewer_approval); ForReviewState→in_review (reviewer claim); InReviewState outbound (ReviewResult required); ApprovedState→done (done-evidence).
- Each state owns ITS entry conditions. Keep `GuardContext`/`TransitionContext` as the input.
- Files: `src/specify_cli/status/wp_state.py`, `transition_context.py`.

### T002 — Force-override into `transition_to`
- `transition_to(target, ctx)` honours `ctx.force` (requires actor + reason): a forced transition not in `allowed_targets()` is permitted exactly where the old `validate_transition` force branch permitted it — including terminal `done`/`canceled` → any lane. Raise `InvalidTransitionError`/return the structured rejection otherwise.
- Add a dedicated terminal force-exit parity test.
- Files: `src/specify_cli/status/wp_state.py`.

### T003 — `validate_transition` becomes a thin delegator
- Rewrite `validate_transition(from, to, ctx) -> (ok, error_message)` to resolve aliases then delegate to `wp_state_for(resolved_from)` (a `can_transition_to`-style call that returns the `(ok, error)` shape). No edge/guard/force logic remains in `transitions.py`.
- Files: `src/specify_cli/status/transitions.py`.

### T004 — Eliminate `ALLOWED_TRANSITIONS` as an authority
- Migrate `validate.py::validate_canonical_event` to decide edge legality via the FSM (e.g. `wp_state_for(from).may_transition_to(to)`), not `(from,to) in ALLOWED_TRANSITIONS`.
- Remove `ALLOWED_TRANSITIONS` or relegate it to a clearly-commented non-authoritative derived projection (tests/graph only); drop or annotate the `status/__init__.py` export accordingly. No production gate may consult it.
- Files: `src/specify_cli/status/validate.py`, `transitions.py`, `status/__init__.py`.

### T005 — `validate.py`: genesis is `from_lane`-only
- Accept `genesis` as a valid `from_lane`; flag `to_lane=genesis` as non-canonical (FR-015).
- Files: `src/specify_cli/status/validate.py`.

### T006 — Architectural test: FSM is the sole edge+transition authority
- A test that greps/asserts no production module under `src/` imports `ALLOWED_TRANSITIONS` for an edge gate, and that the only edge authority is `WPState.allowed_targets()`.
- Files: `tests/specify_cli/status/test_wp_state.py` (or a new architectural test under the WP's owned tests).

## Test Strategy
- T007 parity suite green throughout (behavior preservation, NFR-001). Targeted run: `python -m pytest tests/status/test_transitions.py tests/specify_cli/status/test_wp_state.py tests/status/test_validate*.py -q`. `ruff` + `mypy` clean on touched files (NFR-004); no new disabled checks.

## Definition of Done
- Guards + force live in the State objects; `validate_transition` delegates; no production `ALLOWED_TRANSITIONS` gate remains; genesis `from_lane`-only; parity + architectural tests green; behavior preserved.

## Risks & Mitigations
- Intricate guard matrix → migrate guard-by-guard keeping the envelope green. An overlooked derived-set gate re-introduces the split-brain → the audit (T004/T006) must be exhaustive.

## Review Guidance — **Persona ICs: Paula-Patterns (single-ownership) + Randy-Reducer (no derived debt); reviewer: reviewer-renata**
- Paula: confirm exactly ONE authority for edges AND transitions; no parallel/derived gate survives.
- Randy: confirm the old literal is gone (not duplicated); the derived projection, if kept, is non-authoritative and earns its keep.
- Renata: verify behavior preservation (parity suite is non-vacuous: RED on the base for a deliberately-broken guard), terminal force-exit parity, and genesis `from_lane`-only.

## Activity Log
- 2026-06-07 — system — Prompt created.
