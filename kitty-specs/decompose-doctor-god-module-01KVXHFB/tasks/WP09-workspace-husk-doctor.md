---
work_package_id: WP09
title: _workspace_husk_doctor extraction
dependencies:
- WP08
requirement_refs:
- FR-003
- FR-004
tracker_refs:
- '2059'
planning_base_branch: prog/2059-doctor
merge_target_branch: prog/2059-doctor
branch_strategy: Planning artifacts for this mission were generated on prog/2059-doctor. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into prog/2059-doctor unless the human explicitly redirects the landing branch.
created_at: '2026-06-24T19:54:56+00:00'
subtasks:
- T025
- T026
- T027
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3468271"
history:
- date: '2026-06-24'
  action: created
  actor: claude
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/cli/commands/_workspace_husk_doctor.py
create_intent:
- src/specify_cli/cli/commands/_workspace_husk_doctor.py
- tests/specify_cli/cli/commands/test_workspace_husk_doctor.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/_workspace_husk_doctor.py
- tests/specify_cli/cli/commands/test_workspace_husk_doctor.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile via the `/ad-hoc-profile-load` skill (profile: **randy-reducer**, role: implementer). Adopt its boundaries, governance scope, and initialization declaration for this work package. Then return here.

## Objective

Extract the workspace-husk cluster (C) into a standalone `_workspace_husk_doctor.py` (cohesive — standalone, not folded into a `_misc` catch-all per data-model.md).

## Context

- Cluster C (research §2, lines 159-237 + 1031-1065): `_workspace_husk_status_label` (159), `_emit_workspace_husk_fix` (167), `_emit_workspace_husk_report` (214), `workspaces` cmd (1031).
- The `workspaces` command flags: `--fix`, `--json`. Exit contract: 0 clean / 1 husks-or-error. Husk status comes via the `status` package; the heavy import stays function-local per the existing pattern.

## Subtasks

### T025 — Create `_workspace_husk_doctor.py`
- Move Cluster C into the sibling, importing shared infra from `_doctor_shared`. Keep domain imports function-local. Confirm each function ≤15 CC (these are already small).

### T026 — Delegate
- `workspaces` command body becomes a thin shell delegating to the sibling, preserving `--fix`/`--json` and the 0/1 (clean / husks-or-error) exit contract.

### T027 — Focused tests
- `test_workspace_husk_doctor.py`: per-helper tests for status-label classification, fix emission, report emission, and the husk-present vs clean exit. ≥90% coverage.
- WP01 golden green.

## Branch Strategy

Planning branch & merge target: **`prog/2059-doctor`** (PR-bound to `main`). Worktrees per `lanes.json`. Commit with `--to-branch prog/2059-doctor`; transitions from the primary checkout CWD.

## Test Strategy (ATDD)

RED per-helper tests before the move; GREEN after. Golden green.

## Out-of-map edits

- `src/specify_cli/cli/commands/doctor.py` — delegate the `workspaces` body. Owned by WP11; sequential chain → no concurrent writer.

## Definition of Done

- Cluster C in standalone `_workspace_husk_doctor.py` (no `_misc` catch-all).
- `--fix`/`--json` + 0/1 exit contract byte-preserved (golden green).
- ≥90% coverage; ruff + mypy --strict clean, zero new suppressions.

## Risks

- Husk `--fix` vs report exit (0 clean / 1 husks-or-error) must be preserved.

## Reviewer Guidance

Recommended reviewer: standard. Verify standalone extraction, exit contract unchanged, ≥90% coverage, golden green.

## Activity Log

- 2026-06-24T19:54:56Z – claude – planning – WP created (deps WP08).
- 2026-06-24T22:16:32Z – claude:opus:randy-reducer:implementer – shell_pid=3436325 – Assigned agent via action command
- 2026-06-24T22:25:44Z – claude:opus:randy-reducer:implementer – shell_pid=3436325 – Cluster C standalone-extracted; 100% cov; golden+husk tests green
- 2026-06-24T22:26:19Z – claude:opus:reviewer-renata:reviewer – shell_pid=3468271 – Started review via action command
- 2026-06-24T22:29:38Z – user – shell_pid=3468271 – Cluster C in standalone _workspace_husk_doctor (no _misc); --fix/--json+0/1 exit byte-preserved (golden+test_doctor_husks+1833 green); domain imports func-local; repo_root injected from shell preserves locate seam; one-way imports AST-verified; 100% coverage; mypy --strict clean
