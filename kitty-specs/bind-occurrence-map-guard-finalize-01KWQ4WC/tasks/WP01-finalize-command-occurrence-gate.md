---
work_package_id: WP01
title: Finalize-tasks command occurrence-map gate
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
tracker_refs: []
planning_base_branch: feat/bind-occurrence-map-guard-finalize
merge_target_branch: feat/bind-occurrence-map-guard-finalize
branch_strategy: Planning artifacts for this mission were generated on feat/bind-occurrence-map-guard-finalize. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/bind-occurrence-map-guard-finalize unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Finalize command gate
assignee: ''
agent: "claude"
shell_pid: "1533562"
history:
- at: '2026-07-04T18:48:18Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/mission_finalize.py
create_intent:
- tests/tasks/test_finalize_tasks_occurrence_gate.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/agent/mission_finalize.py
- tests/tasks/test_finalize_tasks_occurrence_gate.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Finalize-tasks command occurrence-map gate

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

Then follow Pedro's discipline: TDD (red first), Python 3.12+ idiom, `mypy --strict`, no suppressions.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

Make a **bulk-edit** mission fail at `spec-kitty agent mission finalize-tasks` when its `occurrence_map.yaml` is **missing, schema-invalid, or inadmissible** — *before* any `implement WP##`. Reuse the existing enforcement; add no new validation logic.

Done when:
- `finalize-tasks` (both normal and `--validate-only`) on a bulk-edit mission with a bad map exits 1 and surfaces the gate's canonical error (JSON error field in `--json` mode; `render_gate_failure` panel otherwise).
- `finalize-tasks` on a bulk-edit mission with a **valid, admissible** map proceeds unchanged.
- `finalize-tasks` on a **non-bulk** mission proceeds unchanged (gate is a no-op).
- The `--validate-only` zero-mutation invariant still holds.
- `mypy --strict` and `ruff` pass with zero new issues/suppressions.

## Context & Constraints

- Charter: `.kittify/charter/charter.md` (ATDD-first, single canonical authority, DIR-006/030 quality gates).
- Plan: [../plan.md](../plan.md) IC-01. Research/evidence: [../research.md](../research.md) F3–F6.
- **Reuse, don't rewrite** (C-001): the enforcement function is `ensure_occurrence_classification_ready(feature_dir) -> GateResult` in `src/specify_cli/bulk_edit/gate.py:49-96`. It self-conditions: `load_meta` → if `change_mode != "bulk_edit"` returns `passed=True` with empty errors (`gate.py:54-60`); otherwise checks presence (`:63-72`), schema (`:74-81`), and **admissibility** (`:83-90`, `occurrence_map.py:377`, `MIN_ADMISSIBLE_CATEGORIES = 3`). Companion renderer: `render_gate_failure(result, console)` (`gate.py:99-107`).
- **Reference implementation shape** (mirror it): `src/specify_cli/cli/commands/implement.py:1239-1244`:
  ```python
  from specify_cli.bulk_edit.gate import ensure_occurrence_classification_ready, render_gate_failure
  gate_result = ensure_occurrence_classification_ready(feature_dir)
  if not gate_result.passed:
      render_gate_failure(gate_result, console)
      raise typer.Exit(1)
  ```
- **Do NOT** touch `bulk_edit/gate.py`, `occurrence_map.py`, `mission.yaml`, the `mission_v1` guard registry, or the implement/review backstop call sites (`implement.py:1241`, `agent/workflow.py:2371` — these stay as-is per FR-004).
- Target file: `src/specify_cli/cli/commands/agent/mission_finalize.py`. `finalize_tasks()` starts ~`:1520`; it runs a linear validation pipeline over `planning_dir` and has a `--validate-only` mode split (`if validate_only:` ~`:1673`). The existing `_validate_*` phase helpers live near `:546` (e.g. `_validate_requirement_mapping`).

## Branch Strategy

- **Strategy**: pr-bound (already-confirmed)
- **Planning base branch**: `feat/bind-occurrence-map-guard-finalize`
- **Merge target branch**: `feat/bind-occurrence-map-guard-finalize`

> Execution worktrees are allocated per computed lane from `lanes.json`. Do not edit these fields.

