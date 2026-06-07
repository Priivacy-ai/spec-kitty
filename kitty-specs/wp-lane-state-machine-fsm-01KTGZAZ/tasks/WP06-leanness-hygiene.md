---
work_package_id: WP06
title: Leanness & hygiene — shared seed fixture, lock-in FSM API, no debt
dependencies:
- WP01
- WP02
- WP03
- WP04
requirement_refs:
- FR-016
- FR-017
- FR-018
- FR-020
tracker_refs:
- '1666'
planning_base_branch: mission/wp-lane-state-machine-fsm
merge_target_branch: mission/wp-lane-state-machine-fsm
branch_strategy: Planning artifacts for this mission were generated on mission/wp-lane-state-machine-fsm. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/wp-lane-state-machine-fsm unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
- T030
- T031
phase: Phase 3 - Leanness
assignee: ''
agent: claude
scope: codebase-wide
history:
- at: '2026-06-07T13:30:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: tests/status/conftest.py
execution_mode: code_change
model: ''
owned_files:
- tests/status/conftest.py
- tests/conftest.py
- tests/utils.py
- src/specify_cli/status/bootstrap.py
role: implementer
tags:
- leanness
- hygiene
- test-fixtures
task_type: implement
---

# Work Package Prompt: WP06 — Leanness & hygiene

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` for profile **`randy-reducer`** (role: `implementer`). This WP is a leanness pass — apply behavior-preserving reduction.

## Objective & Success Criteria

Remove the avoidable complexity surfaced by the leanness lens: one shared seed fixture
(not 12 copies), the operator-mandated FSM API locked in by real callers, the redundant
bootstrap `force` dropped, remaining stale docstrings fixed, the tautological count test
annotated.

- FR-016, FR-017, FR-018, FR-020; NFR-003; US8 (review randy + paula-4/5). SC-006.

## Context & Constraints

- `research/review-randy-reducer.md`: 12 duplicated `_seed_planned` helpers; three zero-caller FSM interface methods (operator-mandated — KEEP, lock in); stale `tests/utils.py` PLANNED default; redundant bootstrap `force=True`; genesis-in-summary (handled by WP03).
- **`scope: codebase-wide`** — this WP edits many test files to remove the `_seed_planned` copies; it is the cross-cutting hygiene WP. Run it LAST (depends on WP01–WP04) so the FSM API and call sites are stable before lock-in.
- **C-003 / operator directive**: do NOT remove `current_lane`/`may_transition_to`/`transition_to` — they are the mandated public FSM API. Lock them in (T029), don't delete.

## Branch Strategy
- Base/merge: `mission/wp-lane-state-machine-fsm`; lane worktree per `lanes.json`. `spec-kitty agent action implement WP06 --agent <name>`.

## Subtasks & Detailed Guidance

### T027 — Consolidate the seed helpers
- Replace the ~12 per-file `_seed_planned` definitions with ≤2 shared fixtures: one in `tests/status/conftest.py` (covers `tests/status/` + `tests/specify_cli/status/`) and, if needed, one in `tests/conftest.py` for the rest (`tests/agent/`, `tests/integration/`, `tests/lanes/`, `tests/sync/`, `tests/cli/`). Provide a `seed_to_planned(feature_dir, wp_id, slug=...)` callable. Remove the copies.

### T028 — Fix stale test util default
- `tests/utils.py::_seed_canonical_wp_state`: replace the `Lane(current_lane or "planned")` default so it does not fabricate an illegal `planned` event for a now-genesis WP (use `genesis` or require an explicit seed).

### T029 — Lock in the FSM API (FR-017)
- Migrate a handful of real call sites to use `current_lane`/`may_transition_to`/`transition_to` (e.g. a reader using `wp_state_for(x).current_lane`, an edge check using `.may_transition_to`) so the operator-mandated interface has ≥1 production/test caller and is not dead. Keep within this WP's owned files or coordinate if a call site is owned by another WP.

### T030 — Drop redundant bootstrap force
- `status/bootstrap.py`: the guard-free `genesis→planned` seed no longer needs `force=True` (post-WP01 the transition is a real allowed edge). Drop it, or add a one-line note if intentional. Don't record `"force": true` on every seed.

### T031 — Annotate the tautological test
- Add a comment to the equivalence / `test_transition_count` test explaining it is tautological-by-design now that `ALLOWED_TRANSITIONS` is derived (it confirms the derivation ran + the count).

## Test Strategy
- Targeted re-run of the suites whose `_seed_planned` you touched: `python -m pytest tests/status/ tests/specify_cli/status/ tests/sync/ tests/lanes/ -q`. `ruff`+`mypy` clean. Behavior unchanged.

## Definition of Done
- ≤2 shared seed fixtures (copies removed); FSM API has real callers; bootstrap force dropped; stale defaults/docstrings fixed; tautological test annotated; suites green.

## Risks & Mitigations
- Cross-cutting test edits — keep behavior identical; run after WP01–WP04.

## Review Guidance — **Persona ICs: Randy-Reducer (leanness) + Paula-Patterns; reviewer: reviewer-renata**
- Randy: net reduction (12→≤2 fixtures); no dead API (methods now have callers); no new redundancy. Renata: behavior preserved; the operator-mandated API was locked in, not removed.

## Activity Log
- 2026-06-07 — system — Prompt created.
