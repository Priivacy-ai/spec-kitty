---
work_package_id: WP05
title: spec-kitty next Guard Wiring + Per-Guard Non-Vacuity Teeth Tests
dependencies:
- WP01
requirement_refs: []
subtasks:
- T020
- T021
- T022
- T023
- T024
- T025
- T026
- T027
- T028
phase: Phase 2 - Chokepoint (sequential, alone)
history:
- at: '2026-08-14T02:50:21Z'
  actor: system
  action: Prompt authored during tasks-authoring pass (not run via /spec-kitty.tasks)
agent_profile: ''
authoritative_surface: src/runtime/next/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/runtime/next/runtime_bridge_cores.py
- src/runtime/next/runtime_bridge.py
- src/runtime/next/runtime_bridge_io.py
- tests/runtime/test_bridge_cores.py
- tests/next/test_runtime_bridge_unit.py
- tests/specify_cli/next/test_runtime_bridge_composition.py
role: ''
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP05 – `spec-kitty next` Guard Wiring + Per-Guard Non-Vacuity Teeth Tests

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load`, or select via `spec-kitty agent profile list` for an
`implement`-typed WP on `src/runtime/next/` — this is the mission's central,
highest-risk surface; prefer the strongest available model per the charter's
model-task-routing discipline.

---

## ⚠️ THIS WP IS A DECLARED CHOKEPOINT — READ BEFORE STARTING

This WP touches the runtime-state schema (`runtime_bridge_cores.py`'s `status_facts` /
fact-object shape). Per this mission's tasks.md ("Parallelism & Chokepoints" section),
**it runs alone — no other WP is scheduled concurrently with it**, even though its
file list does not literally overlap WP06/WP07. Do not start this WP until WP01
(baseline), WP03 (the predicate this WP calls), and — for the campsite-clean
sequencing to make sense downstream — WP02 have all landed.

---

## Objectives & Success Criteria

Implement IC-02 + IC-05 (plan.md) — this mission's central, named engineering risk:
repeating the `3823f2b00`-shaped dead path (a signal added but never actually reachable
because `_tasks_dir_ready` short-circuits first). Thread the new bare-prose signal
through a sibling fact object into all four guard functions FR-010 names, read
**before** each guard's `_tasks_dir_ready` short-circuit, plus one synthetic-reversion
("teeth") test per guard.

Success: Story 3's Independent Test — a regression test exercises `spec-kitty next`'s
tasks-boundary decision directly (not only the pure `evaluate_guards` core) in both
configurations (zero WP files; ≥1 WP file, none referencing the bare-prose ids) and the
decision does not advance in either case, naming FR-001/FR-002 specifically. Each of
the four teeth tests, run individually, fails when only that guard's wiring is
reverted.

## Context & Constraints

- Read plan.md's "Story 3 / FR-002 / FR-003" section and "C-007 — fact-port shape" in
  full — both are already-resolved, traced decisions this WP implements literally, not
  re-derives.
- **FR-003's audit finding (already traced by plan.md, not this WP's job to redo)**:
  the composed `"tasks"` vocabulary is production-live for the built-in `software-dev`
  mission type at the tasks-finalize boundary — `_evaluate_composed_tasks_terminal_guard`
  is the guard `spec-kitty next` actually invokes in production for this mission's own
  mission type. The CLI-native `_evaluate_tasks_finalize_guard` is non-primary, not
  proven dead (a custom mission type without a matching `action_sequence` entry falls
  back to it) — **wire all four guards**, per plan.md's explicit scope decision:
  `_evaluate_tasks_packages_guard`, `_evaluate_tasks_finalize_guard`,
  `_evaluate_composed_tasks_packages_guard`, `_evaluate_composed_tasks_terminal_guard`
  (all in `src/runtime/next/runtime_bridge_cores.py`).
- **C-007 binding**: the new fact is a **sibling** `BareProseRequirementFacts` dataclass,
  NOT an extension of `RequirementMappingFacts` (which is WP-shaped and early-returns on
  absent `tasks_dir` — exactly the coupling this mission must avoid). It must arrive in
  `runtime_bridge_cores.py` as plain data only — never a new cross-package import (WP04's
  test enforces this).
- **PLAN-ARCH-001 binding**: read the new `status_facts` key via
  `.get("bare_prose_requirement_failures", ())`, **never a bare subscript** —
  `tests/runtime/test_bridge_cores.py`'s `_snapshot()` helper does not yet populate this
  key, and a bare subscript would `KeyError` every existing caller instantly.
  `requirement_mapping_failures` itself stays a bare subscript, unchanged.
- **FR-002's ordering constraint (the load-bearing fix)**: read the new fact
  **unconditionally, before** each guard's own `_tasks_dir_ready` check. This is the
  exact difference from the reverted `_zero_declared_requirement_block`.
- **C-009, already resolved**: no `mission_step_contracts/` schema change and no
  orchestrator-api documentation update are needed — the new failure flows through the
  existing `Decision(kind=blocked, ...)` guard-failure-list shape. Do not add new
  schema fields.
- **Fail-loud contract (Story 5 / FR-007 / FR-008), textually separate from the
  advisory**: do NOT route the new gather step through
  `_log_requirement_extraction_warnings_safely` (`runtime_bridge.py` ~line 835) — that
  wrapper's "never crash into a gate" contract is the *opposite* of this new detector's
  "never silently report clean" contract.

## Branch Strategy

- **Strategy**: Planning artifacts were generated on `pr/bare-prose-requirements-uncounted`;
  completed changes must merge back into `pr/bare-prose-requirements-uncounted`
  (base `op/3394-requirement-citation-scope` @ `ab15225ea`).
- **Planning base branch**: `pr/bare-prose-requirements-uncounted` (mission topology).
- **Merge target branch**: `pr/bare-prose-requirements-uncounted`.

> **ATDD RED verification uses `ab15225ea`, not the fields above or `main`.** Same
> caveat as WP03: the mechanism this WP wires into does not exist on `main`. Verify RED
> against `ab15225ea` / `origin/op/3394-requirement-citation-scope` specifically.

## Subtasks & Detailed Guidance

### Subtask T020 – ATDD RED-first commit

- **Purpose**: Charter C-011 binding.
- **Steps**: Write failing tests for each of the four guards, plus the zero-WP-files /
  ≥1-WP-file-no-match integration cases (Story 3), in
  `tests/runtime/test_bridge_cores.py` (pure-core guards) and
  `tests/next/test_runtime_bridge_unit.py` (CLI-native integration). Verify RED against
  **`ab15225ea`**.
- **Notes**: This commit lands BEFORE any implementation commit (T021-T025).

### Subtask T021 – Add the sibling fact object

- **Purpose**: C-007-compliant fact port.
- **Steps**: Add to `runtime_bridge_cores.py`, beside `RequirementMappingFacts`
  (line 241):
```python
@dataclass(frozen=True)
class BareProseRequirementFacts:
    flagged: Mapping[str, tuple[str, ...]]
    classification_error: str | None