## Subtasks & Detailed Guidance

### Subtask T001 – Red: finalize-tasks occurrence-gate integration tests

- **Purpose**: Lock the behavior with failing tests before wiring the gate (ATDD).
- **Files**: create `tests/tasks/test_finalize_tasks_occurrence_gate.py`.
- **Steps**:
  1. Study existing finalize tests for the invocation pattern: `tests/tasks/test_finalize_tasks_json_output_unit.py` uses `CliRunner().invoke(app, ["finalize-tasks", "--json", ...])` with a `meta.json` fixture. Reuse its fixture scaffolding.
  2. Reuse the gate fixtures from `tests/specify_cli/bulk_edit/test_gate.py` (`_write_meta` / `_write_occurrence_map` helpers, `:21-29`) for `change_mode` + occurrence-map file shaping.
  3. **Observable contract — pin assertions to the GATE, not the whole command.** `finalize_tasks` runs other `typer.Exit(1)` validators after the gate (requirement mapping `mission_finalize.py:546`, dependency graph, ownership `:1607-1664`, plus the commit pipeline). A minimal bulk-edit fixture will *not* satisfy those, so **do not assert `exit_code == 0` for the pass cases** — that would false-red on unrelated downstream validators (and must not be "fixed" by weakening the fail-case assertions). Instead:
     - **Fail cases**: assert the gate's error string is **PRESENT** in output (`--json`: the `gate_errors` / error field carrying the occurrence-map message; human: the `render_gate_failure` panel text, e.g. "Bulk Edit Gate: BLOCKED" / "Occurrence map required for bulk_edit missions") **and** `exit_code == 1`.
     - **Pass cases**: assert the gate's error string is **ABSENT** from output (the gate did not fire). Do not require the whole command to reach exit 0 unless you also build the full fixture (spec FR table, per-WP `owned_files`) and mock the commit seam — asserting error-string-absent is the robust, sufficient contract for "the gate let it through".
  4. Cases (each drives the `finalize-tasks` command against a prepared feature dir):
     - `change_mode="bulk_edit"` + **no** `occurrence_map.yaml` → gate error PRESENT, exit 1. Assert in both `--json` (error field) and human (panel) modes.
     - `change_mode="bulk_edit"` + **schema-invalid** map → gate error PRESENT, exit 1.
     - `change_mode="bulk_edit"` + **valid schema but < 3 categories (inadmissible)** → gate error PRESENT, exit 1.
     - `change_mode="bulk_edit"` + **valid, admissible** map (>= 3 categories, no placeholders) → gate error ABSENT.
     - `change_mode="standard"` (or absent) → gate error ABSENT (gate no-op).
     - **`--validate-only` variant** of the missing-map case → gate error PRESENT, exit 1 (proves it blocks in validate-only mode).
- **Notes**: keep each case isolated with its own tmp feature dir. Fail-fast placement (T003) makes the gate the first failing phase, so the fail cases surface the gate error deterministically before any downstream validator runs.
- **Parallel?**: [P] (new file, no collision).

### Subtask T002 – Add the read-only `_validate_occurrence_map_ready` helper

- **Purpose**: Encapsulate the gate call as a finalize phase mirroring the other `_validate_*` helpers.
- **Files**: `src/specify_cli/cli/commands/agent/mission_finalize.py`.
- **Steps**: add near the other phase helpers (~`:546`):
  ```python
  def _validate_occurrence_map_ready(planning_dir: Path, *, json_output: bool) -> None:
      """Phase: bulk-edit occurrence-map gate (reuses the implement-time check)."""
      from specify_cli.bulk_edit.gate import (
          ensure_occurrence_classification_ready,
          render_gate_failure,
      )
      result = ensure_occurrence_classification_ready(planning_dir)
      if result.passed:
          return
      if json_output:
          _emit_json({
              "error": "Bulk edit occurrence-map gate blocked finalize-tasks.",
              "gate_errors": list(result.errors),
          })
      else:
          render_gate_failure(result, console)
      raise typer.Exit(1)
  ```
  Match the module's actual JSON-emit helper name/shape (grep for how other phases emit `--json` errors — use the same helper, e.g. `_emit_json` or the local equivalent). Keep it **read-only** (only `ensure_occurrence_classification_ready`, which reads; no writes).
