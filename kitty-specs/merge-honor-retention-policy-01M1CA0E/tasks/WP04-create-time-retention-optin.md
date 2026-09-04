---
work_package_id: WP04
title: Create-time retention opt-in (mission create flags + mint)
dependencies:
- WP01
requirement_refs:
- FR-009
planning_base_branch: fix/3131-merge-retention
merge_target_branch: fix/3131-merge-retention
branch_strategy: Planning artifacts for this mission were generated on fix/3131-merge-retention. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/3131-merge-retention unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
history:
- at: '2026-08-31T16:30:00Z'
  actor: claude
  action: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/mission_creation.py
create_intent:
- tests/specify_cli/test_mission_create_retention.py
execution_mode: code_change
owned_files:
- src/specify_cli/core/mission_creation.py
- src/specify_cli/cli/commands/agent/mission_create.py
- tests/specify_cli/test_mission_create_retention.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
Before reading further, load your assigned agent profile via `/ad-hoc-profile-load python-pedro` (role: implementer). Then read `plan.md` decision 9 and `spec.md` FR-009 / User Story 3.

## Objective

Let a mission DECLARE retention at creation, so the policy is machine-readable
from the start (closes the loop that made #3131 possible). Depends on WP01's
schema fields.

## Context — read, do not re-derive
- `create_mission_core` in `src/specify_cli/core/mission_creation.py` (~342) —
  keyword-only policy params already exist (`pr_bound=False` ~351, `topology` ~352).
- Mint site: `mission_creation.py` ~694-711 (the meta build), persisted by
  `write_meta` at ~771.
- CLI wiring: `src/specify_cli/cli/commands/agent/mission_create.py` (the typer
  command that calls `create_mission_core`).

## Subtask guidance

### T014 — create_mission_core kwargs + conditional mint
- Add keyword-only `retain_branches: bool = False`, `retain_worktrees: bool = False`.
- At the mint site, write each field ONLY when True:
  `if retain_branches: meta["retain_branches"] = True` (and worktrees). Do NOT
  write `False` — non-retaining missions stay field-absent (SC-004, FR-009 AC-2).

### T015 — CLI flags
- Add `--retain-branches`/`--retain-worktrees` typer options (bool, default False)
  to `mission_create.py`; pass them into `create_mission_core`. Canonical naming
  (`retain`, no `feature*` alias); help text one-liner each.

### T016 — Tests
`tests/specify_cli/test_mission_create_retention.py`:
- create with both flags → `meta.json` has `retain_branches: true` / `retain_worktrees: true`.
- create with neither → both fields ABSENT (not `false`).
- create with one flag → only that field present.
- round-trip: `load_meta_fail_closed` reads the minted value back as `True`.

## Branch Strategy
Planning base and final merge target: `fix/3131-merge-retention`. Depends on WP01.

## Definition of Done
- Create-time flags mint the fields (True-only) into meta.json.
- Non-retaining create leaves fields absent.
- `ruff` + `mypy --strict` clean; help text present.

## Test surface
`PWHEADLESS=1 pytest tests/specify_cli/test_mission_create_retention.py -q`

## Reviewer guidance
- Confirm field-absent-when-false (no default-write) — the byte-identical guarantee.
- Confirm flag naming honors the terminology canon.
