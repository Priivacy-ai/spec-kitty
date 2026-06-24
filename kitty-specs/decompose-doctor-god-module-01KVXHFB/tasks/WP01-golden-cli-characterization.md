---
work_package_id: WP01
title: Golden CLI characterization harness
dependencies: []
requirement_refs:
- FR-001
- FR-002
tracker_refs:
- '2059'
planning_base_branch: prog/2059-doctor
merge_target_branch: prog/2059-doctor
branch_strategy: Planning artifacts for this mission were generated on prog/2059-doctor. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into prog/2059-doctor unless the human explicitly redirects the landing branch.
created_at: '2026-06-24T19:54:56+00:00'
subtasks:
- T001
- T002
- T003
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2983459"
history:
- date: '2026-06-24'
  action: created
  actor: claude
agent_profile: randy-reducer
authoritative_surface: tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py
create_intent:
- tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py
execution_mode: code_change
owned_files:
- tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile via the `/ad-hoc-profile-load` skill (profile: **randy-reducer**, role: implementer). Adopt its boundaries, governance scope, and initialization declaration for this work package. Then return here.

## Objective

Capture a **golden characterization test** of the `spec-kitty doctor` CLI surface BEFORE any extraction begins. This is the single objective proof that the public surface stays byte-identical (FR-001, C-005). Nothing today asserts the full 16-subcommand contract as one byte-stable snapshot — this WP creates it and it must pass at HEAD against the un-refactored `doctor.py`.

## Context

- The frozen contract is [contracts/cli-surface-contract.md](../contracts/cli-surface-contract.md): 16 subcommand names, each subcommand's flags/params, per-subcommand `--help`, and the documented exit-code contract.
- `app = typer.Typer(name="doctor", ...)` is defined at `doctor.py:79`; the 16 `@app.command(name=...)` decorators are enumerable via `app.registered_commands`.
- Three name paths are load-bearing for cross-module coupling (`compat/safety_modes.py:186-194`, `__init__.py` argv fast-paths): `doctor skills`, `doctor restart-daemon`, `doctor sparse-checkout --fix`. The harness MUST exercise these names.

## Subtasks

### T001 — Enumerate `app.registered_commands`
- Assert exactly the 16 frozen names are registered (set equality, order-independent): `command-files`, `skills`, `tool-surfaces`, `state-roots`, `workspaces`, `identity`, `topology`, `sparse-checkout`, `shim-registry`, `invocation-pairing`, `ops`, `orphan-daemons`, `restart-daemon`, `mission-state`, `doctrine`, `coordination`.
- For each subcommand, assert its parameter set (flag names + arity) matches the contract table — so a dropped/renamed flag fails the test.

### T002 — Snapshot each subcommand `--help`
- Render `--help` per subcommand via `typer.testing.CliRunner` and byte-pin each (snapshot or inline expected). A help-text drift must fail.

### T003 — Pin exit-code contracts
- Assert: `doctor ops --threshold 5` (without `--close-stale`) raises `BadParameter`; `doctor skills` 0/1/2; `doctor restart-daemon` 0/1/2/3; `doctor sparse-checkout --fix` reaches the CI-refusal/clean path. Explicitly invoke the `skills`, `restart-daemon`, and `sparse-checkout` names so name preservation is enforced.
- Run the full new test at HEAD: it MUST pass against the current (un-refactored) `doctor.py` — this is the baseline every later WP re-runs.

## Branch Strategy

Planning branch & merge target: **`prog/2059-doctor`** (PR-bound to `main`). Execution worktrees are allocated per computed lane from `lanes.json` at implement time. Commit with explicit `--to-branch prog/2059-doctor` on `safe-commit`; run status transitions from the primary checkout CWD.

## Test Strategy (ATDD)

This WP *is* the test. The deliverable is the golden harness itself, green at HEAD. No source change.

## Definition of Done

- `test_doctor_cli_surface_golden.py` exists and passes at HEAD against the un-refactored `doctor.py`.
- It pins the 16 names, per-subcommand params, per-subcommand `--help` bytes, and the documented exit codes, including the three load-bearing names.
- `ruff` + `mypy --strict` clean on the new test file.

## Risks

- A too-loose snapshot won't detect flag/help drift — pin names + params + help bytes, not just presence.

## Reviewer Guidance

Recommended reviewer: standard. Verify the test enumerates all 16 names by set-equality, pins per-subcommand params and `--help`, asserts the `ops --threshold`/`skills`/`restart-daemon` exit contracts, and is green at HEAD. This harness gates every subsequent extraction WP.

## Activity Log

- 2026-06-24T19:54:56Z – claude – planning – WP created (golden harness, no deps).
- 2026-06-24T20:24:58Z – claude:opus:randy-reducer:implementer – shell_pid=2957510 – Assigned agent via action command
- 2026-06-24T20:31:07Z – claude:opus:randy-reducer:implementer – shell_pid=2957510 – Golden CLI characterization green at HEAD
- 2026-06-24T20:31:14Z – claude:opus:reviewer-renata:reviewer – shell_pid=2983459 – Started review via action command
- 2026-06-24T20:31:45Z – user – shell_pid=2983459 – Golden harness pins 16 names, param arity, --help snapshots, exit-code contracts incl 3 load-bearing names; green at HEAD; ruff/mypy clean; no source change
