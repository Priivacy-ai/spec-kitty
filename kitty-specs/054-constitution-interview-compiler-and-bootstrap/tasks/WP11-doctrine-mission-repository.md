---
work_package_id: WP11
title: Create MissionRepository and Redirect Package Asset Resolution
lane: "done"
dependencies:
- WP05
- WP09
base_branch: feature/agent-profile-implementation
base_commit: ccf10b079434c7593611d85bbc1fa1b0d60f0eab
created_at: '2026-03-10T07:03:39.032013+00:00'
subtasks:
- T052
- T053
- T054
- T055
- T056
phase: Phase 4 - Mission Consolidation
assignee: ''
agent: ''
shell_pid: '599084'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-03-10T06:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated manually
requirement_refs: []
---

# Work Package Prompt: WP11 - Create MissionRepository and Redirect Package Asset Resolution

## ⚠️ IMPORTANT: Review Feedback Status

- If review feedback exists, address it before treating this WP as complete.

---

## Review Feedback

*[Empty initially.]*

---

## Objectives & Success Criteria

- A `MissionRepository` class in `src/doctrine/missions/repository.py` provides query methods for mission configs, command templates, and action assets.
- `get_package_asset_root()` in `src/specify_cli/runtime/home.py` resolves to `doctrine.missions` instead of `specify_cli.missions`.
- The tier-5 (package default) resolution in `resolver.py` serves content from `doctrine/missions/` at runtime.
- `pyproject.toml` packaging includes `doctrine/missions/` as package data.
- All existing tests continue to pass — template resolution, command resolution, mission discovery.

## Context & Constraints

- Currently `src/specify_cli/missions/` and `src/doctrine/missions/` both contain command-templates and templates. Per CLAUDE.md, `src/doctrine/missions/` is the canonical source, but `src/specify_cli/missions/` is what gets served to installed users via tier-5 resolution.
- The two copies are fully divergent — `doctrine/missions/` has 79 template files while `specify_cli/missions/` has 58 stale copies, and virtually all shared files differ in content.
- Other doctrine artifact types (directives, tactics, styleguides, etc.) all have repository classes with a standard interface; missions do not.
- `copy_specify_base_from_local()` already correctly copies from `src/doctrine/missions/` during local dev.
- This WP focuses on creating the repository and redirecting resolution. WP12 handles the removal of the stale `specify_cli/missions/` content.

## Subtasks & Detailed Guidance

### Subtask T052 - Create `MissionRepository` in `src/doctrine/missions/repository.py`

- **Purpose**: Provide a repository service for mission command templates and metadata, following the established doctrine repository pattern.
- **Steps**:
  1. Create `src/doctrine/missions/repository.py`.
  2. Implement `MissionRepository` with:
     - `__init__(missions_root: Path)` — root of the missions directory tree.
     - `list_missions() -> list[str]` — return available mission keys (directory names with `mission.yaml`).
     - `get_command_template(mission: str, command: str) -> Path | None` — resolve a command-template file.
     - `get_template(mission: str, template: str) -> Path | None` — resolve a regular template file.
     - `get_action_index_path(mission: str, action: str) -> Path | None` — resolve action index.yaml.
     - `get_action_guidelines_path(mission: str, action: str) -> Path | None` — resolve action guidelines.md.
     - `get_mission_config_path(mission: str) -> Path | None` — resolve mission.yaml.
  3. Add a `default_missions_root()` classmethod that uses `importlib.resources.files("doctrine")` to find the shipped missions directory.
  4. Export from `src/doctrine/missions/__init__.py`.
- **Files**: `src/doctrine/missions/repository.py`, `src/doctrine/missions/__init__.py`
- **Notes**: Keep the repository read-only (no save/delete). Missions are shipped assets, not user-created. The repository does not need two-source merging like directive/tactic repositories — mission overrides are handled by the 5-tier resolver in `specify_cli`.

### Subtask T053 - Redirect `get_package_asset_root()` to `doctrine.missions`

- **Purpose**: Make installed packages serve templates from `doctrine/missions/` instead of the stale `specify_cli/missions/`.
- **Steps**:
  1. In `src/specify_cli/runtime/home.py`, update `get_package_asset_root()` to resolve via `importlib.resources.files("doctrine")` / `"missions"` as primary, with `specify_cli/missions` as fallback.
  2. Update the development layout fallback path accordingly.
  3. Verify that `resolver.py` tier-5 resolution now serves doctrine content.
- **Files**: `src/specify_cli/runtime/home.py`
- **Notes**: Keep a fallback to `specify_cli/missions` for backward compatibility during the transition period (WP12 removes it).

### Subtask T054 - Update `pyproject.toml` packaging

- **Purpose**: Ensure `doctrine/missions/` is included as package data in built distributions.
- **Steps**:
  1. In `pyproject.toml`, add `"src/doctrine/missions/"` to the packages/package-data configuration if not already present.
  2. Verify that `doctrine/missions/**/*.md`, `doctrine/missions/**/*.yaml`, and `doctrine/missions/**/mission.yaml` are included in the wheel.
  3. Check that existing `"src/specify_cli/missions/"` entry is still present (removal happens in WP12).
- **Files**: `pyproject.toml`
- **Notes**: Check the existing packaging pattern for `doctrine` — it may already include subpackage data via glob patterns.

### Subtask T055 - Update `copy_specify_base_from_package()` to use doctrine source

- **Purpose**: Make the package-based init flow use `doctrine.missions` instead of `specify_cli.missions`.
- **Steps**:
  1. In `src/specify_cli/template/manager.py`, update `copy_specify_base_from_package()` to prefer `doctrine.missions` as the source for mission content.
  2. Keep the existing fallback candidates as a safety net.
  3. Verify `copy_specify_base_from_local()` still works (it already uses `src/doctrine/missions/`).
- **Files**: `src/specify_cli/template/manager.py`

### Subtask T056 - Add tests and verify no regressions

- **Purpose**: Lock in the new resolution behavior and verify all consumers still work.
- **Steps**:
  1. Add unit tests for `MissionRepository` (list_missions, get_command_template, get_action_index_path).
  2. Verify tier-5 resolution serves doctrine content.
  3. Run full test suite.
  4. Run ruff and mypy checks.
- **Files**: `tests/doctrine/missions/test_mission_repository.py`, existing resolver tests

## Test Strategy

- `pytest -q tests/doctrine/missions/test_mission_repository.py`
- `pytest -q tests/` (full suite)
- `ruff check src/doctrine/missions/ src/specify_cli/runtime/`
- `mypy src/doctrine/missions/repository.py --ignore-missing-imports`

## Risks & Mitigations

- Changing `get_package_asset_root()` affects all tier-5 resolution. Keep `specify_cli/missions` as a fallback until WP12 removes it.
- Installed distributions may not include `doctrine/missions/` without explicit `pyproject.toml` updates. Verify with a test build.

## Review Guidance

- Confirm `MissionRepository` follows the established doctrine repository pattern.
- Confirm tier-5 resolution now serves from `doctrine/missions/` by default.
- Confirm `pyproject.toml` includes `doctrine/missions/` data files.
- Confirm all existing template resolution tests still pass.

## Activity Log

- 2026-03-10T06:00:00Z - system - lane=planned - Prompt created.
- 2026-03-10T07:09:05Z – unknown – shell_pid=599084 – lane=for_review – MissionRepository created, get_package_asset_root redirected to doctrine.missions with fallback, pyproject.toml updated, tests added
- 2026-03-10T07:14:15Z – unknown – shell_pid=599084 – lane=done – Moved to done
