---
work_package_id: WP07
title: CLI path + golden-contract hygiene
dependencies: []
requirement_refs:
- FR-009
- FR-010
planning_base_branch: placement-port-residuals
merge_target_branch: placement-port-residuals
branch_strategy: Planning artifacts for this mission were generated on placement-port-residuals. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into placement-port-residuals unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-placement-port-residuals-closure-01KYDEF0
base_commit: cb67d191bb45180608ee28d66a91a9758cc18529
created_at: '2026-07-26T20:47:46.758997+00:00'
subtasks:
- T027
- T028
- T029
history:
- at: '2026-07-25T21:12:34Z'
  actor: tasks
  note: WP created from IC-08 (FR-009, FR-010)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent: []
execution_mode: code_change
model: claude-haiku-4-5-20251001
owned_files:
- src/specify_cli/cli/commands/agent/mission_repair.py
- tests/architectural/test_no_raw_mission_spec_paths.py
- tests/specify_cli/cli/commands/agent/test_mission_cli_golden_contract.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

**Before reading anything else**, load `python-pedro` (role `implementer`) via `/ad-hoc-profile-load`;
adopt its directives/tactics and state which you applied. Then proceed.

## Objective

Green `test_no_raw_mission_spec_paths` at `mission_repair.py:65` (FR-009) and reconcile the mission-CLI
golden contract for the sanctioned `agent mission repair` command including its flag surface (FR-010).

Read first: `spec.md` (FR-009, FR-010), `contracts/gate-reconciliation.md` (C-CLI-1, C-CLI-2).

## Context

- RED: `test_no_raw_mission_spec_paths::test_constant_based_mission_spec_path_construction_stays_in_constructor_files`
  — offender `mission_repair.py:65` `mission_dir: Path = repo_root / KITTY_SPECS_DIR / mission`.
- RED: `test_app_exposes_exactly_eight_frozen_commands` — `repair` is a genuinely-wired 9th command
  (`mission.py` `app.command(name="repair")`), frozen `_EXPECTED_COMMANDS` still says 8.
- `_EXPECTED_FLAGS` / `_EXPECTED_POSITIONALS` are parametrized separately — adding `repair` to `_EXPECTED_COMMANDS`
  alone greens the count while leaving repair's flag surface unverified (fakeable — reject).
- `test_repair_command_registered_on_mission_app` PASSED locally / failed CI → verify-on-CI (not assumed a defect).

## Subtasks

### T027 — FR-009: fix the raw mission-spec path
Either route `mission_repair.py:65` through the canonical mission-dir constructor the gate sanctions, OR add
`mission_repair.py` to the `test_no_raw_mission_spec_paths` constructor-file allow-list with a rationale.
Prefer routing through the canonical constructor if one exists (`_mission_dir`/`mission_feature_resolution`);
allow-list only if the module legitimately owns its own path vocabulary. Verify the gate greens.

### T028 — FR-010: reconcile the golden contract
- Add `repair` to `_EXPECTED_COMMANDS` (8→9).
- Add `_EXPECTED_FLAGS["repair"]` (and `_EXPECTED_POSITIONALS["repair"]` if any) pinning repair's actual
  `--mission`/flag/positional surface.
- Rename `test_app_exposes_exactly_eight_frozen_commands` (and its "exactly the 8" docstring) to the new count.
- Add the `repair` row to `kitty-specs/decompose-mission-god-module-01KVXHF8/contracts/cli-surface-contract.md` (**out-of-map**: not in `owned_files` — WPs cannot own kitty-specs paths; small rationale-backed doc edit).

### T029 — Verify
Golden-contract suite green including the repair flag-surface parametrization. Confirm
`test_repair_command_registered_on_mission_app` passes (verify-on-CI note). `ruff` + `mypy --strict` clean.

## Branch Strategy
Planning base / merge target `placement-port-residuals`. Worktree per `lanes.json` via
`spec-kitty agent action implement WP07 --agent claude`. Lane C (independent; split-candidate).

## Definition of Done
- [ ] Raw-path gate green (FR-009); golden-contract green with `repair` name + flag surface pinned (FR-010).
- [ ] Count test + docstring renamed 8→9; `cli-surface-contract.md` has the `repair` row.
- [ ] ruff/mypy clean.

## Risks / reviewer guidance
- Do NOT green the count test without pinning repair's flag surface (fakeable acceptance).
- Reviewer: confirm `_EXPECTED_FLAGS["repair"]` matches the real registered flags; confirm the contract doc row.
