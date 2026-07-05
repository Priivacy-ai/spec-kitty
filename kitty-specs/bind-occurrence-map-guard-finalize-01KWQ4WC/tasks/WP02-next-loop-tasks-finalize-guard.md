---
work_package_id: WP02
title: next-loop tasks_finalize occurrence-map guard
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
tracker_refs: []
planning_base_branch: feat/bind-occurrence-map-guard-finalize
merge_target_branch: feat/bind-occurrence-map-guard-finalize
branch_strategy: Planning artifacts for this mission were generated on feat/bind-occurrence-map-guard-finalize. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/bind-occurrence-map-guard-finalize unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
phase: Phase 1 - Live next-loop guard
assignee: ''
agent: "claude"
shell_pid: "1595904"
history:
- at: '2026-07-04T18:48:18Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/runtime/next/runtime_bridge.py
create_intent:
- tests/next/test_occurrence_gate_next_loop.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/runtime/next/runtime_bridge.py
- tests/next/test_occurrence_gate_next_loop.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – next-loop tasks_finalize occurrence-map guard

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

Make the **live `spec-kitty next` loop** also block a **bulk-edit** mission at the **tasks→implement boundary** when its `occurrence_map.yaml` is missing/schema-invalid/inadmissible — so the "fail before implement" gate is non-vacuous on the framework's dominant execution path (not only when the `finalize-tasks` command is run explicitly, which WP01 covers). Reuse the same enforcement; add no new validation logic.

Done when:
- Both live pre-implement guard enumerators — `_check_cli_guards` (tasks_finalize branch) and `_check_composed_action_guard` (tasks_finalize block of the `action == "tasks"` branch) — block a bulk-edit mission with a bad occurrence map, folding the gate's errors into their existing `failures` list.
- A **valid, admissible** map lets both paths pass; a **non-bulk** mission is a no-op on both.
- The new gate logic lives in **one shared helper** both enumerators call (no drift), with a **parity test** proving identical behavior and no duplicate error.
- No regression in existing `next`-loop guard tests; `mypy --strict` + `ruff` clean; **no new `# noqa`/suppression** and no complexity-ceiling breach.

## Context & Constraints

- Charter: `.kittify/charter/charter.md`. Plan: [../plan.md](../plan.md) IC-01/IC-02. Evidence: [../research.md](../research.md) F1, F2, F7.
- **Why this WP exists**: the `mission.yaml` transition `conditions` surface is DEAD (`evaluate_guards`/`mission_v1` has no live consumer — research F1/F2); the live `next` loop hand-rolls guards in `runtime_bridge`. A `next`-driven mission that never runs the `finalize-tasks` command would otherwise only hit the bad map at implement-time.
- **Reuse, don't rewrite** (C-001): call `ensure_occurrence_classification_ready(feature_dir) -> GateResult` from `src/specify_cli/bulk_edit/gate.py:49-96`. It self-conditions on `change_mode == "bulk_edit"` (returns `passed=True`, empty `errors` for non-bulk), so the helper is safe to call unconditionally on the tasks_finalize path.
- **Exact binding points** (do NOT bind at the branch head or the `tasks_outline`/`tasks_packages` substeps):
  - `_check_cli_guards(step_id, feature_dir)` — `runtime_bridge.py:1065-1112`; the `elif step_id == "tasks_finalize":` branch (~`:1091`).
  - `_check_composed_action_guard(action, feature_dir, ...)` — `runtime_bridge.py:1508-1637`; the tasks_finalize / composition-terminal block of the `action == "tasks"` branch (~`:1640`, i.e. the `else` after `tasks_outline`/`tasks_packages`).
  - Both build a `failures` list and block the advance when non-empty — fold the gate errors into that list.
- **Do NOT** touch `bulk_edit/gate.py`, the `finalize-tasks` command (WP01 owns it), `mission.yaml`, or the implement/review backstops.

## Branch Strategy

- **Strategy**: pr-bound (already-confirmed)
- **Planning base branch**: `feat/bind-occurrence-map-guard-finalize`
- **Merge target branch**: `feat/bind-occurrence-map-guard-finalize`

> Execution worktrees are allocated per computed lane from `lanes.json`. Do not edit these fields.

## Subtasks & Detailed Guidance

### Subtask T005 – Red: next-loop tasks_finalize guard tests (both paths + parity)

- **Purpose**: Lock the behavior with failing tests before wiring (ATDD), including the drift/parity guard the post-plan squad required.
- **Files**: create `tests/next/test_occurrence_gate_next_loop.py`.
- **Steps**:
  1. Study existing `runtime_bridge` guard tests under `tests/next/` for how `_check_cli_guards` / `_check_composed_action_guard` are invoked and how `feature_dir` fixtures are built.
  2. Reuse the meta/occurrence-map fixture shaping from `tests/specify_cli/bulk_edit/test_gate.py`.
  3. Cases for **each** of the two guard functions at the tasks_finalize boundary:
     - bulk_edit + bad map (missing / schema-invalid / inadmissible) → guard reports failure (blocks advance) with the canonical error text.
     - bulk_edit + valid admissible map → guard passes.
     - non-bulk mission → guard no-op (no occurrence-related failure).
  4. **Parity test**: assert `_check_cli_guards` and `_check_composed_action_guard` produce the same block/pass decision for the same fixture at tasks_finalize, and that a single advance does not surface the occurrence error twice.
  5. Regression guard: assert the `tasks_outline` / `tasks_packages` substeps do NOT run the occurrence gate (it must fire only at tasks_finalize).
