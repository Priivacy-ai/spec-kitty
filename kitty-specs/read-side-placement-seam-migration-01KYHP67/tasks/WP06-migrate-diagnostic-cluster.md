---
work_package_id: WP06
title: Migrate diagnostic-heavy cluster + leniency
dependencies:
- WP02
requirement_refs:
- FR-002
- FR-004
- NFR-001
- NFR-002
planning_base_branch: fix/read-side-placement-seam-migration
merge_target_branch: fix/read-side-placement-seam-migration
branch_strategy: Planning artifacts for this mission were generated on fix/read-side-placement-seam-migration. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/read-side-placement-seam-migration unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
phase: Phase 3 - Migrate
history:
- at: '2026-07-27T12:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/aggregate.py
create_intent:
- tests/specify_cli/test_read_seam_leniency.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/coordination/status_transition.py
- src/specify_cli/status/aggregate.py
- src/specify_cli/review/cycle.py
- src/specify_cli/dashboard/scanner.py
- src/specify_cli/retrospective/summary.py
- src/specify_cli/retrospective/writer.py
- src/specify_cli/dossier/api.py
- src/specify_cli/decisions/service.py
- tests/specify_cli/test_read_seam_leniency.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP06 – Migrate diagnostic-heavy cluster + leniency

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load` to load `python-pedro` (implementer, claude).

## Objective
Apply the **shared migration procedure** ([tasks.md](../tasks.md)) per the WP02 ledger to the diagnostic/audit-heavy cluster. **Expect many `stay-lenient` verdicts here** — these readers (status aggregation, dashboard scanner, coordination status, retrospective/dossier/decisions readers) walk corpora and must tolerate half-materialized/deleted coord branches. Do NOT blindly migrate them to fail-loud (NFR-001). This is the correctness-guard WP.

## Subtasks
### T013 — Migrate/keep-lenient per ledger
migrate-fail-loud sites → seam; stay-lenient sites → leave + ensure WP08 allow-list descriptor with rationale.
### T014 — NFR-001 leniency tests
`tests/specify_cli/test_read_seam_leniency.py`: for each stay-lenient diagnostic reader in this cluster, assert it returns (does NOT raise) against a deleted/half-materialized coord branch. Plus behavior-preservation for any migrated site.

## Gates
`PWHEADLESS=1 uv run pytest tests/specify_cli/test_read_seam_leniency.py tests/specify_cli/status/ tests/specify_cli/dashboard/ -q`; `ruff`; `mypy` project-mode.

## DoD / Review
No audit-path regression (NFR-001 tests green); stay-lenient sites recorded for WP08 allow-list; migrated sites healthy-case identical. Finish: commit, `mark-status T013 T014 --status done`, `move-task WP06 --to for_review`.
