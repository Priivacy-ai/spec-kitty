---
work_package_id: WP03
title: Sibling-mission dev-assist retire/narrow
dependencies: []
requirement_refs:
- FR-004
- FR-006
- NFR-002
- C-002
- C-003
tracker_refs:
- '2076'
planning_base_branch: feat/dev-assist-retire-path-hardening
merge_target_branch: feat/dev-assist-retire-path-hardening
branch_strategy: Planning artifacts for this mission were generated on feat/dev-assist-retire-path-hardening. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/dev-assist-retire-path-hardening unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-dev-assist-retire-path-hardening-01KXAVR0
base_commit: 4e129fc35c2c4d8ee3b87208b14e6c2be7c9c237
created_at: '2026-07-12T11:24:54.447409+00:00'
subtasks:
- T001
- T002
- T003
- T004
phase: Dev-assist retirement
shell_pid: "158503"
agent: "claude"
history:
- at: '2026-07-12T10:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/cli/commands/
create_intent: []
execution_mode: code_change
owned_files:
- tests/specify_cli/cli/commands/test_doctor_shim_reexports.py
- tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py
- tests/specify_cli/cli/commands/agent/test_mission_shim_reexports.py
- tests/specify_cli/coordination/test_commit_router_planning_residue.py
role: implementer
tags: []
task_type: implement
---

# WP03 — Sibling-mission dev-assist retire/narrow

## Context

The doctor/mission decomposition tests carry golden-count duplicates and one-shot pins that a standing golden/consolidated-shim guard already subsumes. Verify each subsumption before deletion (C-002). The consolidated shim guards (`test_mission_shim_reexports.py::test_mission_reexports_required_symbol`, `test_doctor_shim_reexports.py::test_contracted_symbol_resolves_from_doctor`) are KEEP (unique private-symbol coverage) — do not remove them.

## Approach

1. **T001 — RETIRE weaker duplicates**: `test_doctor_shim_reexports.py::test_app_is_a_typer_group_with_seventeen_commands` (count-only; strictly subsumed by `test_doctor_cli_surface_golden.py::test_registered_command_names_are_exactly_the_frozen_sixteen` frozenset-equality) and `::test_pointer_comment_references_issue_2059` (asserts source-header strings — no behavioural contract).
2. **T002 — NARROW the golden**: in `test_registered_command_names_are_exactly_the_frozen_sixteen`, drop the redundant `assert len(registered) == 17` (the frozenset-equality subsumes it) and rename the function off the "sixteen"/17 drift to the live count.
3. **T003 — mission + commit-router**: retire/fold `test_mission_shim_reexports.py::test_record_analysis_shim_gaps_closed` (one-shot "gap closed"; both symbols already in the `_RECORD_ANALYSIS` battery covered by `test_mission_reexports_required_symbol`). In `test_commit_router_planning_residue.py`, dedupe the presence overlap with the shim guard but KEEP the unique `__module__`-ownership + AST import-source assertions + the INV-8 `test_commit_router_has_no_cli_imports` arch invariant.
4. **T004 — anti-vacuity + green**: confirm the golden set-equality still fails on the same command-set drift the retired count would have caught; `PWHEADLESS=1 uv run pytest tests/specify_cli/cli/commands/ -q` (doctor+mission) green.

## Acceptance

- Retirements/narrows applied with each citing the guard that preserves its coverage; unique shim guards untouched.
- Doctor/mission suites green; `ruff` clean.

## Branch Strategy

Planning branch: `feat/dev-assist-retire-path-hardening`; final merge target the same (PR'd to `main`). Worktree per lane from `lanes.json`.

## Activity Log

- 2026-07-12T11:36:27Z – user – shell_pid=80044 – Moved to for_review
- 2026-07-12T11:36:42Z – claude – shell_pid=158503 – Started review via action command
- 2026-07-12T11:44:40Z – claude – shell_pid=158503 – LAND (review a55fb964): all retirements subsumed by verified guards, narrow non-vacuous (same-size-rename mutation reds golden), 123 green, ruff clean, mypy warnings pre-existing
