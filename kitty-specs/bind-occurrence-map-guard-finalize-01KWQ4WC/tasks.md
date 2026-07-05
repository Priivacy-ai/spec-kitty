# Tasks: Bind Occurrence-Map Guard at Finalize (#2345)

**Mission**: `bind-occurrence-map-guard-finalize-01KWQ4WC`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md)

Two independent, parallelizable work packages, one per implementation concern. Both reuse the existing `ensure_occurrence_classification_ready` check (no new validation logic) and are conditioned on stored `change_mode == "bulk_edit"`. The implement-time and review-time backstops (`implement.py`, `agent/workflow.py`) are left unchanged.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Red: finalize-tasks occurrence-gate integration tests | WP01 | [P] |
| T002 | Add read-only `_validate_occurrence_map_ready` helper | WP01 | |
| T003 | Call helper in `finalize_tasks` before the `--validate-only` split (fail-fast) | WP01 | |
| T004 | Green + preserve `--validate-only` read-only invariant; mypy/ruff | WP01 | |
| T005 | Red: `next`-loop tasks_finalize guard tests (both dispatch paths + parity) | WP02 | [P] |
| T006 | Add shared `_occurrence_gate_failures` helper in `runtime_bridge.py` | WP02 | |
| T007 | Wire helper into `_check_cli_guards` tasks_finalize branch | WP02 | |
| T008 | Wire helper into `_check_composed_action_guard` tasks_finalize block | WP02 | |
| T009 | Green + no next-loop guard regressions; mypy/ruff; no new suppressions | WP02 | |

---

## WP01 — Finalize-tasks command occurrence-map gate (IC-01)

- **Goal**: A bulk-edit mission fails at `spec-kitty agent mission finalize-tasks` when its `occurrence_map.yaml` is missing, schema-invalid, or inadmissible — before any `implement WP##`. Non-bulk missions unaffected.
- **Priority**: P1 (this is the issue's literal acceptance test).
- **Independent test**: run `finalize-tasks` (and `--validate-only`) on a bulk-edit fixture with a bad map → exit 1 with the gate's error; on a valid admissible map → proceeds; on a non-bulk mission → proceeds unchanged.
- **Requirements**: FR-001, FR-002, FR-003, FR-004.
- **Prompt**: [tasks/WP01-finalize-command-occurrence-gate.md](./tasks/WP01-finalize-command-occurrence-gate.md) (~230 lines)

### Subtasks

- [ ] T001 Red: add `tests/tasks/test_finalize_tasks_occurrence_gate.py` covering bulk_edit × {missing, schema-invalid, inadmissible (<3 categories), valid-admissible}, non-bulk pass, and `--validate-only` blocks (WP01)
- [ ] T002 Add read-only `_validate_occurrence_map_ready(planning_dir, *, json_output)` helper in `mission_finalize.py`, mirroring `implement.py:1239-1244` (WP01)
- [ ] T003 Call the helper inside `finalize_tasks` before the `if validate_only:` split, fail-fast placement (WP01)
- [ ] T004 Make tests green; confirm `test_finalize_tasks_validate_only_readonly.py` still passes; `mypy --strict` + `ruff` zero-issue on the changed file (WP01)

### Dependencies

None. Independent of WP02.

---

## WP02 — `next`-loop tasks_finalize occurrence-map guard (IC-02)

- **Goal**: The live `spec-kitty next` loop also blocks a bulk-edit mission at the tasks→implement boundary (not only at implement-time) when the occurrence map is bad — via ONE shared helper called from both guard enumerators so the new logic cannot drift.
- **Priority**: P2 (non-vacuousness; delivers the ticket's "plan→implement transition" surface on the live runtime).
- **Independent test**: drive `_check_cli_guards` and `_check_composed_action_guard` at the `tasks_finalize` boundary with a bulk-edit bad-map fixture → both block with the canonical error; valid map → both pass; non-bulk → both no-op; parity test asserts identical behavior and no duplicate error.
- **Requirements**: FR-001, FR-002, FR-003.
- **Prompt**: [tasks/WP02-next-loop-tasks-finalize-guard.md](./tasks/WP02-next-loop-tasks-finalize-guard.md) (~250 lines)

### Subtasks

- [ ] T005 Red: add `tests/next/test_occurrence_gate_next_loop.py` asserting both dispatch paths block at `tasks_finalize` for a bad bulk-edit map, pass for a valid map, no-op for non-bulk, plus a parity/no-double-report assertion (WP02)
- [ ] T006 Add shared `_occurrence_gate_failures(feature_dir) -> list[str]` helper in `runtime_bridge.py` (returns `ensure_occurrence_classification_ready(feature_dir).errors`) (WP02)
- [ ] T007 Call the shared helper from `_check_cli_guards` `elif step_id == "tasks_finalize"` (~:1091), folding errors into `failures` (WP02)
- [ ] T008 Call the shared helper from `_check_composed_action_guard` tasks_finalize terminal block of the `action == "tasks"` branch (~:1640), folding errors into `failures` (WP02)
- [ ] T009 Make tests green; no regression in existing `next`-loop guard tests; `mypy --strict` + `ruff`; confirm no new `# noqa`/suppression and no complexity-ceiling breach (WP02)

### Dependencies

None. Independent of WP01 (both reuse `bulk_edit.gate`, which is unchanged).

---

## MVP

**WP01** is the MVP — it satisfies the issue's literal acceptance criteria. WP02 completes non-vacuous coverage of the autonomous execution path.
