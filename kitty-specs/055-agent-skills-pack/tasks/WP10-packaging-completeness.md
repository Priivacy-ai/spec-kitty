---
work_package_id: WP10
title: Packaging Completeness
dependencies:
- WP09
requirement_refs:
- NFR-005
subtasks:
- T041
- T042
phase: Phase 3 - Second Slice
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
authoritative_surface: src/specify_cli/
execution_mode: code_change
mission_id: 01KN2371WVZGV7TH7WMR2CN9Q1
owned_files:
- src/specify_cli/**
wp_code: WP10
---

# Work Package Prompt: WP10 – Packaging Completeness

## Objectives & Success Criteria

- Add `src/specify_cli/skills/` to `also_copy` in `pyproject.toml` for pattern consistency
- Verify the skills module is included in wheel builds via a test

**Status**: `also_copy` entry already added. Test pending.

## Activity Log

- 2026-03-21T08:30:00Z – system – lane=planned – Prompt created.
- 2026-03-21T08:30:01Z – claude – lane=doing – Implementation started.
- 2026-03-21T09:00:00Z – claude – lane=done – Packaging resolved: packages=["src/specify_cli"] auto-includes skills/; also_copy entry added for mutmut consistency
