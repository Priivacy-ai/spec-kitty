---
work_package_id: WP05
title: _command_surface_doctor + skills CC20 / repair CC16 decompose
dependencies:
- WP04
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-006
tracker_refs:
- '2059'
planning_base_branch: prog/2059-doctor
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on prog/2059-doctor. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into prog/2059-doctor unless the human explicitly redirects the landing branch.
created_at: '2026-06-24T19:54:56+00:00'
subtasks:
- T013
- T014
- T015
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/cli/commands/_command_surface_doctor.py
create_intent:
- src/specify_cli/cli/commands/_command_surface_doctor.py
- tests/specify_cli/cli/commands/test_command_surface_doctor.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/_command_surface_doctor.py
- tests/specify_cli/cli/commands/test_command_surface_doctor.py
role: implementer
tags: []
history:
- date: '2026-06-24'
  action: created
  actor: claude
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile via the `/ad-hoc-profile-load` skill (profile: **randy-reducer**, role: implementer). Adopt its boundaries, governance scope, and initialization declaration for this work package. Then return here.

## Objective

Extract the tool-surface + command-skill + slash-command cluster (A) into `_command_surface_doctor.py` and **decompose `skills` (CC20)** and **`_repair_command_skill_state` (CC16)** into ≤15-CC tested helpers. The `skills` command fuses command-skills + slash-commands into one payload, so these belong in one sibling (research OQ1).

## Context

- Cluster A (research §2, lines 135-924): `_vibe_skill_path_configured`, `_get_slash_command_agents`, `SlashCommandGap` (dataclass), `_load_slash_command_state`, `_print_slash_command_report`, `_repair_slash_command_state`, `_slash_command_payload`, `_load_and_optionally_repair_slash_commands`, `_print_slash_command_payload`, `_load_command_skill_state`, `_repair_command_skill_state` (CC16), `_command_skill_payload`, `_print_command_skill_paths`, `_print_command_skill_report`, `command_files` cmd, `skills` cmd (CC20), `_configured_tool_keys`, `_print_tool_surface_human`, `tool_surfaces` cmd.
- Test-facing re-exports: `SlashCommandGap`, `_load_slash_command_state`, `_repair_slash_command_state` (FR-006).
- **I-7 / safety coupling:** `doctor skills` and `doctor sparse-checkout` are safety-keyed by name in `compat/safety_modes.py`; `_is_doctor_skills_invocation` argv fast-path keys on `doctor skills`. Names stay byte-identical.

## Subtasks

### T013 — Create `_command_surface_doctor.py` + decompose
- Move Cluster A into the sibling, importing shared infra from `_doctor_shared`. Decompose `skills` (CC20) into ≤15-CC helpers (e.g. separate load / repair / payload-build / human-render / exit-code phases) and `_repair_command_skill_state` (CC16) into focused sub-steps.
- `ruff check --select C901` on the sibling → zero findings.

### T014 — Delegate + re-export
- `command-files`, `skills`, `tool-surfaces` command bodies become thin shells delegating to the sibling, preserving the 0/1/2 exit contracts (incl. not-in-project / unknown-kind / config-error).
- Re-export `SlashCommandGap`, `_load_slash_command_state`, `_repair_slash_command_state` from `doctor`.

### T015 — Focused tests
- `test_command_surface_doctor.py`: per-helper tests for slash/command-skill load + repair + payload + render + the decomposed `skills`/`_repair_command_skill_state` branches. ≥90% coverage.
- Run WP01 golden + `tests/cli_gate/test_doctor_modes.py` + `test_safe_commands.py` — all green (safety predicates keyed on the preserved names).

## Branch Strategy

Planning branch & merge target: **`prog/2059-doctor`** (PR-bound to `main`). Worktrees per `lanes.json`. Commit with `--to-branch prog/2059-doctor`; transitions from the primary checkout CWD.

## Test Strategy (ATDD)

RED per-helper tests (especially the decomposed `skills`/repair branches) before extraction; GREEN after. Golden + safety-mode suites green.

## Out-of-map edits

- `src/specify_cli/cli/commands/doctor.py` — delegate the three command bodies + re-export. Owned by WP11; sequential chain → no concurrent writer.

## Definition of Done

- Cluster A in `_command_surface_doctor.py`; `skills` CC20 + `_repair_command_skill_state` CC16 decomposed (C901 clean).
- `SlashCommandGap` + the two slash-state symbols re-export from `doctor`; safety-mode + argv-fast-path tests green (names preserved).
- ≥90% coverage; golden green; ruff + mypy --strict clean, zero new suppressions.

## Risks

- Renaming `skills`/`sparse-checkout`/`command-files`/`tool-surfaces` breaks safety predicates + argv fast-paths (I-7) — names are frozen.
- Relocating `skills` at CC20 or `_repair_command_skill_state` at CC16 fails the gate.

## Reviewer Guidance

Recommended reviewer: standard. Verify the decomposition (C901 clean), subcommand names unchanged, safety-mode + argv-fast-path tests green, ≥90% coverage, golden green.

## Activity Log

- 2026-06-24T19:54:56Z – claude – planning – WP created (deps WP04; decompose skills CC20 + repair CC16).
