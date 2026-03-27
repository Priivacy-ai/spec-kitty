---
work_package_id: WP03
title: Reroute Direct MissionRepository Template Consumers
lane: planned
dependencies:
- WP01
- WP02
subtasks:
- T001
- T002
- T003
phase: Phase 3 - Consumer Rerouting
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
review_feedback: ''
planning_base_branch: feature/agent-profile-implementation
merge_target_branch: feature/agent-profile-implementation
branch_strategy: Work is done on feature/agent-profile-implementation targeting PR #305.
history:
- timestamp: '2026-03-26T07:55:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated for mission-template-repository-refactor
---

# Work Package Prompt: WP03 - Reroute Direct MissionRepository Template Consumers

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Reroute `Mission.get_command_template()` in `src/specify_cli/mission.py` to delegate through `MissionTemplateRepository`
- Reroute manifest mission_dir template access in `src/specify_cli/manifest.py`
- Reroute template discovery in `src/specify_cli/runtime/show_origin.py`
- Make `MissionRepository.get_command_template()` and `get_template()` thin delegations to `MissionTemplateRepository`
- All existing tests continue to pass (backward compat)

**Success**: `pytest tests/missions/ tests/runtime/ tests/doctrine/ -q` passes with no failures.

## Context & Constraints

- **Backward compatibility**: `MissionRepository` methods must remain callable - they become thin delegations
- **Mock targets**: Existing tests that mock `MissionRepository.get_command_template` must still work
- **Shipped migrations**: Do NOT touch any migration files

## Detailed Steps

### T001: Update MissionRepository to delegate

In `src/doctrine/missions/repository.py`:
- `get_command_template()` delegates to `MissionTemplateRepository.get_command_template()` but preserves its instance-based signature (it takes self and uses self._root)
- `get_template()` delegates similarly
- Non-template methods (`get_action_index_path`, `get_mission_config_path`, etc.) remain unchanged

Note: Since MissionRepository is instance-based (takes a `missions_root` in `__init__`) and MissionTemplateRepository is static (always uses doctrine default root), the delegation only applies when MissionRepository is instantiated with the default doctrine root. For non-default roots (e.g., test fixtures), MissionRepository keeps its own implementation.

### T002: Update Mission class

In `src/specify_cli/mission.py`:
- `Mission.get_command_template()` delegates to `MissionTemplateRepository.get_command_template()` or `resolve_command_template()` as appropriate

### T003: Update show_origin.py and manifest.py

In `src/specify_cli/runtime/show_origin.py`:
- Replace `MissionRepository().get_command_template()` calls with `MissionTemplateRepository.get_command_template()`

In `src/specify_cli/manifest.py`:
- Replace direct path construction (`mission_dir / "command-templates"`) with `MissionTemplateRepository` methods

## Verification

```bash
source .venv/bin/activate
.venv/bin/python -m pytest tests/missions/ tests/runtime/ tests/doctrine/ tests/specify_cli/ -q
```
