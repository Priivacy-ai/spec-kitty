---
work_package_id: WP01
title: Internalize the Runtime Surface
dependencies: []
requirement_refs:
- FR-001
- NFR-001
- NFR-002
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
- T009
history:
- at: '2026-04-25T10:31:00+00:00'
  actor: planner
  event: created
authoritative_surface: src/specify_cli/next/_internal_runtime/
execution_mode: code_change
owned_files:
- src/specify_cli/next/_internal_runtime/**
- tests/fixtures/runtime_parity/**
- tests/next/test_internal_runtime_parity.py
tags: []
---

# WP01 — Internalize the Runtime Surface

## Objective

Build CLI-owned modules that replicate the public surface of `spec_kitty_runtime`
0.4.3 used by the CLI, with byte-equal behavior parity proven against golden
snapshots captured from the currently-installed runtime package. This is the
foundation of the cutover — WP02 and every downstream WP depends on it.

## Context

The mission overall is documented in `kitty-specs/shared-package-boundary-cutover-01KQ22DS/`.
The package boundary doctrine is in
`kitty-specs/shared-package-boundary-cutover-01KQ22DS/spec.md` and `plan.md`. The
exact public surface this WP must implement is in
[`../contracts/internal_runtime_surface.md`](../contracts/internal_runtime_surface.md).

After PR #779 was rejected for preserving the hybrid model, this mission performs
the actual cutover. WP01 ships the new runtime modules; WP02 cuts every CLI
production importer over to them; WP03 architecturally locks the boundary.

**Key invariants this WP must enforce:**

- The internalized runtime MUST NOT import `spec_kitty_runtime` at any layer
  (top-level, lazy, conditional). Independence is the entire point.
- The internalized runtime MUST NOT depend on `rich.*` or `typer.*` directly —
  presentation belongs in the CLI layer (consistent with
  `tests/architectural/test_layer_rules.py` and ADR 2026-03-27-1).
- The internalized runtime's public symbols MUST match the surface in
  `contracts/internal_runtime_surface.md` exactly. External callers in
  `runtime_bridge.py` and `next_cmd.py` already encode that surface in their
  imports.
- Byte-equal parity with `spec_kitty_runtime` 0.4.3 against the reference fixture
  mission, verified by golden snapshot tests (modulo documented timestamp / path
  normalization).

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktree: allocated per lane from `lanes.json` after `finalize-tasks`
  runs. WP01 sits on lane A (runtime track).

## Implementation

### Subtask T001 — Capture parity baselines from `spec_kitty_runtime` 0.4.3

**Purpose**: Lock in the behavior contract. Whatever `spec_kitty_runtime` 0.4.3
returns today is what the internalized runtime must return. Without these
snapshots, "byte-equal parity" has no reference.

**Steps**:

1. Pick a reference fixture mission: the smallest possible mission scaffold that
   exercises (a) `start_mission_run`, (b) one `next_step` call returning a
   `discover` decision, (c) one `next_step` call after answering it. Place it at
   `tests/fixtures/runtime_parity/reference_mission/`. (Mirrors the structure
   used by `runtime-mission-execution-extraction-01KPDYGW`.)

2. Run `spec-kitty-runtime` 0.4.3 against the fixture inside a script captured
   at `tests/fixtures/runtime_parity/_capture_baselines.py`. The script:
   - Calls `start_mission_run(...)` and writes the JSON-serialized result to
     `snapshot_start_mission_run.json`.
   - Calls `next_step(...)` once and writes `snapshot_next_step_1.json`.
   - Calls `provide_decision_answer(...)` then `next_step(...)` and writes
     `snapshot_next_step_2.json` and `snapshot_provide_decision_answer.json`.
   - All writes use `json.dumps(..., sort_keys=True, indent=2)`.
   - Timestamps and absolute paths are normalized via the same regex
     normalization `runtime-mission-execution-extraction-01KPDYGW` uses (capture
     it from that mission's quickstart).

3. Commit the snapshots under `tests/fixtures/runtime_parity/`. They are the
   golden baselines against which the internalized runtime is judged.

**Files**:
- `tests/fixtures/runtime_parity/reference_mission/` (new)
- `tests/fixtures/runtime_parity/_capture_baselines.py` (new)
- `tests/fixtures/runtime_parity/snapshot_*.json` (new)

**Validation**:
- The capture script is deterministic — running it twice produces zero diff.
- Snapshots round-trip through `json.loads` cleanly.

### Subtask T002 — Create `_internal_runtime/` package skeleton

**Purpose**: Lay down the empty module shells so subtasks T003..T008 can fill
each one independently.

**Steps**:

1. Create `src/specify_cli/next/_internal_runtime/__init__.py` with a docstring
   explaining the underscore prefix (CLI-internal; not part of the public CLI
   import surface). Leave `__all__` empty for now; T009 fills it.

2. Create empty stub files (with module docstrings) for:
   - `src/specify_cli/next/_internal_runtime/models.py`
   - `src/specify_cli/next/_internal_runtime/emitter.py`
   - `src/specify_cli/next/_internal_runtime/lifecycle.py`
   - `src/specify_cli/next/_internal_runtime/engine.py`
   - `src/specify_cli/next/_internal_runtime/planner.py`
   - `src/specify_cli/next/_internal_runtime/schema.py`

**Files**: 7 new files under `src/specify_cli/next/_internal_runtime/`.

**Validation**: `python -c "import specify_cli.next._internal_runtime"` succeeds.

### Subtask T003 — Internalize models [P]

**Purpose**: Provide CLI-owned `DiscoveryContext`, `MissionPolicySnapshot`,
`MissionRunRef`, and `NextDecision` dataclasses.

**Steps**:

1. Read the upstream sources for these dataclasses inside the installed
   `spec_kitty_runtime` 0.4.3 package (look at
   `python -c "import spec_kitty_runtime; print(spec_kitty_runtime.__file__)"`).

2. Reproduce the dataclasses verbatim into
   `src/specify_cli/next/_internal_runtime/models.py`. Preserve:
   - Field names and types.
   - Default values.
   - `__slots__` if present.
   - `frozen=True` if present.

3. The reproduction is **derived from**, not **copy-paste with attribution**, but
   structural fidelity matters more than originality of expression. Comment at
   the top of the file: "Internalized from spec-kitty-runtime 0.4.3 as part of
   `shared-package-boundary-cutover-01KQ22DS` (mission). See
   `runtime-standalone-package-retirement-01KQ20Z8` for the upstream public-API
   inventory."

**Files**: `src/specify_cli/next/_internal_runtime/models.py`.

**Validation**:
- `mypy --strict` passes.
- A pickle round-trip yields equal dataclass instances (proves field shape
  matches the upstream).

### Subtask T004 — Internalize emitter [P]

**Purpose**: Provide CLI-owned `NullEmitter` and the runtime emitter Protocol.

**Steps**:

1. Reproduce `NullEmitter` (a no-op event emitter with the same method signatures
   the upstream defines) into
   `src/specify_cli/next/_internal_runtime/emitter.py`.
2. Reproduce the emitter `Protocol` (typed interface) so callers can implement
   custom emitters against `_internal_runtime` without depending on
   `spec_kitty_runtime`.
3. Same provenance comment as T003.

**Files**: `src/specify_cli/next/_internal_runtime/emitter.py`.

**Validation**: `mypy --strict` passes; `NullEmitter()` is constructible without
arguments.

### Subtask T005 — Internalize schema [P]

**Purpose**: Provide CLI-owned `ActorIdentity`, `load_mission_template_file`,
and `MissionRuntimeError`.

**Steps**:

1. Reproduce the three symbols into
   `src/specify_cli/next/_internal_runtime/schema.py`.
2. `load_mission_template_file` reads YAML from a `Path`; preserve the upstream
   error-handling exactly (which exceptions wrap which causes).
3. `MissionRuntimeError` MUST be a subclass of `Exception` and preserve the same
   `__init__` signature the upstream uses.
4. Same provenance comment as T003.

**Files**: `src/specify_cli/next/_internal_runtime/schema.py`.

**Validation**: `mypy --strict` passes; constructing `ActorIdentity` with the
parameters callers in `runtime_bridge.py` use succeeds.

### Subtask T006 — Internalize engine

**Purpose**: Provide CLI-owned `_read_snapshot` and the snapshot-persistence
sub-module that `runtime_bridge.py` imports as `engine`.

**Steps**:

1. Reproduce the engine module into
   `src/specify_cli/next/_internal_runtime/engine.py`. Preserve:
   - `_read_snapshot(...)` callable (underscore prefix preserved — every caller
     uses it by that name).
   - Any module-level state (LRU caches, etc.).

2. Internal helpers may be renamed; the only stable surface is `_read_snapshot`
   and the module reference itself (callers import the module via
   `from specify_cli.next._internal_runtime import engine`).

3. Same provenance comment as T003.

**Files**: `src/specify_cli/next/_internal_runtime/engine.py`.

**Validation**: `mypy --strict` passes; `_read_snapshot` against the reference
fixture's run-state directory returns a dict that round-trips cleanly through
`json.dumps`.

### Subtask T007 — Internalize planner

**Purpose**: Provide CLI-owned `plan_next` (the DAG planner).

**Steps**:

1. Reproduce the planner module into
   `src/specify_cli/next/_internal_runtime/planner.py`. The DAG planner is the
   most complex internal module; preserve its sub-functions verbatim.
2. Same provenance comment as T003.

**Files**: `src/specify_cli/next/_internal_runtime/planner.py`.

**Validation**: `mypy --strict` passes; given the reference fixture's mission
state, `plan_next(...)` returns a `NextDecision` with the same `kind` and
`payload` as the upstream baseline.

### Subtask T008 — Internalize lifecycle

**Purpose**: Provide CLI-owned `next_step`, `start_mission_run`, and
`provide_decision_answer` (the lifecycle entry points).

**Steps**:

1. Reproduce these three callables into
   `src/specify_cli/next/_internal_runtime/lifecycle.py`. They orchestrate
   `engine`, `planner`, `schema`, and emit events through whatever emitter the
   caller passes.
2. Imports in this module reference `_internal_runtime`'s own sub-modules, never
   `spec_kitty_runtime`.
3. Same provenance comment as T003.

**Files**: `src/specify_cli/next/_internal_runtime/lifecycle.py`.

**Validation**: `mypy --strict` passes.

### Subtask T009 — Wire up `__init__.py` and run parity tests

**Purpose**: Expose the public surface listed in
`contracts/internal_runtime_surface.md` and prove byte-equal parity against the
golden baselines from T001.

**Steps**:

1. Update `src/specify_cli/next/_internal_runtime/__init__.py`:
   ```python
   from specify_cli.next._internal_runtime.models import (
       DiscoveryContext,
       MissionPolicySnapshot,
       MissionRunRef,
       NextDecision,
   )
   from specify_cli.next._internal_runtime.emitter import NullEmitter
   from specify_cli.next._internal_runtime.lifecycle import (
       next_step,
       provide_decision_answer,
       start_mission_run,
   )

   __all__ = [
       "DiscoveryContext",
       "MissionPolicySnapshot",
       "MissionRunRef",
       "NextDecision",
       "NullEmitter",
       "next_step",
       "provide_decision_answer",
       "start_mission_run",
   ]
   ```

2. Create `tests/next/test_internal_runtime_parity.py`. The test:
   - Loads each `tests/fixtures/runtime_parity/snapshot_*.json` baseline.
   - Runs the same call against the internalized runtime.
   - Applies the same timestamp / path normalization the capture script used.
   - Asserts byte-equal JSON.

3. Run the parity test. If any snapshot diffs, iterate on the relevant
   sub-module until parity passes.

**Files**:
- `src/specify_cli/next/_internal_runtime/__init__.py` (rewrite)
- `tests/next/test_internal_runtime_parity.py` (new)

**Validation**:
- `pytest tests/next/test_internal_runtime_parity.py` passes against all
  captured snapshots.
- `python -c "from specify_cli.next._internal_runtime import next_step, NullEmitter; print('OK')"` succeeds.

## Definition of Done

- [ ] All 9 subtasks complete with checkboxes ticked above (`mark-status` updates the per-WP checkboxes here as the WP advances).
- [ ] `src/specify_cli/next/_internal_runtime/` exists with all 7 sub-modules populated.
- [ ] No file under `_internal_runtime/` imports `spec_kitty_runtime` (verified by grep).
- [ ] Parity test suite is green against the golden baselines.
- [ ] `mypy --strict` is green for all new modules.
- [ ] Test coverage on the new modules ≥ 90% (NFR-001).
- [ ] No production caller has changed yet — `runtime_bridge.py` and
  `next_cmd.py` still import `spec_kitty_runtime`. That cutover is WP02's job.

## Risks

- **Surface is larger than the upstream runtime mission's public-API inventory
  suggests.** Mitigation: T009's parity test catches every behavioral delta. If
  a delta requires a symbol not yet inventoried, file a delta against the
  upstream `runtime-standalone-package-retirement-01KQ20Z8` mission and expand
  this WP's surface in-place (the WP isn't done until parity passes).
- **Reproducing closed dataclasses verbatim risks copyright / attribution
  concerns.** Mitigation: the upstream package is MIT-licensed and Spec Kitty
  Contributors authored both; the provenance comment per subtask explicitly
  attributes the source.
- **Internal helpers in engine / planner have subtle shared state across
  modules.** Mitigation: T009's parity test runs *full lifecycle sequences* in
  T001's fixture, which exercises cross-module state.

## Reviewer guidance

- Verify zero `from spec_kitty_runtime` / `import spec_kitty_runtime` strings
  inside `src/specify_cli/next/_internal_runtime/`.
- Verify the public surface in `__init__.py` matches
  `contracts/internal_runtime_surface.md` exactly.
- Verify parity tests run against the committed golden baselines (not
  regenerated each run).
- Verify the provenance comment exists on every internalized module.
- Verify `mypy --strict` is green.
- Verify NFR-001 coverage gate (≥90%) on the new modules.

## Implementation command

```bash
spec-kitty agent action implement WP01 --agent <name> --mission shared-package-boundary-cutover-01KQ22DS
```
