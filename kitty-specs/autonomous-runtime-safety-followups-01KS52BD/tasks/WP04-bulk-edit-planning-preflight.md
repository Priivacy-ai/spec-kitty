---
work_package_id: WP04
title: Bulk-edit planning pre-flight
dependencies: []
requirement_refs:
- FR-010
- FR-011
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
- T020
agent: ''
history:
- at: '2026-05-21T10:53:40Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: runtime-riley
authoritative_surface: src/specify_cli/bulk_edit/
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/bulk_edit/**
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/cli/commands/agent/workflow.py
- src/specify_cli/mission_metadata.py
- tests/agent/test_bulk_edit_planning_preflight.py
- tests/cli/test_implement_bulk_edit_planning.py
role: implementer
tags: []
---

# Work Package Prompt: WP04 - Bulk-edit planning pre-flight

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load runtime-riley
```

## Objective

Recognize a WP authoring `occurrence_map.yaml` as bulk-edit planning, not an
active rewrite that must be suppressed with `--acknowledge-not-bulk-edit`.

## Context

Issue #1257 reports that `agent action implement WP01` blocks when the mission
spec mentions future bulk edits even though the WP deliverable is the occurrence
map itself.

## Subtasks & Detailed Guidance

### T016 - Add planning false-positive regression

Create a fixture with bulk-edit-like spec text and a claimed WP whose
`owned_files` includes `occurrence_map.yaml`.

### T017 - Inspect claimed WP frontmatter

At implementation pre-flight, load the claimed WP metadata and identify
occurrence-map/planning-artifact ownership.

### T018 - Downgrade planning warning

Make the inferred bulk-edit warning informational for the planning WP.

### T019 - Preserve active rewrite gates

Add negative coverage that active rewrite WPs still require `change_mode:
bulk_edit` and valid occurrence-map coverage when applicable.

### T020 - Verify

Run:

```bash
uv run pytest tests/agent/test_bulk_edit_planning_preflight.py tests/cli/test_implement_bulk_edit_planning.py
uv run mypy --strict src/specify_cli/bulk_edit src/specify_cli/cli/commands/implement.py src/specify_cli/cli/commands/agent/workflow.py src/specify_cli/mission_metadata.py
```

## Branch Strategy

Planning/base branch: `main`. Final merge target: `main`. Use the runtime
resolved lane workspace.

## Definition of Done

- Occurrence-map planning WP no longer needs `--acknowledge-not-bulk-edit`.
- Active rewrite safety remains unchanged.
- No changes to the bulk-edit skill itself.

## Reviewer Guidance

Check for accidental broad bypasses. The exception must be WP-specific.

## Activity Log

- 2026-05-21T10:53:40Z -- system -- Prompt created.
