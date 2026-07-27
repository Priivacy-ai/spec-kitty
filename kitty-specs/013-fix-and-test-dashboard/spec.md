# Feature Specification: Fix and Test Dashboard

**Feature Branch**: `013-fix-and-test-dashboard`
**Created**: 2026-01-16
**Status**: Draft
**Input**: User description: "The PR has until now ignored the dashboard. We made breaking changes to the dashboard and now it's time to fix them. This feature is to fix and test the dashboard."

## Background

The v0.11.0 release introduces a workspace-per-work-package model that changed how features and tasks are organized:
- **New format (0.11.0+)**: Tasks stored in flat `tasks/` directory with lane status in YAML frontmatter
- **Legacy format (pre-0.11.0)**: Tasks stored in lane subdirectories (`tasks/planned/`, `tasks/doing/`, etc.)

The dashboard must support both formats to maintain backwards compatibility while working correctly with the new model.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Kanban Board for New Format Features (Priority: P1)

Users viewing the dashboard for features created with v0.11.0+ should see their work packages correctly organized in kanban lanes, with lane assignment read from YAML frontmatter.

**Why this priority**: This is the primary use case - all new features use the new format.

**Independent Test**: Navigate to dashboard, select a feature with flat `tasks/` directory structure, verify kanban displays correct lane assignments.

**Acceptance Scenarios**:

1. **Given** a feature with tasks in flat `tasks/` directory with `lane: doing` in frontmatter, **When** user views kanban board, **Then** tasks appear in the "Doing" lane
2. **Given** a feature with 10 work packages across different lanes, **When** user views kanban board, **Then** lane counts match the actual frontmatter lane values
3. **Given** a work package with no `lane` field in frontmatter, **When** user views kanban board, **Then** task defaults to "Planned" lane

---

### User Story 2 - View Kanban Board for Legacy Format Features (Priority: P2)

Users viewing the dashboard for features created before v0.11.0 should see their work packages correctly organized in kanban lanes, with lane assignment based on subdirectory location.

**Why this priority**: Backwards compatibility ensures existing projects continue working after upgrade.

**Independent Test**: Navigate to dashboard, select a feature with lane subdirectories (`tasks/planned/`, `tasks/doing/`), verify kanban displays tasks in correct lanes.

**Acceptance Scenarios**:

1. **Given** a feature with tasks in `tasks/done/` subdirectory, **When** user views kanban board, **Then** tasks appear in the "Done" lane
2. **Given** a feature with mixed lane directories, **When** user views kanban board, **Then** each task appears in the lane matching its directory location
3. **Given** an empty lane directory (only `.gitkeep`), **When** user views kanban board, **Then** lane shows 0 items (not counted as legacy)

---

### User Story 3 - Dashboard Test Coverage (Priority: P1)

Developers maintaining the dashboard should have automated tests that verify both legacy and new format handling, preventing regressions.

**Why this priority**: Test coverage is critical to prevent future breaking changes from going undetected.

**Independent Test**: Run `pytest tests/test_dashboard/` and verify tests pass for both format types.

**Acceptance Scenarios**:

1. **Given** a test creating a new-format feature, **When** scanner runs, **Then** tasks are correctly parsed from frontmatter
2. **Given** a test creating a legacy-format feature, **When** scanner runs, **Then** tasks are correctly parsed from subdirectories
3. **Given** the dashboard test suite, **When** tests run, **Then** both formats have explicit test coverage

---

### Edge Cases

- What happens when a feature has both lane subdirectories AND flat task files? (Legacy detection should take precedence)
- How does the system handle malformed frontmatter (missing `work_package_id`)? (Task should be skipped with log warning)
- What happens when a task file has encoding errors? (Dashboard shows error message, doesn't crash)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Dashboard MUST correctly display kanban lanes for features using new frontmatter-based lane format
- **FR-002**: Dashboard MUST correctly display kanban lanes for features using legacy directory-based lane format
- **FR-003**: Scanner MUST auto-detect format type using `is_legacy_format()` function
- **FR-004**: Scanner tests MUST cover both legacy and new format scenarios
- **FR-005**: Dashboard MUST handle missing/malformed task files gracefully without crashing
- **FR-006**: API endpoint `/api/kanban/<feature>` MUST return `is_legacy` flag indicating format type

### Key Entities

- **Work Package**: Task file with ID, title, lane, subtasks, agent assignment
- **Feature**: Collection of work packages with metadata and artifacts
- **Lane**: Kanban status (planned, doing, for_review, done)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All existing dashboard functionality works with features created using new format
- **SC-002**: All existing dashboard functionality works with features created using legacy format
- **SC-003**: Scanner test file covers both format types with at least 2 test cases each
- **SC-004**: No console errors when navigating dashboard pages (except expected 404 for missing constitution)
- **SC-005**: Kanban lane counts match actual task counts for both format types
