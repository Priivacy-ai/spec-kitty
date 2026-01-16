---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
  - "T007"
title: "Add Scanner Format Tests"
phase: "Phase 1 - Test Coverage"
lane: "for_review"
assignee: ""
agent: "claude"
shell_pid: "85594"
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
  - timestamp: "2026-01-16T13:44:43Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Add Scanner Format Tests

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Add test coverage for the dashboard scanner to verify both legacy (directory-based) and new (frontmatter-based) lane formats work correctly.

**Success Criteria:**
- All new tests pass
- Existing legacy format tests continue passing
- Scanner correctly parses frontmatter `lane:` field for new format
- Scanner correctly detects format type via `is_legacy_format()`
- Missing `lane:` field defaults to "planned"

## Context & Constraints

**Background**: The v0.11.0 release changed task organization:
- **New format**: Tasks in flat `tasks/` directory, lane in YAML frontmatter
- **Legacy format**: Tasks in lane subdirectories (`tasks/planned/`, `tasks/doing/`, etc.)

**Key Files**:
- `tests/test_dashboard/test_scanner.py` - ADD tests here
- `src/specify_cli/dashboard/scanner.py` - READ ONLY (already working)
- `src/specify_cli/legacy_detector.py` - READ ONLY (already working)

**Reference Docs**:
- `kitty-specs/013-fix-and-test-dashboard/spec.md` - Requirements
- `kitty-specs/013-fix-and-test-dashboard/plan.md` - Implementation plan
- `kitty-specs/013-fix-and-test-dashboard/quickstart.md` - Test patterns

## Subtasks & Detailed Guidance

### Subtask T001 – Create new format fixture helper

- **Purpose**: Provide a reusable fixture that creates features with new flat `tasks/` format
- **Steps**:
  1. Read existing `_create_feature()` to understand the pattern
  2. Create `_create_new_format_feature(tmp_path: Path) -> Path` function
  3. Create feature directory with flat `tasks/` (NO subdirectories)
  4. Create work package file directly in `tasks/` with frontmatter including `lane: doing`
- **Files**: `tests/test_dashboard/test_scanner.py`
- **Parallel?**: No - must complete before other tests

**Example fixture structure:**
```python
def _create_new_format_feature(tmp_path: Path) -> Path:
    """Creates NEW format with flat tasks/ directory (lane in frontmatter)."""
    feature_dir = tmp_path / "kitty-specs" / "002-new-feature"
    (feature_dir / "tasks").mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")

    prompt = """---
work_package_id: WP01
lane: doing
subtasks: ["T1"]
agent: claude
---
# Work Package Prompt: Demo

Body content here
"""
    (feature_dir / "tasks" / "WP01-demo.md").write_text(prompt, encoding="utf-8")
    return feature_dir
```

### Subtask T002 – Test new format lane detection

- **Purpose**: Verify scanner reads `lane:` field from frontmatter correctly
- **Steps**:
  1. Use `_create_new_format_feature()` to create test feature
  2. Call `scanner.scan_feature_kanban(tmp_path, feature_dir.name)`
  3. Assert task appears in "doing" lane (from frontmatter)
- **Files**: `tests/test_dashboard/test_scanner.py`
- **Parallel?**: Yes (after T001)

### Subtask T003 – Test default lane behavior

- **Purpose**: Verify missing `lane:` field defaults to "planned"
- **Steps**:
  1. Create feature with WP that has NO `lane:` field in frontmatter
  2. Call scanner
  3. Assert task appears in "planned" lane
- **Files**: `tests/test_dashboard/test_scanner.py`
- **Parallel?**: Yes (after T001)

### Subtask T004 – Test multiple lanes

- **Purpose**: Verify scanner distributes tasks correctly across all 4 lanes
- **Steps**:
  1. Create feature with 4 WPs (one per lane: planned, doing, for_review, done)
  2. Call scanner
  3. Assert each lane has exactly 1 task
  4. Assert correct WP IDs in each lane
- **Files**: `tests/test_dashboard/test_scanner.py`
- **Parallel?**: Yes (after T001)

### Subtask T005 – Test is_legacy_format detects new format

- **Purpose**: Verify `is_legacy_format()` returns False for new format features
- **Steps**:
  1. Use `_create_new_format_feature()` to create test feature
  2. Call `is_legacy_format(feature_dir)`
  3. Assert returns False
- **Files**: `tests/test_dashboard/test_scanner.py`
- **Parallel?**: Yes (after T001)

**Import needed:**
```python
from specify_cli.legacy_detector import is_legacy_format
```

### Subtask T006 – Test is_legacy_format detects legacy format

- **Purpose**: Verify `is_legacy_format()` returns True for legacy format features
- **Steps**:
  1. Use existing `_create_feature()` to create legacy feature
  2. Call `is_legacy_format(feature_dir)`
  3. Assert returns True
- **Files**: `tests/test_dashboard/test_scanner.py`
- **Parallel?**: Yes (after T001)

### Subtask T007 – Run full test suite

- **Purpose**: Verify no regressions in existing tests
- **Steps**:
  1. Run `pytest tests/test_dashboard/ -v`
  2. Verify all tests pass
  3. Run `pytest tests/test_dashboard/test_scanner.py -v` specifically
- **Files**: N/A (verification only)
- **Parallel?**: No - final verification step

## Test Strategy

**Commands:**
```bash
# Run scanner tests only
pytest tests/test_dashboard/test_scanner.py -v

# Run all dashboard tests
pytest tests/test_dashboard/ -v

# Run with coverage
pytest tests/test_dashboard/test_scanner.py -v --cov=src/specify_cli/dashboard/scanner
```

**Expected Results:**
- All existing tests pass unchanged
- 5+ new tests pass
- No import errors or fixture failures

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Existing tests break | Keep `_create_feature()` unchanged; add new fixture |
| Import errors | Import `is_legacy_format` at top of test file |
| Fixture path issues | Use `tmp_path` consistently, same as existing tests |

## Definition of Done Checklist

- [ ] `_create_new_format_feature()` fixture implemented
- [ ] All 5 new test functions added
- [ ] All new tests pass
- [ ] All existing tests still pass
- [ ] `pytest tests/test_dashboard/test_scanner.py -v` shows 100% success

## Review Guidance

**Acceptance checkpoints:**
1. New fixture creates flat `tasks/` directory (no subdirectories)
2. Tests cover: lane detection, default lane, multiple lanes, format detection
3. Existing tests unmodified and still passing
4. Test names are descriptive and follow existing patterns

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-01-16T13:44:43Z – system – lane=planned – Prompt created via /spec-kitty.tasks

---

### Updating Lane Status

To change this work package's lane, either:

1. **Edit directly**: Change the `lane:` field in frontmatter AND append activity log entry (at the end)
2. **Use CLI**: `spec-kitty agent tasks move-task WP01 --to <lane> --note "message"` (recommended)

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
- 2026-01-16T13:45:57Z – claude – shell_pid=85594 – lane=doing – Started implementation via workflow command
- 2026-01-16T13:47:42Z – claude – shell_pid=85594 – lane=for_review – All 7 tests pass. Added fixture and 5 new test functions for new format coverage.
# test
# test change
- 2026-01-16T13:53:17Z – claude – shell_pid=85594 – lane=done – Review passed: mission.yaml and directory structure match requirements
- 2026-01-16T13:56:29Z – claude – shell_pid=85594 – lane=done – Testing auto-commit fix
- 2026-01-16T13:58:24Z – claude – shell_pid=85594 – lane=for_review – Testing without gitignore
