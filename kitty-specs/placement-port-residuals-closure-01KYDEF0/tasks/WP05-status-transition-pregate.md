---
work_package_id: WP05
title: status_transition pre-gate adoption (behavior change)
dependencies:
- WP04
requirement_refs:
- FR-005
planning_base_branch: placement-port-residuals
merge_target_branch: placement-port-residuals
branch_strategy: Planning artifacts for this mission were generated on placement-port-residuals. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into placement-port-residuals unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
history:
- at: '2026-07-25T21:12:34Z'
  actor: tasks
  note: WP created from IC-06b (FR-005, C-004 behavior change)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/
create_intent:
- tests/specify_cli/coordination/test_status_transition_degrade.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/coordination/status_transition.py
- tests/specify_cli/coordination/test_status_transition_degrade.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

**Before reading anything else**, load `python-pedro` (role `implementer`) via `/ad-hoc-profile-load`;
adopt its directives/tactics and state which you applied. Then proceed.

## Objective

Adopt `coordination/status_transition.py::_resolve_write_target` onto the shared
`resolve_write_target_or_degrade` helper (from WP04). This ADDS the `_mission_meta_exists` pre-gate it lacks
today — a **real behavior change** (C-004) — while preserving its `get_feature_target_branch` degrade and its
COORD routing for `STATUS_STATE`.

Read first: `spec.md` (FR-005, C-004), `plan.md` (IC-06b), `contracts/degrade-and-read-hygiene.md`.

## Context

- `status_transition._resolve_write_target` (`:638-703`) today has NO `_mission_meta_exists` pre-gate; it calls
  `resolve_placement_only(..., STATUS_STATE).ref` in a `try` and degrades via
  `coord_branch or get_feature_target_branch(repo_root, mission_slug)` on `(ActionContextError, StatusReadPathNotFound, FileNotFoundError)`.
- Its own docstring notes the port "never raises for a merely-absent mission" — so its bootstrap-window degrade
  is structurally weaker than the two WP04 clones. Adding the pre-gate makes the absent-mission degrade explicit.
- `STATUS_STATE` is a COORD kind — it MUST keep resolving to the coord ref (C-004). The helper is kind-parameterized.

## Subtasks

### T021 — Red-first (behavior change coverage)
In `tests/specify_cli/coordination/test_status_transition_degrade.py`, assert the NEW behavior: in the
no-`meta.json` window, `_resolve_write_target` degrades through the shared helper's pre-gate to
`degrade_ref = coord_branch or get_feature_target_branch(...)`; and for a bootstrapped mission, `STATUS_STATE`
resolves to the COORD ref. Confirm the pre-gate branch is RED (not taken) before the change.

### T022 — Adopt the helper
Route `_resolve_write_target` through `resolve_write_target_or_degrade(repo_root, mission_slug, STATUS_STATE, degrade_ref=coord_branch or get_feature_target_branch(repo_root, mission_slug))`.
Preserve the existing typed-exception degrade semantics; keep the coord routing. Do NOT hardcode PRIMARY.

### T023 — Verify C-004 + clean
Assert `STATUS_STATE` still degrades to the coord ref (never PRIMARY). Red-first test green. `ruff` + `mypy --strict`
clean. Run `PWHEADLESS=1 pytest tests/specify_cli/coordination/ -q` and the status-emit path tests — no regression.

## Branch Strategy
Planning base / merge target `placement-port-residuals`. Worktree per `lanes.json` via
`spec-kitty agent action implement WP05 --agent claude`. Depends on WP04 (Lane B).

## Definition of Done
- [ ] `_resolve_write_target` routes through the shared helper; pre-gate added (behavior change) with dedicated test.
- [ ] `STATUS_STATE` stays COORD-routed (C-004); degrade preserved.
- [ ] ruff/mypy clean; coordination + status-emit tests green.

## Risks / reviewer guidance
- The added pre-gate changes behavior in the merely-absent window — the test must pin it explicitly.
- Reviewer: confirm no coord→PRIMARY flattening; confirm `get_feature_target_branch` degrade preserved.
