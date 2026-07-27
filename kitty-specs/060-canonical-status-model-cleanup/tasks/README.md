# Tasks Directory

This directory contains work package (WP) prompt files with static definitions in frontmatter.

## Directory Structure

```
tasks/
├── WP01-setup-infrastructure.md
├── WP02-user-authentication.md
├── WP03-api-endpoints.md
└── README.md
```

All WP files are stored flat in `tasks/`.

## Status Authority

WP status (lane) is NOT stored in frontmatter. The sole authority for WP lane state is `status.events.jsonl` in the feature directory, materialized as `status.json` by the reducer.

- To read WP status: `spec-kitty agent tasks status`
- To move a WP: `spec-kitty agent tasks move-task <WPID> --to <lane>`

Both commands operate on the canonical event log, not on WP files.

## Work Package File Format

Each WP file uses YAML frontmatter for **static definition only**:

```yaml
---
work_package_id: "WP01"
title: "Work Package Title"
dependencies: []
planning_base_branch: "main"
merge_target_branch: "main"
branch_strategy: "Branch from main."
subtasks:
  - "T001"
  - "T002"
execution_mode: "code_change"
owned_files:
  - "src/myapp/feature.py"
authoritative_surface: "src/myapp/"
requirement_refs:
  - "FR-001"
history:
  - at: "2026-01-01T00:00:00Z"
    actor: "planner"
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Work Package Title

[Content follows...]
```

Frontmatter does NOT include `lane`, `review_status`, `reviewed_by`, `review_feedback`, or `progress`. Those are managed by the canonical status model.

Operational metadata (`agent`, `assignee`, `shell_pid`) may be present for runtime coordination.

## File Naming

- Format: `WP01-kebab-case-slug.md`
- Examples: `WP01-setup-infrastructure.md`, `WP02-user-auth.md`
