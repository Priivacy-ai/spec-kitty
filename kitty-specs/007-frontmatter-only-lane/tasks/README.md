# Tasks Directory

This directory contains work package (WP) prompt files organized by kanban lane.

## Directory Structure

```
tasks/
├── planned/      # WP files ready for implementation
├── doing/        # WP files currently being worked on
├── for_review/   # WP files awaiting review
├── done/         # Completed WP files
└── README.md     # This file
```

## Work Package File Format

Each WP file **MUST** use YAML frontmatter (not markdown headers):

```yaml
---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
title: "Work Package Title"
phase: "Phase 1 - Setup"
lane: "planned"
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

# Work Package Prompt: WP01 – Work Package Title

[Content follows...]
```

## File Naming

- Format: `WP01-kebab-case-slug.md` (no extra hyphens in WP number)
- Examples: `WP01-setup-infrastructure.md`, `WP02-user-auth.md`

## Moving Between Lanes

Use the helper script:
```bash
.kittify/scripts/bash/tasks-move-to-lane.sh <FEATURE> <WPID> <lane>
```

Or manually:
1. Move the file to the target lane directory
2. Update the `lane` field in frontmatter
3. Add a history entry with timestamp
