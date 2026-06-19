---
work_package_id: WP05
title: Typed-error pass-through (cheapest behavioral slice)
dependencies:
- WP03
requirement_refs:
- FR-005
tracker_refs: []
planning_base_branch: feat/single-mission-surface-resolver
merge_target_branch: feat/single-mission-surface-resolver
branch_strategy: Planning artifacts for this mission were generated on feat/single-mission-surface-resolver. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-mission-surface-resolver unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
agent: claude
history:
- at: '2026-06-19T17:06:54Z'
  actor: claude
  note: 'WP authored from plan IC-04 (FR-005, #2010 bug #15).'
agent_profile: python-pedro
authoritative_surface: src/mission_runtime/
create_intent:
- tests/mission_runtime/test_resolution_typed_errors.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/mission_runtime/resolution.py
- tests/mission_runtime/test_resolution_typed_errors.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load `python-pedro`; acknowledge its initialization declaration.

## Objective
Preserve `STATUS_READ_PATH_NOT_FOUND` / `MISSION_AMBIGUOUS_SELECTOR` end-to-end through `next` / `mission_runtime` instead of flattening to `MISSION_NOT_FOUND` (#2010 bug #15). The cheapest behavioral slice — NO resolver change, highest-blast-radius desync symptom. (IC-04; FR-005)

## Context
- `src/mission_runtime/resolution.py` (the caller boundary, ~lines 180-218 / the `resolve_status_surface` wrappers) translates/flattens typed errors. The error types already exist in `_read_path_resolver.py`.
- Re-point resolution.py to the WP03 shared delegator and let the typed errors propagate; map them to preserved exit codes through `next`. If the flattening also happens in a `runtime_bridge` caller, fix that site too (rationale-noted leeway if outside owned_files).

## Subtasks
### T018 — Preserve typed errors
- In `resolution.py`, stop collapsing `STATUS_READ_PATH_NOT_FOUND`/`MISSION_AMBIGUOUS_SELECTOR` to `MISSION_NOT_FOUND`; propagate the specific code through the `next`/runtime boundary. Reuse the WP03 delegator.
### T019 — Reproduce bug #15 red→green
- Add a test reproducing #2010 bug #15 (a read-path-not-found / ambiguous handle surfacing through `next` as `MISSION_NOT_FOUND`); show it red pre-fix, green post-fix (the specific code survives).
### T020 — Gates
- `ruff` + `mypy --strict` clean; run `tests/mission_runtime/` + any `next` command tests.

## Branch Strategy
Planning/base + merge target: `feat/single-mission-surface-resolver`. Worktree per lane. Depends **WP03** (delegator).

## Definition of Done
- [ ] `STATUS_READ_PATH_NOT_FOUND`/`MISSION_AMBIGUOUS_SELECTOR` preserved through next/mission_runtime (not flattened).
- [ ] Bug #15 reproduction test red→green.
- [ ] No resolver behavior changed (this is a caller-boundary fix).
- [ ] ruff + mypy --strict clean.

## Risks / Reviewer guidance
- **Risk**: a `runtime_bridge` caller may also flatten — verify the WHOLE path to `next` preserves the code, not just `resolution.py`.
- **Reviewer**: confirm the bug-#15 test asserts the SPECIFIC code (not just "an error"); confirm no resolver logic changed.