```
- **Files**: `src/runtime/next/runtime_bridge_cores.py`.

### Subtask T022 – Add the pure evaluator

- **Purpose**: Fact-port/pure-core split, mirroring `_evaluate_requirement_mapping`.
- **Steps**: Add `_evaluate_bare_prose_requirements(facts: BareProseRequirementFacts) -> list[str]`
  beside `_evaluate_requirement_mapping` (line 253).

### Subtask T023 – Add the residual gather step + fail-loud wrapper

- **Purpose**: The independent-of-`tasks_dir` gather step FR-002 requires, with its own
  "never silently clean" contract.
- **Steps**: In `runtime_bridge.py`, add e.g.
  `_check_bare_prose_requirements_ready(feature_dir) -> list[str]`, reading `spec.md`
  only (no `tasks_dir` dependency). Call `find_bare_prose_requirement_ids`. Wrap in a
  single `try/except`: on exception, return an explicit non-empty failure string
  mirroring `_check_requirement_mapping_ready`'s own `except Exception as exc: return
  [f"..."]` pattern (line 919) — never re-raised as a bare traceback, never
  downgraded to a log line, never routed through
  `_log_requirement_extraction_warnings_safely`.

### Subtask T024 – Add the new status_facts key

- **Purpose**: Plumb the fact through the gather layer.
- **Steps**: In `runtime_bridge_io.py::gather_artifact_presence`, add
  `"bare_prose_requirement_failures": tuple(...)`, populated the same way
  `"requirement_mapping_failures"` already is (line 845).

### Subtask T025 – Wire all four guards

- **Purpose**: The core fix — read before the short-circuit, in every guard.
- **Steps**: In each of `_evaluate_tasks_packages_guard`, `_evaluate_tasks_finalize_guard`,
  `_evaluate_composed_tasks_packages_guard`, `_evaluate_composed_tasks_terminal_guard`,
  add, as the FIRST statement:
  `failures = list(snapshot.status_facts.get("bare_prose_requirement_failures", ()))`
  then extend `failures` with the guard's existing logic (including its
  `_tasks_dir_ready`-gated branch), and `return failures` (or equivalent) instead of the
  bare early-return. See plan.md's code sketch under "FR-002's ordering constraint" for
  the literal before/after shape.

### Subtask T026 – Per-guard teeth tests

- **Purpose**: FR-010/NFR-005 — prove EVERY wired guard is individually load-bearing.
- **Steps**: Add one synthetic-reversion test per guard (up to four total): for each
  guard, construct a test that reverts ONLY that guard's new `.get(...)` read (e.g. by
  testing a snapshot where the fact would fire, asserting the guard's result changes
  when the wiring is present vs. a stubbed-absent wiring) and assert that guard's test
  fails when its own wiring alone is removed. A single existence-proof test anywhere in
  the suite does NOT satisfy this for the other guards — the spec text is explicit and
  literal on this point.

### Subtask T027 – Update the shared test fixture

- **Purpose**: Fixture-accuracy hygiene (not a blocking dependency of T025's `.get()`
  read).
- **Steps**: In `tests/runtime/test_bridge_cores.py`, update `_snapshot()`'s
  `base_status_facts` dict to also set `"bare_prose_requirement_failures"` by default.

### Subtask T028 – Confirm SC-002 / Story 2 AC2 regression

- **Purpose**: The full pre-existing #3394/#3395 suite must stay green, unmodified.
- **Steps**: Run `tests/next/test_runtime_bridge_unit.py` and
  `tests/runtime/test_bridge_cores.py` in full; confirm exact-equality assertions like
  `test_cli_native_tasks_packages_extends_requirement_mapping_failures` and
  `test_cli_native_tasks_finalize_missing_dependency_uses_full_stem_breaks_on_first`
  still pass with their pinned assertions unmodified.

## Test Strategy

- `tests/runtime/test_bridge_cores.py`, `tests/next/test_runtime_bridge_unit.py`,
  `tests/specify_cli/next/test_runtime_bridge_composition.py`,
  `tests/specify_cli/next/test_runtime_bridge_dispatch.py`.
- Run: `PWHEADLESS=1 pytest tests/next/ tests/specify_cli/next/ tests/runtime/ -n 8 --dist loadfile -q`.

## Risks & Mitigations

- Repeating the `3823f2b00`-shaped dead path — mitigated by T025's explicit
  before-the-short-circuit ordering and T026's per-guard teeth tests.
- `KeyError` regressions in every pre-existing `evaluate_guards` fixture — mitigated by
  T025's `.get(..., ())` read plus T027's fixture update.

## Review Guidance

- Confirm the three guards that call `_tasks_dir_ready`
  (`_evaluate_tasks_packages_guard`, `_evaluate_composed_tasks_packages_guard`,
  `_evaluate_composed_tasks_terminal_guard`) read the new fact BEFORE that check, not
  after. `_evaluate_tasks_finalize_guard` has no `_tasks_dir_ready` call today (it uses
  its own inline `tasks_dir_is_dir`/`tasks_wp_files` checks with no early-return
  short-circuit) — for it, confirm instead that the new fact is read unconditionally, as
  the first statement, independent of its own tasks-dir-readiness branches.
- Confirm four independent teeth tests exist (or fewer, with an explicit stated reason
  if FR-003's live-vocabulary finding changes which guards are actually wired — but the
  default per plan.md is all four).
- Confirm WP04's import-boundary test still passes after this WP's edits.
- Confirm no `mission_step_contracts/` schema file changed (C-009).

## Activity Log

- 2026-08-14T02:50:21Z – system – Prompt created.
