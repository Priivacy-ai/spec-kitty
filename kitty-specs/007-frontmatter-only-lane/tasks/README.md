# Tasks Directory

This directory contains work package (WP) prompt files for the feature.

## Directory Structure

All WP files live in this flat directory:
```
tasks/
├── WP01-setup.md
├── WP02-implement.md
├── WP03-test.md
└── README.md
```

## Lane Management

Each WP file has a `lane:` field in its YAML frontmatter:
- `planned` - Not yet started
- `doing` - In progress
- `for_review` - Ready for review
- `done` - Complete

To change a WP's lane:
```bash
python3 .kittify/scripts/tasks/tasks_cli.py update <feature> <WP> <lane>
```

Or edit the `lane:` field directly in the WP file.

## Work Package File Format

Each WP file **MUST** use YAML frontmatter:

```yaml
---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
title: "Work Package Title"
phase: "Phase 1 - Setup"
lane: "planned"  # Edit directly or use: tasks_cli.py update
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-01-01T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Work Package Title

[Content follows...]
```

## File Naming

- Format: `WP01-kebab-case-slug.md` (no extra hyphens in WP number)
- Examples: `WP01-setup-infrastructure.md`, `WP02-user-auth.md`

## Viewing Status

```bash
python3 .kittify/scripts/tasks/tasks_cli.py status <feature>
```
