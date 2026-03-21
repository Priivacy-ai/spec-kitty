---
work_package_id: WP10
title: Packaging Completeness
lane: doing
dependencies:
- WP09
subtasks:
- T041
- T042
phase: Phase 3 - Second Slice
assignee: ''
agent: claude
shell_pid: ''
review_status: ''
reviewed_by: ''
requirement_refs:
- NFR-005
history:
- timestamp: '2026-03-21T08:30:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated for second slice
- timestamp: '2026-03-21T08:30:01Z'
  lane: doing
  agent: claude
  shell_pid: ''
  action: Implementation started
---

# Work Package Prompt: WP10 – Packaging Completeness

## Objectives & Success Criteria

- Add `src/specify_cli/skills/` to `also_copy` in `pyproject.toml` for pattern consistency
- Verify the skills module is included in wheel builds via a test

**Status**: `also_copy` entry already added. Test pending.

## Activity Log

- 2026-03-21T08:30:00Z – system – lane=planned – Prompt created.
- 2026-03-21T08:30:01Z – claude – lane=doing – Implementation started.
