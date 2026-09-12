---
work_package_id: WP04
title: Migrate CLI-commands cluster to the read seam
dependencies:
- WP02
requirement_refs:
- FR-002
- NFR-002
planning_base_branch: fix/read-side-placement-seam-migration
merge_target_branch: fix/read-side-placement-seam-migration
branch_strategy: Planning artifacts for this mission were generated on fix/read-side-placement-seam-migration. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/read-side-placement-seam-migration unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
phase: Phase 3 - Migrate
history:
- at: '2026-07-27T12:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent:
- tests/specify_cli/cli/commands/test_read_seam_migration_cli.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/*.py
- src/specify_cli/cli/commands/charter/_widen.py
- tests/specify_cli/cli/commands/test_read_seam_migration_cli.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP04 – Migrate CLI-commands cluster

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load` to load `python-pedro` (implementer, claude).

## Objective
Apply the **shared migration procedure** ([tasks.md](../tasks.md)) per the WP02 ledger to the top-level `src/specify_cli/cli/commands/*.py` bypass files (non-agent: `archive.py`, `_coordination_doctor.py`, `decision.py`, `merge.py`, `mission_type.py`, `next_cmd.py`, `reconcile.py`, `research.py`, `retrospect.py`, `validate_tasks.py`, `verify.py`) plus `charter/_widen.py`. Note `_coordination_doctor.py` is likely **stay-lenient** (diagnostic). Note `validate_tasks.py` is also touched by #2921's caller but on a different concern — coordinate line-ranges; owned_files stay disjoint from WP01.

## Subtasks
### T009 — Migrate per ledger
As WP03 T007, for this cluster.
### T010 — Behavior-preservation tests
`tests/specify_cli/cli/commands/test_read_seam_migration_cli.py` — healthy-case identical + deleted-coord raises, for migrated sites; leniency retained for stay-lenient ones.

## Gates
`PWHEADLESS=1 uv run pytest tests/specify_cli/cli/commands/ -q -k "read_seam or coordination_doctor or verify or reconcile"`; `ruff`; `mypy` project-mode.

## DoD / Review
Owned bypass sites resolved per ledger; diagnostic readers left lenient; healthy-case identical. Finish: commit, `mark-status T009 T010 --status done`, `move-task WP04 --to for_review`.
