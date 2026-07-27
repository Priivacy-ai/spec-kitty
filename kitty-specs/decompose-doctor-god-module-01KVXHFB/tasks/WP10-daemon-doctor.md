---
work_package_id: WP10
title: _daemon_doctor extraction (orphan + restart)
dependencies:
- WP09
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
- T028
- T029
- T030
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3507046"
history:
- date: '2026-06-24'
  action: created
  actor: claude
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/cli/commands/_daemon_doctor.py
create_intent:
- src/specify_cli/cli/commands/_daemon_doctor.py
- tests/specify_cli/cli/commands/test_daemon_doctor.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/_daemon_doctor.py
- tests/specify_cli/cli/commands/test_daemon_doctor.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile via the `/ad-hoc-profile-load` skill (profile: **randy-reducer**, role: implementer). Adopt its boundaries, governance scope, and initialization declaration for this work package. Then return here.

## Objective

Extract the daemon cluster (I) — `orphan-daemons` + `restart-daemon` bodies — into a cohesive standalone `_daemon_doctor.py`, preserving the four-state `restart-daemon` exit contract and the `_is_doctor_restart_daemon_invocation` argv fast-path coupling.

## Context

- Cluster I (research §2, lines 2223-2358): `orphan_daemons` cmd (2223), `restart_daemon_cmd` (2308).
- Exit contracts: `orphan-daemons` 0 / 1 orphans; `restart-daemon` 0/1/2/3 (four-state). Both flags `--json`.
- **I-7 coupling:** `__init__.py:99,164-172,282-295` `_is_doctor_restart_daemon_invocation` keys on the `doctor restart-daemon` name string — keep the name byte-identical.

## Subtasks

### T028 — Create `_daemon_doctor.py`
- Move both command bodies' logic into the sibling, importing shared infra from `_doctor_shared`. Keep daemon-domain imports function-local. Confirm ≤15 CC.

### T029 — Delegate
- `orphan-daemons` and `restart-daemon` command bodies become thin shells delegating to the sibling, preserving the 0/1 and 0/1/2/3 exit contracts respectively.

### T030 — Focused tests
- `test_daemon_doctor.py`: tests for orphan detection (0 vs 1) and each of the four `restart-daemon` states. ≥90% coverage.
- Run WP01 golden + the argv-fast-path test (`doctor restart-daemon` recognized) green. Reuse fixtures from `test_doctor_restart_daemon.py`/`test_doctor_restart_daemon_timing.py` where useful.

## Branch Strategy

Planning branch & merge target: **`prog/2059-doctor`** (PR-bound to `main`). Worktrees per `lanes.json`. Commit with `--to-branch prog/2059-doctor`; transitions from the primary checkout CWD.

## Test Strategy (ATDD)

RED per-state tests before the move; GREEN after. Golden + argv-fast-path green.

## Out-of-map edits

- `src/specify_cli/cli/commands/doctor.py` — delegate the two daemon bodies. Owned by WP11; sequential chain → no concurrent writer.

## Definition of Done

- Cluster I in standalone `_daemon_doctor.py`.
- `restart-daemon` 0/1/2/3 + `orphan-daemons` 0/1 exit contracts byte-preserved; `restart-daemon` name unchanged (argv fast-path fires).
- ≥90% coverage; golden green; ruff + mypy --strict clean, zero new suppressions.

## Risks

- The four-state `restart-daemon` contract is easy to flatten — keep all four states covered.
- Renaming `restart-daemon` breaks the argv fast-path (I-7).

## Reviewer Guidance

Recommended reviewer: standard. Verify both exit contracts unchanged, the `restart-daemon` name preserved (fast-path test green), ≥90% coverage, golden green.

## Activity Log

- 2026-06-24T19:54:56Z – claude – planning – WP created (deps WP09).
- 2026-06-24T22:45:13Z – claude:opus:randy-reducer:implementer – shell_pid=3475045 – Assigned agent via action command
- 2026-06-24T22:58:36Z – claude:opus:randy-reducer:implementer – shell_pid=3475045 – Cluster I standalone-extracted; 4-state restart preserved; 100% cov; golden+fast-path green
- 2026-06-24T22:58:38Z – claude:opus:reviewer-renata:reviewer – shell_pid=3507046 – Started review via action command
- 2026-06-24T22:58:42Z – user – shell_pid=3507046 – Cluster I in standalone _daemon_doctor; restart-daemon 0/1/2/3 + orphan-daemons 0/1 byte-preserved (golden+restart_daemon[_timing]+argv-fast-path green); restart-daemon name unchanged (I-7); domain imports func-local; one-way imports AST-verified; 100% coverage; mypy --strict clean
