---
work_package_id: WP03
title: Migrate agent-CLI cluster to the read seam
dependencies:
- WP02
requirement_refs:
- FR-002
- NFR-002
planning_base_branch: fix/read-side-placement-seam-migration
merge_target_branch: fix/read-side-placement-seam-migration
branch_strategy: Planning artifacts for this mission were generated on fix/read-side-placement-seam-migration. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/read-side-placement-seam-migration unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
phase: Phase 3 - Migrate
history:
- at: '2026-07-27T12:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent:
- tests/specify_cli/cli/commands/agent/test_read_seam_migration_agent.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/agent/**
- tests/specify_cli/cli/commands/agent/test_read_seam_migration_agent.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – Migrate agent-CLI cluster

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load` to load `python-pedro` (implementer, claude).

## Objective
Apply the **shared migration procedure** (see [tasks.md](../tasks.md) "The shared migration procedure") to the bypass sites in `src/specify_cli/cli/commands/agent/**`, per the WP02 classification ledger. This cluster includes the highest-concentration file `workflow.py` (~17 sites) — take care with mixed read intents.

## Subtasks
### T007 — Migrate per ledger
For each owned file, apply its ledger verdict: migrate-fail-loud → `placement_seam(root,slug).read_dir(kind)` (reuse the seam + `CoordinationBranchDeleted`; retrospective→`resolve_retrospective_home`); stay-lenient → leave + ensure WP08 allow-list carries a descriptor. Do not add a second read authority.
### T008 — Behavior-preservation tests
`tests/specify_cli/cli/commands/agent/test_read_seam_migration_agent.py`: for representative migrated sites, healthy-case resolves the identical dir (NFR-002) and deleted-coord now raises `CoordinationBranchDeleted`.

## Gates (`uv run`)
`PWHEADLESS=1 uv run pytest tests/specify_cli/cli/commands/agent/ -q`; `uv run ruff check <changed>`; `uv run mypy` (project-mode). Classify any pre-existing reds per the baseline-red gotcha.

## DoD / Review
All owned bypass sites resolved per ledger; healthy-case identical; no forked authority. Finish: commit, `mark-status T007 T008 --status done`, `move-task WP03 --to for_review`.