- **Notes**: type-annotate fully (`planning_dir: Path`, `-> None`). No new imports at module top if a local import keeps the surface minimal — match the module's convention.

### Subtask T003 – Call the helper in `finalize_tasks` (fail-fast, before the validate-only split)

- **Purpose**: Fire the gate at the correct timing, in both modes.
- **Files**: `src/specify_cli/cli/commands/agent/mission_finalize.py`.
- **Steps**:
  1. Inside `finalize_tasks(...)`, after `planning_dir` is resolved (~`:1576-1600`) and **before** the `if validate_only:` split (~`:1673`), insert:
     ```python
     _validate_occurrence_map_ready(planning_dir, json_output=json_output)
     ```
  2. Place it **fail-fast** — early, before the expensive requirement-mapping/dependency-graph validators — so a missing map is rejected before heavy bootstrap work (but after `planning_dir`/meta are available). Confirm `json_output`/`console` variable names match the function's locals.
- **Notes**: `planning_dir` is the correct `feature_dir` for the gate (it holds `meta.json` + any `occurrence_map.yaml`).

### Subtask T004 – Green + preserve read-only invariant + quality gates

- **Purpose**: Prove the change is correct and non-regressive.
- **Steps**:
  1. Run the new tests: `PWHEADLESS=1 .venv/bin/python -m pytest tests/tasks/test_finalize_tasks_occurrence_gate.py -q`. All green.
  2. Run the read-only invariant regression: `.venv/bin/python -m pytest tests/specify_cli/cli/commands/test_finalize_tasks_validate_only_readonly.py -q`. Must still pass (the gate is read-only).
  3. Run the broader finalize suite: `.venv/bin/python -m pytest tests/tasks/ -q` to catch ordering regressions.
  4. `.venv/bin/python -m mypy --strict src/specify_cli/cli/commands/agent/mission_finalize.py` and `.venv/bin/ruff check src/specify_cli/cli/commands/agent/mission_finalize.py tests/tasks/test_finalize_tasks_occurrence_gate.py` — zero issues, no new suppressions.

## Test Strategy

Tests are REQUIRED (spec NFR-003, ATDD-first charter). All new tests live in `tests/tasks/test_finalize_tasks_occurrence_gate.py`. Gate-logic unit coverage already exists in `tests/specify_cli/bulk_edit/test_gate.py` — do not duplicate it; these are command-integration tests.

## Risks & Mitigations

- **Placement ordering**: other finalize phases raise `typer.Exit(1)` too; fail-fast placement (T003) makes the occurrence gate deterministic for tests. Mitigation: place before requirement/dependency validators.
- **`--validate-only` mutation**: the gate must not write. Mitigation: it only calls the read-only `ensure_occurrence_classification_ready`; T004 step 2 asserts the invariant.
- **JSON shape drift**: match the module's existing `--json` error emission helper rather than inventing a new shape.

## Review Guidance

- Confirm the gate reuses `ensure_occurrence_classification_ready` unchanged (no new validation).
- Confirm all six test cases exist and pass, including the inadmissible (`<3` categories) branch and the `--validate-only` block.
- **Confirm pass cases assert gate-error-ABSENT (not `exit_code == 0`) and fail cases assert gate-error-PRESENT + exit 1** — reject any test that couples the pass assertion to the whole command's exit code (false-red risk) or that weakened the fail-case assertions to compensate.
- Confirm the implement/review backstops (`implement.py:1241`, `agent/workflow.py:2371`) are untouched.
- Confirm `--validate-only` read-only invariant test still passes; `mypy --strict` + `ruff` clean.

## Activity Log

- 2026-07-04T18:48:18Z – system – Prompt created.
- 2026-07-04T19:15:43Z – claude – shell_pid=1410377 – Assigned agent via action command
- 2026-07-04T19:26:37Z – claude – shell_pid=1410377 – Ready for review
- 2026-07-04T19:32:27Z – claude – shell_pid=1533562 – Started review via action command
