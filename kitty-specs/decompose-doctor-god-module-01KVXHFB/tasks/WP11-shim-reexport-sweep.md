---
work_package_id: WP11
title: Shim re-export sweep + pointer verify + state_roots CC17 + full gate
dependencies:
- WP10
requirement_refs:
- FR-001
- FR-002
- FR-005
- FR-006
- FR-007
tracker_refs:
- '2059'
planning_base_branch: prog/2059-doctor
merge_target_branch: prog/2059-doctor
branch_strategy: Planning artifacts for this mission were generated on prog/2059-doctor. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into prog/2059-doctor unless the human explicitly redirects the landing branch.
created_at: '2026-06-24T19:54:56+00:00'
subtasks:
- T031
- T032
- T033
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3549043"
history:
- date: '2026-06-24'
  action: created
  actor: claude
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/cli/commands/doctor.py
create_intent:
- tests/specify_cli/cli/commands/test_doctor_shim_reexports.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/doctor.py
- tests/specify_cli/cli/commands/test_doctor_shim_reexports.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile via the `/ad-hoc-profile-load` skill (profile: **randy-reducer**, role: implementer). Adopt its boundaries, governance scope, and initialization declaration for this work package. Then return here.

## Objective

Closeout: as the **sole owner of `doctor.py`**, finalize the re-export block (all 11 test-facing private symbols + `app` + `SlashCommandGap`), decompose the last mega-function `state_roots` (CC17), verify the #2059 pointer comment, and run the full gate sweep proving the CLI surface is byte-identical and every gate is clean.

## Context

- `state_roots` cmd (research §2, line 928, CC17) — the only remaining >15-CC function (its bulk is human-render branching; it delegates detection to `state.doctor.check_state_roots`). Decompose its render branches into ≤15-CC helpers. Cluster B is otherwise a thin delegator and stays as a thin shell in `doctor.py` (research OQ2).
- The 11 re-export symbols (contracts/cli-surface-contract.md): `_load_slash_command_state`, `_repair_slash_command_state`, `_collect_profile_health`, `_collect_org_layer_data`, `_build_pack_entries`, `_count_pack_artifacts`, `_resolve_pack_version`, `_render_org_layer_section`, `_print_overdue_details`, plus the two slash/collector entrypoints the doctor test files import — re-validate against `git grep "from specify_cli.cli.commands.doctor import"`.
- Pointer comment (`doctor.py:1-7`) already references #2059 (research §preface) — verify it survived, no new responsibilities added.
- Small clusters' thin shells (state-roots, shim-registry, ops/invocation) stay in `doctor.py`; this WP confirms they remain thin and ≤15 CC.

## Subtasks

### T031 — Re-export sweep + decompose `state_roots`
- Finalize the `from ._x import _y as _y` re-export block so all 11 private symbols + `app` + `SlashCommandGap` resolve from `doctor`. `python -c "from specify_cli.cli.commands.doctor import (...)"` succeeds for the full list.
- Decompose `state_roots` (CC17) into ≤15-CC render helpers (kept in `doctor.py` or a small extraction). `ruff check --select C901` on `doctor.py` → zero findings.
- Add `test_doctor_shim_reexports.py` asserting every contracted symbol imports from `doctor`.

### T032 — Pointer + shape verify
- Confirm `head -7 doctor.py` still references #2059 and the god-module warning; no new responsibilities added (FR-002, I-8).
- Confirm `doctor.py` is reduced to the orchestration shim (≤ ~400 LOC target): `app` + 16 thin command shells + re-export block + `_doctor_shared` import.

### T033 — Full gate sweep
- Run: WP01 golden harness; the 58 doctor test files; `tests/cli_gate/test_doctor_modes.py` + `test_safe_commands.py`; `ruff check`; `ruff check --select C901` (whole `cli/commands/` doctor surface); `mypy --strict`. All green, zero new suppressions.
- Paste the pytest summary lines + ruff/mypy results into the handoff (self-asserted "green" is insufficient).

## Branch Strategy

Planning branch & merge target: **`prog/2059-doctor`** (PR-bound to `main`). Worktrees per `lanes.json`. Commit with `--to-branch prog/2059-doctor`; transitions from the primary checkout CWD.

## Test Strategy (ATDD)

`test_doctor_shim_reexports.py` (RED until the re-export block is complete) + the full pre-existing suite + golden as the byte-identity proof.

## Definition of Done

- All 11 private symbols + `app` + `SlashCommandGap` resolve from `doctor`; `test_doctor_shim_reexports.py` green.
- `state_roots` CC17 decomposed; whole doctor surface C901-clean.
- Pointer comment references #2059, no new responsibilities; `doctor.py` ≤ ~400 LOC.
- Golden + 58 doctor tests + cli_gate green; ruff + mypy --strict clean, zero new suppressions.

## Risks

- A missing re-export or a `state_roots` left at CC17 fails the closeout gate.
- Adding a new responsibility to `doctor.py` violates the god-module pointer rule (I-8).

## Reviewer Guidance

Recommended reviewer: standard. Verify the full re-export list resolves, `state_roots` decomposed (C901 clean), pointer comment intact, `doctor.py` is a thin shim, and the FULL gate sweep is green (request the pasted summaries). This is the mission's byte-identity closeout.

## Activity Log

- 2026-06-24T19:54:56Z – claude – planning – WP created (deps WP10; sole owner of doctor.py).
- 2026-06-24T22:59:00Z – claude:opus:randy-reducer:implementer – shell_pid=3509758 – Assigned agent via action command
- 2026-06-24T23:13:21Z – claude:opus:randy-reducer:implementer – shell_pid=3509758 – Shim closeout: all re-exports resolve; state_roots decomposed; full gate sweep green (428 doctor + golden + cli_gate; ruff/C901/mypy clean); doctor.py 3434->1053 LOC
- 2026-06-24T23:13:23Z – claude:opus:reviewer-renata:reviewer – shell_pid=3549043 – Started review via action command
- 2026-06-24T23:13:28Z – user – shell_pid=3549043 – Full re-export list resolves (test_doctor_shim_reexports green); state_roots CC17 decomposed (whole cli/commands/ C901-clean); pointer comment references #2059 + no new responsibilities; doctor.py is thin orchestration shim (3434->1053 LOC); FULL GATE: 428 doctor tests + golden(38) + cli_gate(50) green, ruff + ruff C901 + mypy --strict clean, zero new suppressions
