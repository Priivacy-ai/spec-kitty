---
work_package_id: WP02
title: Sync-drain operations runbook
dependencies:
- WP01
requirement_refs:
- FR-002
- C-003
- NFR-001
- NFR-005
planning_base_branch: kitty/mission-workflow-self-doc
merge_target_branch: kitty/mission-workflow-self-doc
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-workflow-self-doc. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-workflow-self-doc unless the human explicitly redirects the landing branch.
subtasks:
- T004
- T005
history: []
authoritative_surface: docs/operations/
create_intent:
- docs/operations/sync-drain.md
execution_mode: code_change
owned_files:
- docs/operations/recovery-index.md
- docs/operations/toc.yml
tags: []
tracker_refs: []
---

## Objective
New `docs/operations/sync-drain.md` — the durable 3-gate drain, CITING gate-1's existing home.

## Subtasks
- **T004** Author `sync-drain.md` (frontmatter matching existing ops runbooks — `divio_type: none`/omit `type`; description 50–180). CITE `docs/operations/internal-hosted-readiness.md` (L35–158) for gate-1 (`SPEC_KITTY_ENABLE_SAAS_SYNC` — the rollout flag, NOT `..._ENABLED`; `sync doctor`). Restate only the genuinely-absent: gate-2 (legacy queue / `sync migrate`), gate-3 (TeamSpace blockers), and the false-green trap (`sync doctor` queue-depth 0 vs `sync status` Delivered) + `SPEC_KITTY_HOME` semantics. Drop the fixed #2995/#2985 defect analyses. Content anchor `SPEC_KITTY_ENABLE_SAAS_SYNC`.
- **T005** Register in `recovery-index.md` + `toc.yml`.

## Rules
Verify env-var names + command surfaces against current code/skills (C-005). Do NOT regenerate rollups (WP06). Terminology guard must pass. `.venv/bin/python`, never bare `uv run`.

## Done
Runbook accurate; gate-1 cited not restated; registered; terminology green.