- **Parallel?**: [P] (new file).

### Subtask T006 – Add the shared `_occurrence_gate_failures` helper

- **Purpose**: Single source of the new gate logic so the two mirror enumerators cannot diverge (post-plan medium finding).
- **Files**: `src/runtime/next/runtime_bridge.py`.
- **Steps**: add a module-level helper:
  ```python
  def _occurrence_gate_failures(feature_dir: Path) -> list[str]:
      """Bulk-edit occurrence-map gate errors (empty when not bulk_edit or map is valid)."""
      from specify_cli.bulk_edit.gate import ensure_occurrence_classification_ready
      return list(ensure_occurrence_classification_ready(feature_dir).errors)
  ```
  Self-conditioning means non-bulk/valid returns `[]`. Keep it a single branchless statement body so it adds no complexity to callers.

### Subtask T007 – Wire the helper into `_check_cli_guards` (tasks_finalize)

- **Purpose**: Block the legacy/DAG dispatch path.
- **Files**: `runtime_bridge.py`.
- **Steps**: inside the `elif step_id == "tasks_finalize":` branch (~`:1091`), after the existing per-step checks build their `failures`, add:
  ```python
  failures.extend(_occurrence_gate_failures(feature_dir))
  ```
  Match the branch's actual local variable name for the failure accumulator.

### Subtask T008 – Wire the helper into `_check_composed_action_guard` (tasks_finalize)

- **Purpose**: Block the composed-action dispatch path with identical logic.
- **Files**: `runtime_bridge.py`.
- **Steps**: inside the tasks_finalize/composition-terminal block of the `action == "tasks"` branch (~`:1640`, the `else` after `tasks_outline`/`tasks_packages`), add the same `failures.extend(_occurrence_gate_failures(feature_dir))` against that block's failure accumulator. Confirm the correct `feature_dir` variable is in scope.

### Subtask T009 – Green + no regressions + quality gates

- **Steps**:
  1. `.venv/bin/python -m pytest tests/next/test_occurrence_gate_next_loop.py -q` → green.
  2. `.venv/bin/python -m pytest tests/next/ -q` → no regression in existing guard/decision tests.
  3. `.venv/bin/python -m mypy --strict src/runtime/next/runtime_bridge.py` and `.venv/bin/ruff check src/runtime/next/runtime_bridge.py tests/next/test_occurrence_gate_next_loop.py` → zero issues.
  4. Confirm you added **no** new `# noqa`/`type: ignore` and did not push either target function over the complexity ceiling (the fold-in is a single `.extend(...)` call).

## Test Strategy

Tests REQUIRED. New tests in `tests/next/test_occurrence_gate_next_loop.py`, including the parity/no-double-report assertion and the tasks_outline/tasks_packages negative check.

## Risks & Mitigations

- **Drift between the two enumerators**: mitigated by the single shared helper (T006) — both call the same function.
- **Wrong binding boundary**: the gate must fire only at tasks_finalize, not tasks_outline/tasks_packages; T005 step 5 asserts this.
- **Double-report**: the two guards fire on different dispatch paths, not both for one advance; the parity test asserts a single advance surfaces the error once.
- **Complexity/suppression**: keep the fold-in a single `.extend()`; do not add `# noqa` (NFR-002).

## Review Guidance

- Confirm the new gate logic exists in exactly one helper, called from both enumerators (no duplicated logic).
- Confirm binding is at tasks_finalize only (parity + negative substep tests present and passing).
- Confirm reuse of `ensure_occurrence_classification_ready` unchanged; no new suppressions; `mypy --strict` + `ruff` clean; existing `tests/next/` green.

## Activity Log

- 2026-07-04T18:48:18Z – system – Prompt created.
- 2026-07-04T19:16:04Z – claude – shell_pid=1414399 – Assigned agent via action command
- 2026-07-04T19:26:38Z – claude – shell_pid=1414399 – Ready for review: shared _occurrence_gate_failures helper wired into both live next-loop tasks_finalize guards; 19 new tests + full tests/next/ (516) green; mypy --strict/ruff clean
- 2026-07-04T19:27:20Z – claude – shell_pid=1502392 – Started review via action command
- 2026-07-04T19:39:43Z – user – shell_pid=1502392 – Moved to planned
- 2026-07-04T19:40:37Z – claude – shell_pid=1561802 – Started implementation via action command
- 2026-07-04T19:45:37Z – claude – shell_pid=1561802 – Moved to for_review
- 2026-07-04T19:46:42Z – claude – shell_pid=1595904 – Started review via action command
