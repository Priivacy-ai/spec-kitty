---
work_package_id: WP04
title: SaaS genesis fidelity via spec_kitty_events enum bump
dependencies:
- WP01
requirement_refs:
- FR-010
- FR-011
tracker_refs:
- '1666'
planning_base_branch: mission/wp-lane-state-machine-fsm
merge_target_branch: mission/wp-lane-state-machine-fsm
branch_strategy: Planning artifacts for this mission were generated on mission/wp-lane-state-machine-fsm. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/wp-lane-state-machine-fsm unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
- T023
phase: Phase 2 - SaaS
assignee: ''
agent: claude
history:
- at: '2026-06-07T13:30:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/emitter.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/sync/emitter.py
- src/specify_cli/status/emit.py
- pyproject.toml
role: implementer
tags:
- saas
- external-contract
- spec-kitty-events
task_type: implement
---

# Work Package Prompt: WP04 — SaaS genesis fidelity (spec_kitty_events enum bump)

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` for profile **`python-pedro`** (role: `implementer`).

## Objective & Success Criteria

The `genesis → planned` seed fans out to SaaS as a real transition (not dropped). Add
`genesis` to the external `spec_kitty_events.Lane` via the owning-package workflow;
single-source the local `_PAYLOAD_RULES` lane set.

- FR-010, FR-011; C-004 (Decision DM-01KTH03H); NFR-005. SC-004.

## Context & Constraints

- Review F1/alphonso-3 (`research/review-paula-patterns.md`, `review-architect-alphonso.md`): `spec_kitty_events.Lane` (v5.2.0) lacks `genesis`, so the seed fails pydantic validation in `_saas_fan_out`/`sync/emitter.py:270-271` and is dropped with only a console warning.
- **Decision DM-01KTH03H**: bump the external enum (NOT the in-repo `from_lane=None` workaround).
- **Shared Package Boundary charter (binding)**: `spec_kitty_events` is a true external PyPI dependency. Change the package repo FIRST, publish a versioned artifact with compatibility notes, then update CLI constraints. **No committed path/editable/branch overrides** in `pyproject.toml [tool.uv.sources]`.
- Depends on WP01.

## Branch Strategy
- Base/merge: `mission/wp-lane-state-machine-fsm`; lane worktree per `lanes.json`. `spec-kitty agent action implement WP04 --agent <name>`.

## Subtasks & Detailed Guidance

### T019 — (External) Add `genesis` to `spec_kitty_events.Lane`
- In the `spec-kitty-events` package repo: add the `genesis` enum member; update `StatusTransitionPayload`/`WPStatusChanged` to accept `from_lane=genesis`; add compatibility notes; publish a versioned artifact. **This is a separate repo + release — coordinate it before T020.** If the release cannot be produced in this WP's window, stop and escalate (do NOT commit a path/editable override).

### T020 — Update CLI dependency constraint
- `pyproject.toml`: bump the `spec-kitty-events` version constraint to the genesis-aware release; update the lockfile. No path/editable overrides.

### T021 — Single-source the SaaS lane validator
- `sync/emitter.py`: derive `_PAYLOAD_RULES["WPStatusChanged"]`'s accepted lane set from the canonical lane source (incl. genesis), not a hardcoded 9-lane list.

### T022 — Faithful fan-out + compatibility gate
- `status/emit.py::_saas_fan_out`: emit the genesis seed without a swallowed `ValidationError`. Add a capability/version gate so older `spec_kitty_events` (pre-genesis) degrades gracefully during the rollout window. Fix the stale emit pipeline docstring "(or 'planned')" → "(or 'genesis' for unseeded WPs)".

### T023 — Tests
- A genesis seed produces a contract-valid SaaS payload; a consumer/compatibility fixture covers both old (no-genesis) and new `spec_kitty_events`.

## Test Strategy
- Targeted: `python -m pytest tests/sync/ tests/status/test_emit*.py -q`. `ruff`+`mypy` clean. Run the clean-install/boundary architectural tests if touched.

## Definition of Done
- `spec_kitty_events` released with genesis; CLI constraint bumped (no overrides); `_PAYLOAD_RULES` single-sourced; genesis seed fans out validly with a compat gate; tests green.

## Risks & Mitigations
- External release coordination (the highest-risk item). If the release isn't available, gate the CLI to not crash and escalate — do not improvise an override.

## Review Guidance — **Persona ICs: Paula-Patterns; reviewer: reviewer-renata**
- Paula: no parallel hardcoded lane list survives; the external contract is updated in lock-step (no silent drop). Renata: the compatibility gate is real; no path/editable override committed (Shared Package Boundary).

## Activity Log
- 2026-06-07 — system — Prompt created.
