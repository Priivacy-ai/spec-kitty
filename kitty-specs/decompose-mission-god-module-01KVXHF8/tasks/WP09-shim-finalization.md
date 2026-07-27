---
work_package_id: WP09
title: Shim finalization — pointer comment + re-export sweep + full gate
dependencies:
- WP08
requirement_refs:
- FR-001
- FR-002
- FR-006
- NFR-001
- NFR-002
- NFR-003
- NFR-004
tracker_refs: []
planning_base_branch: prog/2056-mission
merge_target_branch: prog/2056-mission
branch_strategy: Planning artifacts for this mission were generated on prog/2056-mission. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into prog/2056-mission unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-decompose-mission-god-module-01KVXHF8
base_commit: cc74304cd7f3ac2d26cc05c3904ff69feb19f276
created_at: '2026-06-24T19:52:40.998893+00:00'
subtasks:
- T037
- T038
- T039
- T040
- T041
phase: Phase 5 - Shim + gate
assignee: ''
agent: "claude:opus:randy-reducer:implementer"
shell_pid: "3694574"
history:
- timestamp: '2026-06-24T19:52:40Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/cli/commands/agent/mission.py
create_intent:
- tests/specify_cli/cli/commands/agent/test_mission_shim_reexports.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/mission.py
- tests/specify_cli/cli/commands/agent/test_mission_shim_reexports.py
tags: []
---

# Work Package Prompt: WP09 – Shim finalization (pointer comment + re-export sweep + full gate)

## Do This First

1. Confirm WP08 merged; golden test green.
2. Read research.md §4 (coupling/import map) and §5 (the patch survey: ~100 names; the heavy hitters are
   `locate_project_root` 76×, `_find_feature_directory` 39×, `_show_branch_context` 22×).
3. This WP SOLELY owns `mission.py`. Every seam WP (WP02–WP08) left `mission.py` importing from seams; this
   WP turns it into the final thin shim with the complete re-export block.

## Objective

Reduce `mission.py` to a thin command-registration shim that re-exports every previously-importable /
test-patched symbol, add the #2056 decomposition pointer comment, and pass the full gate sweep with zero
patch-target churn.

## Implementation

### T037 — Reduce to the shim
`mission.py` retains: `app = typer.Typer(name="mission", ...)`, the 8 `@app.command` registrations
delegating to the seam command functions, and the re-export block. No business logic remains.

### T038 — Re-export sweep (~100 names)
Re-export EVERY symbol currently importable/patchable as `mission.<name>`. At minimum (from the patch
survey): `locate_project_root`, `run_command`, `get_emitter`, `is_saas_sync_enabled`,
`validate_feature_structure`, `_find_feature_directory`, `_show_branch_context`, `CommitToBranchResult`,
all 8 command functions, plus every helper that any test patches or imports and every name `lifecycle.py` /
`tasks.py` resolve. Derive the full set by grepping `@patch("...mission.` and `from ...mission import`
across `tests/`, `lifecycle.py`, `tasks.py`.

### T039 — Pointer comment (FR-002)
Add the top-of-file #2056 decomposition pointer comment (matching the existing god-module-pointer
convention already in `mission.py`/`tasks.py` and the #1623 style): document the shim role + the seam map
so future maintainers route new responsibilities to the seams, not the shim.

### T040 — Re-export presence test
Author `test_mission_shim_reexports.py` asserting every surveyed patch target resolves via `mission.<name>`
(import + `hasattr` over the enumerated set), so a future accidental drop is caught.

### T041 — Full gate sweep
Run the ENTIRE mission-touching suite (≈50 files) — must pass with ZERO patch-target rewrites — plus the
golden test, `tests/integration/test_json_envelope_strict.py`, `tests/tasks/`. Then: `ruff check` (C901 ≤15
everywhere incl. every seam + phase helper), `mypy --strict`, coverage ≥90% on new code, and confirm zero
new suppressions (`# noqa` / `# type: ignore` / Sonar) were added across the whole mission.

## Acceptance (mission-level — SC-1..SC-8)

- `mission.py` is a thin shim, no business logic; #2056 pointer comment present.
- Entire suite passes with zero patch-target churn; re-export presence test green; golden green.
- ruff C901 ≤15 everywhere; mypy --strict clean; new-code coverage ≥90%; zero new suppressions.

## Out-of-map edits

- None — this WP solely owns `mission.py` and its new re-export test.

## Activity Log

- 2026-06-24T23:46:32Z – claude:opus:randy-reducer:implementer – shell_pid=3694574 – Assigned agent via action command
