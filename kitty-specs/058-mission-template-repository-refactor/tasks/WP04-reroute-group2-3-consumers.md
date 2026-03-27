---
work_package_id: WP04
title: Reroute Resolver and Direct-Path Consumers
lane: planned
dependencies:
- WP03
subtasks:
- T001
- T002
- T003
phase: Phase 4 - Consumer Rerouting
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

# Work Package Prompt: WP04 - Reroute Resolver and Direct-Path Consumers

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Reroute 5-tier resolver consumers to use `MissionTemplateRepository.resolve_command_template()`
- Reroute direct importlib/path consumers to use `MissionTemplateRepository` methods
- All existing tests continue to pass

**Success**: `pytest tests/ -q` (full suite) passes with no failures.

## Context & Constraints

- **5-tier resolver stays**: `src/specify_cli/runtime/resolver.py` remains as the implementation engine. `MissionTemplateRepository.resolve_*` calls it internally
- **Lazy imports**: Any `specify_cli` imports in `doctrine` code must be lazy (inside method bodies)
- **Shipped migrations**: Do NOT touch any migration files

## Detailed Steps

### T001: Reroute 5-tier resolver consumers

In `src/specify_cli/next/prompt_builder.py`:
- Replace direct `resolver.resolve_template()` calls with `MissionTemplateRepository.resolve_command_template()`

In `src/specify_cli/cli/commands/init.py`:
- Replace `_resolve_mission_command_templates_dir()` usage with `MissionTemplateRepository` where appropriate
- If the function does more than template resolution, keep it but delegate the template part

In `src/specify_cli/next/runtime_bridge.py`:
- Replace `MissionRepository.default_missions_root()` with `MissionTemplateRepository.missions_root()`

### T002: Reroute direct importlib/path consumers

In `src/specify_cli/template/manager.py`:
- Replace direct path construction for mission templates with `MissionTemplateRepository` methods

In `src/specify_cli/cli/commands/agent/config.py`:
- Replace `.kittify/missions/` path access with `MissionTemplateRepository` methods where appropriate

### T003: Verify no remaining direct path construction

Search for patterns like:
- `missions_root / mission / "command-templates"` (should use API)
- `missions_root / mission / "templates"` (should use API)
- `importlib.resources.files("doctrine") / "missions"` outside of repository classes (should use API)

Exceptions:
- Shipped migrations (frozen)
- `test_package_bundling.py` (needs repo-root paths for `python -m build`)
- MissionRepository and MissionTemplateRepository themselves (they implement the path logic)

## Verification

```bash
source .venv/bin/activate
.venv/bin/python -m pytest --tb=short -q
```

Full test suite passes.
