---
work_package_id: WP07
title: Migrate core/context/workspace/plan/misc cluster
dependencies:
- WP02
requirement_refs:
- FR-002
- NFR-002
planning_base_branch: fix/read-side-placement-seam-migration
merge_target_branch: fix/read-side-placement-seam-migration
branch_strategy: Planning artifacts for this mission were generated on fix/read-side-placement-seam-migration. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/read-side-placement-seam-migration unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
phase: Phase 3 - Migrate
history:
- at: '2026-07-27T12:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/context/resolver.py
create_intent:
- tests/specify_cli/test_read_seam_migration_core.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/acceptance/__init__.py
- src/specify_cli/agent_tasks_ports.py
- src/specify_cli/agent_utils/status.py
- src/specify_cli/context/resolver.py
- src/specify_cli/core/stale_detection.py
- src/specify_cli/core/worktree_topology.py
- src/specify_cli/doctrine_synthesizer/apply.py
- src/specify_cli/manifest.py
- src/specify_cli/mission_loader/command.py
- src/specify_cli/missions/plan/plan_interview.py
- src/specify_cli/missions/plan/specify_interview.py
- src/specify_cli/orchestrator_api/commands.py
- src/specify_cli/sync/events.py
- src/specify_cli/task_utils/support.py
- src/specify_cli/workspace/context.py
- src/runtime/next/runtime_bridge_identity.py
- tests/specify_cli/test_read_seam_migration_core.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP07 – Migrate core/context/workspace/plan/misc cluster

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load` to load `python-pedro` (implementer, claude).

## Objective
Apply the **shared migration procedure** ([tasks.md](../tasks.md)) per the WP02 ledger to the remaining consumers (owned_files list). Two special cases:
- `src/runtime/next/runtime_bridge_identity.py` — under the shared-package boundary (`src/runtime/`). Confirm the CLAUDE.md shared-package-boundary rules permit routing it through `placement_seam` (public import) vs keeping it public-import-only; follow the ledger's decision and record rationale if it stays.
- `task_utils/support.py` — verify whether it is a caller or infra; follow the ledger.
- `workspace/context.py` (~7 sites) is the hot spot in this cluster.

## Subtasks
### T015 — Migrate per ledger (as WP03 T007).
### T016 — Behavior-preservation tests: `tests/specify_cli/test_read_seam_migration_core.py`.

## Gates
`PWHEADLESS=1 uv run pytest tests/specify_cli/test_read_seam_migration_core.py tests/specify_cli/workspace/ tests/specify_cli/context/ -q`; `ruff`; `mypy` project-mode; if you touch `src/runtime/`, run `pytest tests/architectural/test_shared_package_boundary.py -q`.

## DoD / Review
Owned bypass sites resolved per ledger; shared-package boundary respected; healthy-case identical. Finish: commit, `mark-status T015 T016 --status done`, `move-task WP07 --to for_review`.
