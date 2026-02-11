---
work_package_id: WP06
title: Fix Bug
lane: "done"
dependencies: []
base_branch: main
base_commit: a8373ae11b029bfaa8ebb0c7209fadc448f98be9
created_at: '2026-02-11T15:23:00.553146+00:00'
subtasks: [T039, T040, T041, T042, T043, T044]
phase: Phase 1 - Bug Fixes
shell_pid: "35268"
agent: "codex"
reviewed_by: "Robert Douglass"
review_status: "approved"
---

# Work Package Prompt: WP06 – Fix Bug #119 - Assignee Relaxation

## Objectives

- Assignee optional for WPs in 'done' lane
- Strict checks remain for 'doing' and 'for_review' lanes
- Required fields (lane, agent, shell_pid) still enforced
- 5 tests passing (regression test updated + 2 new tests)

**Command**: `spec-kitty implement WP06`

## Context

- **Issue**: #119 by @fabiodouek
- **File**: `src/specify_cli/core/acceptance_core.py:455`
- **Bug**: Strict validation requires assignee even for completed WPs
- **Fix**: Make assignee optional for 'done' lane
- **2.x Note**: acceptance_core.py doesn't exist on 2.x (will be manually ported in WP10)

## Test-First Subtasks

### T039-T041: Write/Update Tests

**T039**: Update existing regression test
```python
# In tests/specify_cli/core/test_acceptance_support.py
def test_acceptance_succeeds_for_done_wp_without_assignee():
    """Done WPs should not require assignee."""
    wp = create_test_wp(lane="done", assignee=None)
    result = validate_wp_metadata(wp)
    assert result.is_valid, "Should pass for done WP without assignee"
```

**T040**: Test strict check still works for active WPs
**T041**: Test required fields still enforced

### T042-T043: Implement Fix

**T042**: Modify acceptance_core.py:455
```python
# Before:
if wp.current_lane in {"doing", "for_review", "done"} and not wp.assignee:
    metadata_issues.append(f"{wp_id}: missing assignee")

# After:
if wp.current_lane in {"doing", "for_review"} and not wp.assignee:
    metadata_issues.append(f"{wp_id}: missing assignee")
# 'done' removed - assignee not required for completed work
```

**T043**: Verify acceptance workflow not broken

### T044: Commit

Commit: `fix: relax strict assignee gate in acceptance validation (fixes #119)`

## Activity Log

- 2026-02-11T15:25:53Z – unknown – shell_pid=2443 – lane=for_review – Moved to for_review
- 2026-02-11T15:50:57Z – codex – shell_pid=35268 – lane=doing – Started review via workflow command
- 2026-02-11T15:51:34Z – codex – shell_pid=35268 – lane=done – Review passed: Implementation correctly relaxes assignee requirement for 'done' lane. Code change is minimal and surgical (1 line). Tests are comprehensive covering all edge cases. All 32 acceptance tests pass. Commit message follows conventions. Fixes bug #119 as specified.
