# Data Model: Frontmatter-Only Lane Management

**Feature**: 007-frontmatter-only-lane
**Date**: 2025-12-17

## Entity Overview

```
┌─────────────────┐      ┌─────────────────┐
│    Feature      │──────│  Work Package   │
│                 │ 1:N  │      (WP)       │
└─────────────────┘      └─────────────────┘
                                 │
                                 │ has
                                 ▼
                         ┌─────────────────┐
                         │      Lane       │
                         │   (enum field)  │
                         └─────────────────┘
```

## Entities

### Feature

A development feature tracked by Spec Kitty.

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | string | Feature identifier (e.g., "007-frontmatter-only-lane") |
| `branch` | string | Git branch name |
| `spec_path` | path | Path to spec.md |
| `tasks_dir` | path | Path to tasks/ directory (flat structure) |

**Location**: `kitty-specs/{feature-id}/`

**Constraints**:

- Feature ID matches branch name
- One spec.md per feature
- One flat tasks/ directory per feature

### Work Package (WP)

A unit of work within a feature.

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `work_package_id` | string | Yes | Unique ID (e.g., "WP01") |
| `title` | string | Yes | Human-readable title |
| `lane` | Lane | Yes | Current workflow status |
| `phase` | string | No | Implementation phase |
| `assignee` | string | No | Assigned developer/agent |
| `agent` | string | No | AI agent identifier |
| `shell_pid` | string | No | Process ID if running |
| `subtasks` | list[string] | No | Task IDs within WP |
| `activity_log` | text | No | Historical lane changes |
| `history` | list[HistoryEntry] | No | Structured history (legacy) |

**Location**: `kitty-specs/{feature-id}/tasks/WP##-description.md`

**File Format**:

```yaml
---
work_package_id: "WP01"
title: "Implement core functionality"
lane: "doing"
phase: "Phase 1"
assignee: ""
activity_log: |
  - 2025-12-17T10:00:00Z – agent-001 – lane=planned – Created
  - 2025-12-17T14:30:00Z – agent-001 – lane=doing – Started implementation
---

[Markdown content with implementation details]
```

**Constraints**:

- `work_package_id` must be unique within feature
- `lane` must be valid Lane enum value
- File lives in flat `tasks/` directory (never in subdirectories)

### Lane (Enum)

Workflow status for a work package.

| Value | Description |
|-------|-------------|
| `planned` | Work defined but not started |
| `doing` | Work in progress |
| `for_review` | Implementation complete, awaiting review |
| `done` | Reviewed and accepted |

**Valid Transitions**:

```
planned → doing → for_review → done
                      ↓
                   doing (rework)
```

**Source of Truth**: The `lane:` YAML frontmatter field in the WP file.

**Not Used**: Directory location (deprecated with this feature).

### HistoryEntry (Embedded)

Legacy structured history entry (retained for backwards compatibility).

| Attribute | Type | Description |
|-----------|------|-------------|
| `timestamp` | ISO datetime | When change occurred |
| `lane` | Lane | Lane at time of entry |
| `agent` | string | Agent that made change |
| `shell_pid` | string | Process ID |
| `action` | string | Description of action |

**Note**: New implementations should use `activity_log` (text format) instead.

## State Transitions

### Lane Update Flow

**Note**: As of v0.11.1+, use `spec-kitty agent workflow implement/review` commands. This describes the underlying mechanism.

```
1. User/Agent invokes: spec-kitty agent workflow implement WP## (or legacy: tasks_cli.py update)
2. System locates WP file in flat tasks/ directory
3. System validates new lane value
4. System updates lane: field in frontmatter
5. System appends activity_log entry
6. System saves file (atomic write)
```

### Migration Flow

```
1. User invokes: spec-kitty upgrade
2. System scans kitty-specs/ and .worktrees/*/kitty-specs/
3. For each feature with lane subdirectories:
   a. Read all WP files from planned/, doing/, for_review/, done/
   b. Move files to flat tasks/ directory
   c. Ensure lane: frontmatter matches source directory
   d. Remove empty lane subdirectories
4. System reports migration summary
```

## Directory Structure

### Before Migration (Legacy)

```
kitty-specs/007-feature/tasks/
├── planned/
│   └── WP01-setup.md
├── doing/
│   └── WP02-implement.md
├── for_review/
│   └── WP03-test.md
├── done/
│   └── WP04-deploy.md
└── README.md
```

### After Migration (New)

```
kitty-specs/007-feature/tasks/
├── WP01-setup.md       # lane: "planned"
├── WP02-implement.md   # lane: "doing"
├── WP03-test.md        # lane: "for_review"
├── WP04-deploy.md      # lane: "done"
└── README.md
```

## Validation Rules

### Lane Field Validation

| Rule | Error Message |
|------|---------------|
| Missing `lane:` field | "Warning: WP {id} missing lane field, defaulting to 'planned'" |
| Invalid `lane:` value | "Error: Invalid lane '{value}'. Valid lanes: planned, doing, for_review, done" |

### Legacy Format Detection

| Condition | Detection |
|-----------|-----------|
| Directory exists: `tasks/planned/` with .md files | Legacy format |
| Directory exists: `tasks/doing/` with .md files | Legacy format |
| Directory exists: `tasks/for_review/` with .md files | Legacy format |
| Directory exists: `tasks/done/` with .md files | Legacy format |
| Only flat .md files in `tasks/` | New format |

## API Contracts

### Update Command

**Command**: `tasks_cli.py update <feature> <wp_id> <lane> [--note "message"]` (deprecated - use `spec-kitty agent workflow implement/review`)

**Parameters**:

- `feature`: Feature ID (e.g., "007-frontmatter-only-lane")
- `wp_id`: Work package ID (e.g., "WP01")
- `lane`: Target lane (planned|doing|for_review|done)
- `--note`: Optional activity log message

**Behavior**:

1. Validate lane value
2. Locate WP file in `tasks/`
3. Update `lane:` frontmatter field
4. Append activity log entry with timestamp, agent, new lane
5. Return success/failure status

**Output** (success):

```
Updated WP01 to lane 'for_review'
```

**Output** (legacy format detected):

```
Error: Legacy directory-based lanes detected.
Run 'spec-kitty upgrade' to migrate to frontmatter-only lanes.
```

### Status Command

**Command**: `tasks_cli.py status [feature]`

**Parameters**:

- `feature`: Optional. Auto-detected from worktree if omitted.

**Output**:

```
Feature: 007-frontmatter-only-lane

PLANNED (1)
  WP01  Setup project structure

DOING (2)
  WP02  Implement core functionality
  WP03  Write unit tests

FOR REVIEW (1)
  WP04  Update documentation

DONE (0)
  (none)
```
