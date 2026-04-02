---
work_package_id: WP01
title: Update Hardcoded Mission Paths
dependencies: []
requirement_refs:
- FR-001
- C-002
planning_base_branch: feature/agent-profile-implementation-rebased
merge_target_branch: feature/agent-profile-implementation-rebased
branch_strategy: Planning artifacts for this mission were generated on feature/agent-profile-implementation-rebased. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation-rebased unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
history:
- at: '2026-04-02T17:58:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer
authoritative_surface: tests/missions/
execution_mode: code_change
lane: planned
owned_files:
- tests/missions/test_documentation_mission.py
- tests/missions/test_documentation_templates.py
- tests/missions/test_mission_software_dev_integration.py
- tests/specify_cli/test_command_template_cleanliness.py
task_type: implement
---

# Work Package Prompt: WP01 -- Update Hardcoded Mission Paths

## Objectives & Success Criteria

- Replace all hardcoded `src/specify_cli/missions/` paths in 4 test files with `MissionTemplateRepository.default_missions_root()`
- All 4 test files pass with zero failures and zero errors
- No other tests broken by the change

## Context & Constraints

- **Root cause**: Commit `bd7a288c` moved mission YAML/templates from `src/specify_cli/missions/` to `src/doctrine/missions/`
- **Constraint C-002**: Use `MissionTemplateRepository` rather than hardcoding `src/doctrine/missions/` to avoid repeating the same brittleness
- **Spec**: `kitty-specs/062-fix-doctrine-migration-test-failures/spec.md`
- **Plan**: `kitty-specs/062-fix-doctrine-migration-test-failures/plan.md`

## Branch Strategy

- **Strategy**: Direct commit to feature branch
- **Planning base branch**: `feature/agent-profile-implementation-rebased`
- **Merge target branch**: `feature/agent-profile-implementation-rebased`

**Implementation command**: `spec-kitty implement WP01`

## Subtasks & Detailed Guidance

### Subtask T001 -- Fix test_mission_software_dev_integration.py

- **Purpose**: This file hardcodes `src/specify_cli/missions/software-dev/mission.yaml` which no longer exists.
- **File**: `tests/missions/test_mission_software_dev_integration.py`
- **Current code** (lines 34-40):
  ```python
  MISSION_YAML_PATH = (
      Path(__file__).resolve().parents[2]
      / "src"
      / "specify_cli"
      / "missions"
      / "software-dev"
      / "mission.yaml"
  )
  ```
- **Fix**: Replace with:
  ```python
  from doctrine.missions.repository import MissionTemplateRepository

  MISSIONS_ROOT = MissionTemplateRepository.default_missions_root()
  MISSION_YAML_PATH = MISSIONS_ROOT / "software-dev" / "mission.yaml"
  ```
- **Parallel?**: Yes -- independent file
- **Verification**: `pytest tests/missions/test_mission_software_dev_integration.py -x`

### Subtask T002 -- Fix test_documentation_mission.py

- **Purpose**: This file hardcodes `src/specify_cli` as base for mission lookup.
- **File**: `tests/missions/test_documentation_mission.py`
- **Current code** (lines 12-13, 19): References `REPO_ROOT / "src" / "specify_cli"` then appends `missions/documentation`
- **Fix**: Replace path construction with:
  ```python
  from doctrine.missions.repository import MissionTemplateRepository

  MISSIONS_ROOT = MissionTemplateRepository.default_missions_root()
  DOC_MISSION_DIR = MISSIONS_ROOT / "documentation"
  ```
- **Parallel?**: Yes -- independent file
- **Note**: Also update the docstring on line 18 that says `"Test documentation mission loads from src/specify_cli/missions/."` to reflect the new location.

### Subtask T003 -- Fix test_documentation_templates.py

- **Purpose**: Hardcodes `MISSION_DIR` to old location.
- **File**: `tests/missions/test_documentation_templates.py`
- **Current code** (line 11):
  ```python
  MISSION_DIR = REPO_ROOT / "src" / "specify_cli" / "missions" / "documentation"
  ```
- **Fix**: Replace with:
  ```python
  from doctrine.missions.repository import MissionTemplateRepository

  MISSION_DIR = MissionTemplateRepository.default_missions_root() / "documentation"
  ```
- **Parallel?**: Yes -- independent file

### Subtask T004 -- Fix test_command_template_cleanliness.py

- **Purpose**: References `src/specify_cli/missions/software-dev/command-templates` which no longer exists.
- **File**: `tests/specify_cli/test_command_template_cleanliness.py`
- **Steps**:
  1. Read the file to find the exact path construction
  2. Replace with `MissionTemplateRepository.default_missions_root() / "software-dev" / "command-templates"`
  3. Add the `MissionTemplateRepository` import
- **Parallel?**: Yes -- independent file

### Subtask T005 -- Verify all 4 files pass

- **Purpose**: Confirm the fixes work end-to-end.
- **Command**:
  ```bash
  pytest tests/missions/test_mission_software_dev_integration.py \
         tests/missions/test_documentation_mission.py \
         tests/missions/test_documentation_templates.py \
         tests/specify_cli/test_command_template_cleanliness.py -v
  ```
- **Expected**: All tests pass, zero errors.

## Risks & Mitigations

- `MissionTemplateRepository` import fails → ensure `doctrine` package is importable (it's part of the editable install)
- Tests may have additional hardcoded references beyond the identified lines → grep each file for `specify_cli/missions` before committing

## Review Guidance

- Verify no test still references `src/specify_cli/missions/`
- Verify `MissionTemplateRepository` is used consistently (not hardcoded `src/doctrine/missions/`)
- Check that test logic is unchanged -- only the path source is different

## Activity Log

- 2026-04-02T17:58:00Z -- system -- Prompt created.
