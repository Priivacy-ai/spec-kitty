---
work_package_id: WP06
title: _mission_state_doctor extraction
dependencies:
- WP05
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
- T016
- T017
- T018
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3323546"
history:
- date: '2026-06-24'
  action: created
  actor: claude
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/cli/commands/_mission_state_doctor.py
create_intent:
- src/specify_cli/cli/commands/_mission_state_doctor.py
- tests/specify_cli/cli/commands/test_mission_state_doctor.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/_mission_state_doctor.py
- tests/specify_cli/cli/commands/test_mission_state_doctor.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile via the `/ad-hoc-profile-load` skill (profile: **randy-reducer**, role: implementer). Adopt its boundaries, governance scope, and initialization declaration for this work package. Then return here.

## Objective

Extract the mission-state audit/repair/teamspace-dry-run cluster (H) into `_mission_state_doctor.py`. The `mission_state` command is already dispatch-thin (delegates to `_validate_modes`/`_run_*` helpers); move its helpers with it and **drop its `# noqa: C901`** once they move (NFR-003 — no new suppressions, and this one becomes unnecessary).

## Context

- Cluster H (research §2, lines 1905-2426): `_print_rich_audit_report` (CC15), `_audit_fixture_root`, `_MissionStateMode` (enum), `_validate_modes`, `_resolve_fail_on`, `_resolve_audit_root`, `_emit_mission_state`, `_run_mission_repair`, `_run_teamspace_dry_run_mode`, `_emit_json_error`, `_audit_fail_gate`, `_run_audit_mode`, `mission_state` cmd (carries `# noqa: C901`).
- The command's contract: mode-exclusive (0 no-mode / 2 multi-mode-or-bad-fail-on); gate exit 1. Flags: `--audit`, `--fix`, `--teamspace-dry-run`, `--json`, `--mission`, `--fail-on`, `--fixture-dir`, `--include-fixtures`, `--manifest-path`, `--allow-dirty`.
- `_print_rich_audit_report` sits at CC15 (at the ceiling) — keep it ≤15.

## Subtasks

### T016 — Create `_mission_state_doctor.py`
- Move Cluster H helpers + the `_MissionStateMode` enum into the sibling, importing shared infra from `_doctor_shared`. Keep `_print_rich_audit_report` ≤15 CC (split if any edit nudges it over).

### T017 — Delegate + drop suppression
- `mission_state` command body stays a thin dispatch shell in `doctor.py`, delegating to `_validate_modes`/`_run_audit_mode`/`_run_mission_repair`/`_run_teamspace_dry_run_mode` now living in the sibling. Drop the `# noqa: C901` (the helpers it dispatched to have moved; the shell is well under 15).
- `ruff check --select C901` on `doctor.py` (the `mission_state` shell) + the sibling → zero findings, no suppression.

### T018 — Focused tests
- `test_mission_state_doctor.py`: per-helper tests for mode validation (exclusivity → exit 2), fail-on resolution, audit-root resolution, repair, teamspace-dry-run, audit-fail gate. ≥90% coverage.
- WP01 golden green.

## Branch Strategy

Planning branch & merge target: **`prog/2059-doctor`** (PR-bound to `main`). Worktrees per `lanes.json`. Commit with `--to-branch prog/2059-doctor`; transitions from the primary checkout CWD.

## Test Strategy (ATDD)

RED per-helper tests before the move; GREEN after. Mode-exclusivity + gate-exit assertions; golden green.

## Out-of-map edits

- `src/specify_cli/cli/commands/doctor.py` — delegate the `mission_state` dispatch shell + remove the `# noqa: C901`. Owned by WP11; sequential chain → no concurrent writer.

## Definition of Done

- Cluster H in `_mission_state_doctor.py`; `mission_state` shell is suppression-free and ≤15 CC.
- Mode-exclusivity (exit 2) + gate (exit 1) + the 10-flag set byte-preserved (golden green).
- ≥90% coverage; ruff + mypy --strict clean, zero new suppressions.

## Risks

- Dropping the `# noqa: C901` without the helpers actually moving would leave the shell over the ceiling — confirm with `ruff --select C901`.
- The mode-exclusivity matrix must be preserved exactly.

## Reviewer Guidance

Recommended reviewer: standard. Verify the suppression is dropped (and unnecessary), mode-exclusivity/gate exits unchanged, ≥90% coverage, golden green.

## Activity Log

- 2026-06-24T19:54:56Z – claude – planning – WP created (deps WP05; drop mission_state noqa).
- 2026-06-24T21:34:11Z – claude:opus:randy-reducer:implementer – shell_pid=3262641 – Assigned agent via action command
- 2026-06-24T21:49:57Z – claude:opus:randy-reducer:implementer – shell_pid=3262641 – Cluster H extracted; C901 noqa dropped; 95% cov; golden+mission-state tests green
- 2026-06-24T21:49:59Z – claude:opus:reviewer-renata:reviewer – shell_pid=3323546 – Started review via action command
- 2026-06-24T21:50:04Z – user – shell_pid=3323546 – Cluster H in _mission_state_doctor; mission-state shell suppression-free + <=15CC (C901 clean); mode-exclusivity exit2/no-mode exit0/gate exit1 byte-preserved (golden+test_doctor_mission_state green); locate seam retargeted to sibling; one-way imports AST-verified; 95% coverage; mypy --strict clean
