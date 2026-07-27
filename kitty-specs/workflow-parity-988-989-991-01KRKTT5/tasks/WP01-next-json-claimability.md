---
work_package_id: WP01
title: next --json claimability parity
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-010
- C-001
planning_base_branch: fix/workflow-parity-988-989-991
merge_target_branch: fix/workflow-parity-988-989-991
branch_strategy: Planning artifacts for this mission were generated on fix/workflow-parity-988-989-991. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/workflow-parity-988-989-991 unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
agent: claude
history:
- at: '2026-05-14T18:15:00Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/next/
execution_mode: code_change
mission_slug: workflow-parity-988-989-991-01KRKTT5
owned_files:
- src/specify_cli/next/**
- src/specify_cli/cli/commands/next_cmd.py
- tests/next/test_next_claimable_payload.py
role: implementer
tags: []
---

# WP01 — `next --json` claimability parity (#988)

## ⚡ Do This First: Load Agent Profile

Before reading the rest of this WP, load the assigned agent profile via:

```
/ad-hoc-profile-load python-pedro
```

This injects the Python implementation doctrine for this codebase.

## Objective

Align the `spec-kitty next --json` payload with the canonical claim algorithm used by `spec-kitty agent action implement`. When the explicit implement action would auto-claim a WP, `next --json` must serialize that concrete `wp_id`. When selection is intentionally suppressed, the payload must include a structured `selection_reason`.

## Context

- Bug report: https://github.com/Priivacy-ai/spec-kitty/issues/988
- Spec: [../spec.md](../spec.md) (see FR-001..FR-003, FR-010, C-001)
- Research: [../research.md](../research.md) (`#988` section)
- Contract: [../contracts/next-json-claimability.md](../contracts/next-json-claimability.md)

### Code map (read these first)

- Payload builder: `src/specify_cli/next/decision.py:115` — `Decision.to_dict()`
- CLI emission: `src/specify_cli/cli/commands/next_cmd.py:353` — `_print_decision()`
- Current "first WP by lane" primitive: `src/specify_cli/next/decision.py:338` — `_find_first_wp_by_lane()`
- Canonical claim algorithm: `src/specify_cli/status/work_package_lifecycle.py:98` — `start_implementation_status()`

## Branch Strategy

- Planning/base branch: `fix/workflow-parity-988-989-991`
- Final merge target: `fix/workflow-parity-988-989-991` → ultimately `main` (per `start-here.md`)
- This WP runs on the shared feature branch (no per-lane worktree); only `lanes.json` driven flows allocate worktrees.

## Subtasks

### T001 — Add `ClaimablePreview` dataclass + `preview_claimable_wp()` helper

**Purpose**: Provide a side-effect-free preview of the claim algorithm so the `next` payload can match the explicit action without mutating state.

**Steps**:
1. Create or extend `src/specify_cli/next/discovery.py` (or, if simpler, add the helper to `src/specify_cli/next/decision.py` alongside `_find_first_wp_by_lane`).
2. Define `ClaimablePreview` as a frozen dataclass with fields:
   - `wp_id: str | None`
   - `selection_reason: str | None`
   - `candidates: tuple[str, ...]`
3. Define `preview_claimable_wp(feature_dir: Path, *, mission_meta: MissionMeta) -> ClaimablePreview`:
   - Walk the same candidate set `start_implementation_status()` walks (planned WPs whose dependencies are satisfied, ordered the same way).
   - If at least one candidate is selectable → set `wp_id` to the first selectable WP, leave `selection_reason=None`.
   - Else → set `wp_id=None` and choose a stable token for `selection_reason`: `"no_planned_wps"`, `"all_wps_in_progress"`, `"dependencies_unsatisfied"`, or `"baseline_violation"`.
4. Add `__all__` exports for both names.

**Files**:
- `src/specify_cli/next/discovery.py` (new, ~80 lines including type hints)
- `src/specify_cli/next/__init__.py` (re-export)

**Validation**:
- [ ] `mypy --strict src/specify_cli/next/discovery.py` passes.
- [ ] Helper does not call any function that mutates the event log or filesystem state outside the read path.

### T002 — Wire `next --json` payload to populate `wp_id` + `selection_reason`

**Purpose**: Use the helper from T001 inside the JSON payload builder so the wire contract matches [../contracts/next-json-claimability.md](../contracts/next-json-claimability.md).

**Steps**:
1. In `Decision.to_dict()` (or the closest peer that builds the dict before serialization), detect `mission_state == "implement"` AND `preview_step == "implement"`.
2. When the condition holds, call `preview_claimable_wp(...)` and merge `wp_id` and `selection_reason` into the dict.
3. Preserve the existing wire shape for any other `mission_state` (do not introduce these keys outside the implement state — spec C-001).
4. Replace any duplicate logic that currently re-derives `wp_id` from `_find_first_wp_by_lane` with the new helper (FR-003: single implementation path).

**Files**:
- `src/specify_cli/next/decision.py` (modify, ~30 lines net change)
- `src/specify_cli/cli/commands/next_cmd.py` (modify only if the printer needs to know the new field shape; typically untouched if the dict already round-trips)

**Validation**:
- [ ] The JSON payload contains `wp_id` (concrete or null) and `selection_reason` (null or string) for the implement state.
- [ ] The JSON payload for non-implement states is byte-for-byte identical to today (run a smoke command pre/post on a non-implement mission).

### T003 — Regression test `tests/next/test_next_claimable_payload.py`

**Purpose**: Lock the FR-001/FR-002 contract.

**Steps**:
1. Add a pytest module under `tests/next/`. Use the existing mission/status scaffolding fixtures (`tests/next/test_next_command_integration.py` is the nearest example to crib from).
2. Test cases:
   - `test_implement_state_with_one_planned_wp_returns_wp_id`: Create a mission with one `planned` WP whose dependencies are satisfied. Call `next --json` programmatically. Assert `payload["wp_id"] == "WP01"` and `payload["selection_reason"] is None`.
   - `test_implement_state_with_only_in_progress_wps_returns_selection_reason`: Same mission, mark `WP01` as `in_progress` via the canonical event log API. Assert `payload["wp_id"] is None` and `payload["selection_reason"] in {"all_wps_in_progress", ...}` (the exact token defined in the helper).
   - `test_non_implement_state_payload_shape_unchanged`: Use a mission in a non-implement state and assert the payload does NOT contain a `wp_id` key (or contains it with its pre-existing value if it already existed) — i.e. wire shape regression.

**Files**:
- `tests/next/test_next_claimable_payload.py` (new, ~120 lines)

**Validation**:
- [ ] Tests fail against the pre-fix code (`wp_id` is null in scenario 1).
- [ ] Tests pass against the post-fix code.
- [ ] `uv run pytest tests/next/test_next_claimable_payload.py -q` runs in under 2 seconds.

## Definition of Done

- [ ] All three subtasks complete and committed.
- [ ] Contract [../contracts/next-json-claimability.md](../contracts/next-json-claimability.md) is satisfied.
- [ ] `uv run pytest tests/next/ tests/specify_cli/cli/commands/test_next.py -q` is green (existing + new tests).
- [ ] `uv run mypy --strict src/specify_cli/next` is green.
- [ ] `uv run ruff check src/specify_cli/next tests/next/test_next_claimable_payload.py` is green.

## Risks & Mitigations

- **R-1**: Re-deriving candidate selection drifts from `start_implementation_status()`.
  - **Mitigation**: Place the helper next to the existing claim algorithm OR have the helper import the claim algorithm's internal selector. Add a test that asserts the helper's `candidates` matches the order `start_implementation_status` would have walked.
- **R-2**: Wire-shape change for non-implement states breaks consumers.
  - **Mitigation**: Conditional emission of `wp_id`/`selection_reason` only in implement state (spec C-001).

## Reviewer guidance

- Re-read `Decision.to_dict()` before/after the diff and confirm only the implement branch grew new fields.
- Look for any duplicate "which WP would we claim" logic outside the new helper — remove or call into the helper.
- Spot-check `selection_reason` token strings against the data-model document.
