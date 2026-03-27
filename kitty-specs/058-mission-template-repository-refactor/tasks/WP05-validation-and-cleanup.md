---
work_package_id: WP05
title: Final Validation and Cleanup
lane: planned
dependencies:
- WP04
subtasks:
- T001
- T002
- T003
phase: Phase 5 - Validation
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

# Work Package Prompt: WP05 - Final Validation and Cleanup

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Full test suite passes
- No remaining direct path construction to mission templates (except allowed exceptions)
- Backward compatibility confirmed (existing mock targets still work)
- Architecture docs updated to reference MissionTemplateRepository

**Success**: Full pytest suite green. `grep -r` for direct path patterns returns only allowed exceptions.

## Detailed Steps

### T001: Run full test suite

```bash
source .venv/bin/activate
.venv/bin/python -m pytest --tb=short -q
```

Fix any failures.

### T002: Verify no remaining direct path construction

Search for these patterns and verify they only appear in allowed locations:
- `/ "command-templates" /` outside MissionTemplateRepository, MissionRepository, tests, and migrations
- `/ "templates" /` outside MissionTemplateRepository, MissionRepository, CentralTemplateRepository, tests, and migrations
- `importlib.resources.files("doctrine") / "missions"` outside repository classes

### T003: Update architecture docs

In `architecture/2.x/04_implementation_mapping/README.md`:
- Add MissionTemplateRepository to the implementation mapping
- Reference the dual-mode API (doctrine-level vs project-aware)

## Verification

```bash
source .venv/bin/activate
.venv/bin/python -m pytest --tb=short -q
```

Full suite green. No stale path patterns outside allowed exceptions.
