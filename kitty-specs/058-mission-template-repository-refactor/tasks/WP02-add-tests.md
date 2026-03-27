---
work_package_id: WP02
title: Add Comprehensive Tests
lane: planned
dependencies:
- WP01
subtasks:
- T001
- T002
- T003
phase: Phase 2 - Testing
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

# Work Package Prompt: WP02 - Add Comprehensive Tests

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Create `tests/doctrine/test_mission_template_repository.py` covering all API methods
- Test doctrine-level lookups for all 4 missions (software-dev, research, documentation, plan)
- Test content template lookups
- Test list_* methods return expected template names
- Test resolve_* with no project_dir falls to defaults
- Test resolve_* with project_dir + override file picks override (tier 1)
- Test resolve_* with nonexistent template raises FileNotFoundError
- Test missions_root() returns valid path

**Success**: All new tests pass. `pytest tests/doctrine/test_mission_template_repository.py -v` runs clean.

## Context & Constraints

- **Existing test patterns**: See `tests/doctrine/missions/test_mission_repository.py` and `tests/doctrine/test_central_templates.py` for test structure
- **Override testing**: Use `tmp_path` fixture to create mock project directories with override files
- **API rule**: Tests must NOT use hardcoded paths like `Path("src/doctrine/missions/...")` - use MissionTemplateRepository API methods instead

## Detailed Steps

### T001: Doctrine-level lookup tests

Test `get_command_template()` and `get_content_template()`:
- Valid mission + valid template returns existing Path
- Valid mission + nonexistent template returns None
- Nonexistent mission returns None
- Test against all 4 shipped missions

Test `list_command_templates()` and `list_content_templates()`:
- software-dev has at least ["implement", "plan", "specify", "tasks"]
- research has at least ["implement", "plan", "specify", "tasks"]
- Nonexistent mission returns empty list
- Lists are sorted

Test `missions_root()`:
- Returns a Path that exists
- Contains subdirectories for shipped missions

### T002: Project-aware resolution tests

Test `resolve_command_template()`:
- With no project_dir, returns same as get_command_template()
- With project_dir but no overrides, returns doctrine default
- With project_dir and tier-1 override file, returns override path
- With nonexistent template at all tiers, raises FileNotFoundError

Test `resolve_content_template()`:
- Same patterns as command template resolution

### T003: Edge cases

- Empty mission name
- Template name with/without .md extension handling
- Mission name with special characters

## Verification

```bash
source .venv/bin/activate
.venv/bin/python -m pytest tests/doctrine/test_mission_template_repository.py -v
```

All tests pass.
