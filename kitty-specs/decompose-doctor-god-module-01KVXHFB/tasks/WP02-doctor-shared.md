---
work_package_id: WP02
title: _doctor_shared single console/guard home
dependencies:
- WP01
requirement_refs:
- FR-007
tracker_refs:
- '2059'
planning_base_branch: prog/2059-doctor
merge_target_branch: prog/2059-doctor
branch_strategy: Planning artifacts for this mission were generated on prog/2059-doctor. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into prog/2059-doctor unless the human explicitly redirects the landing branch.
created_at: '2026-06-24T19:54:56+00:00'
subtasks:
- T004
- T005
- T006
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3044423"
history:
- date: '2026-06-24'
  action: created
  actor: claude
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/cli/commands/_doctor_shared.py
create_intent:
- src/specify_cli/cli/commands/_doctor_shared.py
- tests/specify_cli/cli/commands/test_doctor_shared.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/_doctor_shared.py
- tests/specify_cli/cli/commands/test_doctor_shared.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile via the `/ad-hoc-profile-load` skill (profile: **randy-reducer**, role: implementer). Adopt its boundaries, governance scope, and initialization declaration for this work package. Then return here.

## Objective

Extract the shared infrastructure (`console`, `_json_output_guard`, `_json_error`, `_is_interactive_environment`, and the module constants) into a new `_doctor_shared.py` as the **single canonical home (H1)** — extracted FIRST so every sibling (WP03–WP10) imports a stable surface. This resolves the dominant circular-import hazard: every module that emits must use the SAME `Console()` instance, never re-instantiate one.

## Context

- Research §6 / data-model.md I-3: `_profile_health_render.console` is the single Console today and `doctor.py:85-103` re-imports it. A per-module `Console()` breaks `--json` stdout cleanliness and the byte-pinned doctrine-selections snapshot.
- Shared infra in `doctor.py` to move: `_is_interactive_environment` (62), `_json_output_guard` (109), `_json_error` (125), constants `_CI_ENV_VARS`/`_STARTED_AT_COLUMN`/`_NOT_IN_PROJECT_MESSAGE` (47-59), plus the `console` re-export.
- WP01's golden harness must stay green throughout.

## Subtasks

### T004 — Create `_doctor_shared.py`
- Create `src/specify_cli/cli/commands/_doctor_shared.py` housing `console` (re-exported from `_profile_health_render` to keep the single instance, OR promoted here with `_profile_health_render` importing it back — pick one canonical direction and document it), `_json_output_guard`, `_json_error`, `_is_interactive_environment`, and the three constants.
- Imports only: stdlib + `rich` + `_profile_health_render` (for `console`, if re-exporting). No import of any cluster sibling and no import of `doctor.py` (one-way graph, I-2).

### T005 — Repoint `doctor.py` and `_profile_health_render`
- In `doctor.py`, replace the in-file shared-infra definitions with `from ._doctor_shared import console, _json_output_guard, _json_error, _is_interactive_environment, ...`. Reconcile `_profile_health_render` so exactly ONE `Console()` exists across the surface.
- Grep-confirm: `git grep -n "Console()" src/specify_cli/cli/commands/` shows a single instantiation.

### T006 — Focused tests + golden
- `test_doctor_shared.py`: cover `_json_output_guard` (stdout suppression), `_json_error` (envelope shape), `_is_interactive_environment` (env-gated branches), and the single-Console invariant (assert identity across import sites). ≥90% coverage of `_doctor_shared.py`.
- Re-run WP01 golden harness — byte-identical.

## Branch Strategy

Planning branch & merge target: **`prog/2059-doctor`** (PR-bound to `main`). Execution worktrees allocated per `lanes.json`. Commit with explicit `--to-branch prog/2059-doctor`; status transitions from the primary checkout CWD.

## Test Strategy (ATDD)

RED: a single-Console identity assertion + guard/error-shape tests fail before extraction (or are new). GREEN after the move. WP01 golden stays green.

## Out-of-map edits

- `src/specify_cli/cli/commands/doctor.py` — swap shared-infra defs to imports from `_doctor_shared` (delegation only; no behavior change). `doctor.py` is owned by WP11; this sequential-chain edit has no concurrent writer.
- `src/specify_cli/cli/commands/_profile_health_render.py` — console-home reconciliation only (single instance).

## Definition of Done

- `_doctor_shared.py` is the single home for console/guards/constants; exactly one `Console()` across the surface.
- `_doctor_shared` ≥90% covered; WP01 golden green; doctrine-selections snapshot green.
- `ruff` + `mypy --strict` clean, zero new suppressions; one-way import graph preserved.

## Risks

- A per-module `Console()` breaks `--json` cleanliness + the doctrine snapshot (H1) — assert single-instance identity.
- A sibling↔orchestrator import cycle if `_doctor_shared` imports `doctor.py` — it must not.

## Reviewer Guidance

Recommended reviewer: standard. Verify a single `Console()` instance, `_doctor_shared` imports nothing from siblings/orchestrator, guards/error-shape covered ≥90%, golden + doctrine snapshot green. This WP is the foundation every later sibling imports.

## Activity Log

- 2026-06-24T19:54:56Z – claude – planning – WP created (deps WP01; resolves H1).
- 2026-06-24T20:32:09Z – claude:opus:randy-reducer:implementer – shell_pid=2988975 – Assigned agent via action command
- 2026-06-24T20:43:16Z – claude:opus:randy-reducer:implementer – shell_pid=2988975 – _doctor_shared single console home; 100% cov; golden+doctrine snapshot green; ruff/mypy clean
- 2026-06-24T20:43:24Z – claude:opus:reviewer-renata:reviewer – shell_pid=3044423 – Started review via action command
- 2026-06-24T20:43:36Z – user – shell_pid=3044423 – Single Console() in cluster (identity asserted across 3 import sites); _doctor_shared imports stdlib+rich+_profile_health_render only (AST-verified, no sibling/orchestrator); guards+error+env branches 100% cov; golden+doctrine-selections snapshot green; ruff/mypy --strict clean; behavior-preserving delegation. Perf flake pre-existing on baseline.
