---
work_package_id: WP03
title: Dry-run forecast reuses the retention resolver
dependencies:
- WP01
requirement_refs:
- FR-008
planning_base_branch: fix/3131-merge-retention
merge_target_branch: fix/3131-merge-retention
branch_strategy: Planning artifacts for this mission were generated on fix/3131-merge-retention. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/3131-merge-retention unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
history:
- at: '2026-08-31T16:30:00Z'
  actor: claude
  action: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/merge/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/merge/forecast.py
- tests/merge/test_forecast_seam.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
Before reading further, load your assigned agent profile via `/ad-hoc-profile-load python-pedro` (role: implementer). Then read `contracts/retention-resolver-contract.md` → "Consumption contract" item 2 — AUTHORITATIVE.

## Objective

Make `spec-kitty merge --dry-run` report the RESOLVED cleanup decision + a
retention-conflict note, instead of echoing raw flags (spec FR-008, US4, SC-003).
Depends on WP01's `resolve_merge_retention`.

## Context — read, do not re-derive
- `src/specify_cli/merge/forecast.py` — `run_dry_run_forecast` (~131) takes
  `delete_branch`/`remove_worktree` as bool and echoes them raw into the payload
  (~223-226). It already resolves PRIMARY dirs for other facts (~188-192).
- The forecast does NOT go through `_run_lane_based_merge`, so it must call the
  resolver itself (that is why the resolver is a standalone pure function).

## Subtask guidance

### T012 — Reuse the resolver in forecast
- `run_dry_run_forecast` signature: accept the tri-state (`bool | None`) flags
  (thread from the CLI dry-run dispatch, which shares the merge flags).
- Resolve against the primary meta dir it already computes; replace the raw echo
  at ~223-226 with the RESOLVED `delete_branch`/`remove_worktree` and add a
  `retention` object: `{"branch_source": ..., "worktree_source": ..., "warnings": [...]}`.
- Keep all other payload keys byte-identical; keep complexity ≤15.

### T013 — Forecast test update
- Update `tests/merge/test_forecast_seam.py` golden key-set assertion (~44) to
  include the new `retention` key. Flag this golden-key change in the PR body.
- Add a case: a retaining mission's forecast shows `delete_branch: false`,
  `remove_worktree: false`, and `retention.branch_source == "meta"`.

## Branch Strategy
Planning base and final merge target: `fix/3131-merge-retention`. Depends on WP01.

## Definition of Done
- Forecast reports resolved values + `retention` provenance; no raw flag echo.
- Golden-key test updated; retaining-mission forecast case green.
- `ruff` + `mypy --strict` clean.

## Test surface
`PWHEADLESS=1 pytest tests/merge/test_forecast_seam.py -q`

## Reviewer guidance
- Confirm forecast uses the SAME `resolve_merge_retention` (no second resolver impl).
- Confirm the payload key set change is intentional and documented.
