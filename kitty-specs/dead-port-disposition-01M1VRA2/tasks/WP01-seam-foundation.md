---
work_package_id: WP01
title: Seam foundation — factory, registry, NullEmitter.for_mission
dependencies: []
requirement_refs:
- C-005
- FR-002
- FR-003
- FR-004
- FR-009
- NFR-005
- NFR-006
- NFR-007
planning_base_branch: feat/dead-port-disposition
merge_target_branch: feat/dead-port-disposition
branch_strategy: Planning artifacts for this mission were generated on feat/dead-port-disposition. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/dead-port-disposition unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-dead-port-disposition-01M1VRA2
base_commit: 5f695cd4ef5632923a215589c25fdd1699a75522
created_at: '2026-09-06T18:25:57.515068+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - Foundation
history:
- at: '2026-09-06T16:48:26Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/runtime/next/_internal_runtime/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/runtime/next/_internal_runtime/events.py
- src/runtime/next/_internal_runtime/emitter.py
- tests/next/test_internal_runtime_coverage.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – Seam foundation — factory, registry, NullEmitter.for_mission

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent tasks status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`,````bash`

---

## Objectives & Success Criteria

This WP gives the canonical seam module everything the bridge currently gets from the concrete duplicate class, so that class becomes deletable (WP04) and the bridge can bind to a factory (WP03).

Done means:

- `NullEmitter.for_mission(*, feature_dir, mission_slug, mission_type)` exists and resolves `mission_id` with degrade-to-`None` (FR-003).
- `NullEmitter.seed_from_snapshot(snapshot)` exists and is a no-op (FR-004).
- `runtime_emitter_for_mission(...)`, `register_runtime_emitter_factory(...)`, `reset_runtime_emitter_factory()` exist and satisfy contract rules S1–S6 in `contracts/emitter-seam.md` (FR-002).
- `__all__` in both `events.py` and the `emitter.py` shim export the three new names; `test_emitter_module_re_exports` updated.
- The module docstring names the real zeitgeist seam and the E3 registration point (FR-009, first half).
- `pytest tests/next/test_internal_runtime_coverage.py -q` green; `ruff check src/runtime/next/_internal_runtime/` and `mypy src/runtime/next/_internal_runtime/events.py` clean; no function exceeds complexity 15 (NFR-007).
- Zero new `feature*` identifiers in your added lines (NFR-006). The keyword parameter `feature_dir` is pre-existing and stays.
- No file outside `owned_files` is modified.

## Context & Constraints

- Governing ADR: `docs/adr/3.x/2026-09-06-2-runtime-event-emitter-disposition.md` (Accepted). Read §Decision Outcome (a) and (b).
- Plan: `kitty-specs/dead-port-disposition-01M1VRA2/plan.md` §Design "Seam design (Concern A)".
- Contract you are implementing: `kitty-specs/dead-port-disposition-01M1VRA2/contracts/emitter-seam.md`.
- Research decisions that bind you: `research.md` R-2 (do **not** widen the Protocol), R-4 (factory idiom, call-time env read), R-5 (layer safety), R-7 (`for_mission`, no alias).
- The class you are absorbing: `src/runtime/next/event_emitter.py` (88 lines). Read it once; do not modify or delete it here (WP04 owns deletion).
- The registration idiom to mirror: `src/specify_cli/status/adapters.py:201-214` (`ensure_zeitgeist_moment_handlers` / `reset_handlers`) and its import-tail gate at `:355-365`.
- Env-gate helper: `is_truthy` — find its import in `status/adapters.py` and reuse the same helper.
- Charter: `.kittify/charter/charter.md` — Single canonical authority; Internal Runtime Boundary (`src/runtime/` may import `specify_cli.*` except `specify_cli.cli` and `specify_cli.next`).

## Branch Strategy

- **Strategy**: Planning artifacts were generated on feat/dead-port-disposition; completed changes must merge back into feat/dead-port-disposition.
- **Planning base branch**: feat/dead-port-disposition
- **Merge target branch**: feat/dead-port-disposition

> These fields are populated automatically by `spec-kitty agent mission tasks`. Execution worktrees are allocated per computed lane from `lanes.json`; run `spec-kitty agent action implement WP01 --agent <name>` and work inside the workspace it returns.

## Subtasks & Detailed Guidance

### Subtask T001 – `NullEmitter` mission fields + `for_mission` classmethod

- **Purpose**: Promote the one capability the bridge needs at construction (mission-identity resolution) onto the canonical null implementation, under the Canon-compliant name.
- **Steps**:
  1. In `src/runtime/next/_internal_runtime/events.py`, add `from pathlib import Path` and `from specify_cli.mission_metadata import resolve_mission_identity` (top-level import; `planner.py:46` already imports this module, so the layer ledger is unchanged).
  2. Extend `NullEmitter.__init__` **without changing its existing positional signature**:
     ```python
     def __init__(
         self,
         correlation_id: str = "",
         *,
         mission_slug: str = "",
         mission_type: str = "",
         mission_id: str | None = None,
     ) -> None:
         self.correlation_id = correlation_id
         self.mission_slug = mission_slug
         self.mission_type = mission_type
         self.mission_id = mission_id
     ```
     Every existing `NullEmitter()` and `NullEmitter("corr")` call in the tree must keep working.
  3. Add the classmethod:
     ```python
     @classmethod
     def for_mission(
         cls,
         *,
         feature_dir: Path,
         mission_slug: str,
         mission_type: str,
     ) -> "NullEmitter":
         """Build the null seam for one mission, resolving its ULID when possible."""
         try:
             mission_id: str | None = resolve_mission_identity(feature_dir).mission_id
         except Exception:  # noqa: BLE001 — identity is informational; the seam must never raise
             mission_id = None
         return cls(mission_slug=mission_slug, mission_type=mission_type, mission_id=mission_id)
     ```
     The broad except mirrors the class being absorbed (`event_emitter.py:50-53`) and is justified inline: emission is instrumentation, never control flow.
- **Files**: `src/runtime/next/_internal_runtime/events.py`
- **Parallel?**: No (T002, T003, T005 build on it).
- **Notes**: Do not add `for_feature`. Do not add `for_mission` to the Protocol (R-2).

### Subtask T002 – `NullEmitter.seed_from_snapshot`

- **Purpose**: The bridge (`runtime_bridge.py:1614`, `:2745`) and the engine adapter (`runtime_bridge_engine.py:344`) call `seed_from_snapshot` on the object the factory returns. The null emitter must accept it.
- **Steps**: Add to `NullEmitter`:
  ```python
  def seed_from_snapshot(self, snapshot: Any) -> None:
      """No-op: the null seam carries no phase state to seed."""
      del snapshot
  ```
  `_BufferingRuntimeEmitter` already has the same method (`runtime_bridge_retrospective.py:119`); keep the signatures identical.
- **Files**: `src/runtime/next/_internal_runtime/events.py`
- **Parallel?**: No.

### Subtask T003 – Factory, registry, env gate

- **Purpose**: Replace "the bridge imports a concrete class" with "the bridge calls a factory that a future producer can register into" (ADR (a)).
- **Steps**:
  1. Below `NullEmitter`, add:
     ```python
     RuntimeEmitterFactory = Callable[..., RuntimeEventEmitter]
     _registered_factory: RuntimeEmitterFactory | None = None


     def register_runtime_emitter_factory(factory: RuntimeEmitterFactory) -> None:
         """Register the producer factory a future E3 adapter installs at import tail."""
         global _registered_factory
         _registered_factory = factory


     def reset_runtime_emitter_factory() -> None:
         """Restore the default (null) seam; test-only utility, mirrors reset_handlers()."""
         global _registered_factory
         _registered_factory = None


     def runtime_emitter_for_mission(
         *,
         feature_dir: Path,
         mission_slug: str,
         mission_type: str,
     ) -> RuntimeEventEmitter:
         """Return the mission's runtime emitter seam.

         Under SPEC_KITTY_SYNC_MINIMAL_IMPORT the null seam is returned unconditionally
         (S2). Otherwise the registered factory wins (S3); with none registered the
         null seam is returned (S1). The env gate is read at call time so tests can
         toggle it without reloading this module.
         """
         if is_truthy(os.environ.get("SPEC_KITTY_SYNC_MINIMAL_IMPORT")):
             return NullEmitter.for_mission(feature_dir=feature_dir, mission_slug=mission_slug, mission_type=mission_type)
         factory = _registered_factory or NullEmitter.for_mission
         return factory(feature_dir=feature_dir, mission_slug=mission_slug, mission_type=mission_type)
     ```
  2. Imports: `os`, `Callable` (from `collections.abc`), and `is_truthy` (same helper `status/adapters.py` uses — grep its import line and copy it).
  3. `global` on a module-private is acceptable here because it mirrors the existing handler-registry idiom; do not introduce a class-based registry.
- **Files**: `src/runtime/next/_internal_runtime/events.py`
- **Parallel?**: No.
- **Notes**: Keep each function under complexity 15 (they are trivial). `runtime_emitter_for_mission` returns the Protocol type; mypy must accept `NullEmitter` as structurally conforming.

### Subtask T004 – `__all__` and the re-export shim

- **Purpose**: `tests/next/test_internal_runtime_coverage.py:171-174` asserts `emitter_mod.__all__ == {"NullEmitter", "RuntimeEventEmitter"}` exactly; it must be updated in lockstep.
- **Steps**:
  1. `events.py` `__all__`: append `"runtime_emitter_for_mission"`, `"register_runtime_emitter_factory"`, `"reset_runtime_emitter_factory"`.
  2. `src/runtime/next/_internal_runtime/emitter.py`: import and re-export the same three names; extend its `__all__`.
  3. `tests/next/test_internal_runtime_coverage.py::test_emitter_module_re_exports`: extend the set assertion and add identity assertions for the three names (`emitter_mod.runtime_emitter_for_mission is events_mod.runtime_emitter_for_mission`, etc.).
- **Files**: `src/runtime/next/_internal_runtime/events.py`, `src/runtime/next/_internal_runtime/emitter.py`, `tests/next/test_internal_runtime_coverage.py`
- **Parallel?**: Yes, once the names in T003 are fixed.

### Subtask T005 – Unit tests for S1–S6

- **Purpose**: Contract rules in `contracts/emitter-seam.md` must each have a direct test (charter: every new branch/helper needs tests in the same PR).
- **Steps**: Add to `tests/next/test_internal_runtime_coverage.py` (near the re-export tests; markers already file-level):
  1. `test_factory_returns_null_emitter_by_default` — call `reset_runtime_emitter_factory()`, then `runtime_emitter_for_mission(feature_dir=tmp_path, mission_slug="m", mission_type="software-dev")`; assert `isinstance(result, NullEmitter)`, `result.mission_slug == "m"`, `result.mission_id is None` (no `meta.json`). (S1, S5 degrade path)
  2. `test_factory_honors_registered_factory` — register `lambda **kw: sentinel`; assert the factory returns `sentinel` and receives exactly the three keyword args; `reset_runtime_emitter_factory()` in a `finally`. (S3)
  3. `test_factory_reset_restores_default` — register, reset, assert `NullEmitter`. (S4)
  4. `test_factory_minimal_import_gate_wins` — register a factory that raises `AssertionError("must not be called")`; `monkeypatch.setenv("SPEC_KITTY_SYNC_MINIMAL_IMPORT", "1")`; assert `NullEmitter` returned and the factory was not called. (S2)
  5. `test_for_mission_resolves_mission_id_from_meta` — write `tmp_path/"meta.json"` with `{"mission_id": "01KT3YBDABCDEFGHIJKLMNOP"}` (see `tests/specify_cli/events/test_decision_log_coord.py::_write_coord_meta` for the shape); assert `NullEmitter.for_mission(feature_dir=tmp_path, ...).mission_id == "01KT3YBDABCDEFGHIJKLMNOP"`. (S5 success path)
  6. `test_for_mission_degrades_on_corrupt_meta` — write invalid JSON; assert `mission_id is None` and no exception. (S5 degrade)
  7. `test_null_emitter_seed_and_emits_never_raise` — call `seed_from_snapshot(object())` and every `emit_*` with `object()`; no exception. (S6)
  8. `test_null_emitter_bare_constructor_unchanged` — `NullEmitter()` and `NullEmitter("c")` still work; new fields default to `""`/`""`/`None`.
- **Files**: `tests/next/test_internal_runtime_coverage.py`
- **Parallel?**: No (needs T001–T003).
- **Notes**: Use a fixture or `try/finally` so no test leaks a registered factory into another test.

### Subtask T006 – Seam docstring

- **Purpose**: FR-009. The concrete class's docstring (`event_emitter.py:1-10`) claims E3 will register "the zeitgeist moment fan-out" at this seam; that fan-out already lives at `status/adapters.py`. The consolidated seam must not repeat the misdirection.
- **Steps**: Add a section comment/docstring above the factory block in `events.py` stating, in this order: (1) the seam is the reserved E3 producer seam for the six `mission_next` runtime moments; (2) a producer registers via `register_runtime_emitter_factory` at import tail under the `SPEC_KITTY_SYNC_MINIMAL_IMPORT` gate, mirroring `specify_cli.status.adapters.ensure_zeitgeist_moment_handlers`; (3) the zeitgeist *moment fan-out* is a separate, already-live seam in `specify_cli/status/adapters.py` and is not what registers here; (4) reference ADR `2026-09-06-2`.
- **Files**: `src/runtime/next/_internal_runtime/events.py`
- **Parallel?**: Yes.

## Test Strategy

```bash
.venv/bin/pytest tests/next/test_internal_runtime_coverage.py -q -p no:cacheprovider
.venv/bin/pytest tests/runtime/test_bridge_parity.py tests/specify_cli/events/test_decision_log.py -q -p no:cacheprovider   # NullEmitter() call sites still work
.venv/bin/ruff check src/runtime/next/_internal_runtime/ tests/next/test_internal_runtime_coverage.py
.venv/bin/mypy src/runtime/next/_internal_runtime/events.py src/runtime/next/_internal_runtime/emitter.py
.venv/bin/pytest tests/architectural/test_layer_rules.py -q -p no:cacheprovider
```

Record passed/failed counts in the Activity Log.

## Risks & Mitigations

- **Signature drift on `NullEmitter.__init__`** breaks dozens of `NullEmitter()` call sites → keep `correlation_id` positional-first; new fields keyword-only with defaults (T001 step 2, test 8 in T005).
- **Leaked registry state between tests** → reset in `finally`/fixture.
- **Import cycle** via `specify_cli.mission_metadata` → it is already imported by `planner.py`; if mypy or import order complains, import inside `for_mission` with a `# noqa: PLC0415` and one-line rationale.

## Review Guidance

- Verify the Protocol body is byte-identical to before (R-2).
- Verify `event_emitter.py` is untouched.
- Verify S1–S6 each map to a named test.
- Grep the diff's added lines for `feature` — only the pre-existing `feature_dir` keyword may appear.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last). Append at the end. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`.

- 2026-09-06T16:48:26Z – system – Prompt created.
- 2026-09-06T18:40:16Z – claude/python-pedro – Implemented T001–T006 in commit 548130ee9 (worktree lane-a). Verification (main venv binaries, worktree src on PYTHONPATH, foreground with `timeout 600`): `pytest tests/next/test_internal_runtime_coverage.py -q -p no:cacheprovider` → 128 passed, 0 failed; `pytest tests/runtime/test_bridge_parity.py tests/specify_cli/events/test_decision_log.py -q -p no:cacheprovider` → 44 passed, 0 failed (NullEmitter() call sites intact); `pytest tests/architectural/test_layer_rules.py -q -p no:cacheprovider` → 54 passed, 0 failed; `ruff check src/runtime/next/_internal_runtime/ tests/next/test_internal_runtime_coverage.py` → exit 0; diff-scoped `ruff check $(git diff --name-only --diff-filter=AMR HEAD | grep '\.py$')` → exit 0; `mypy src/runtime/next/_internal_runtime/events.py src/runtime/next/_internal_runtime/emitter.py` → 0 issues. Terminology grep (`git diff HEAD | grep '^+' | grep -i feature | grep -v feature_dir`) → empty. Protocol body byte-identical (no +/- on any `emit_*` line); `event_emitter.py` untouched. One added `# noqa: BLE001` (justified inline, as specified). New names importable from both `_internal_runtime.events` and `_internal_runtime.emitter`; zero production callers of `runtime_emitter_for_mission` at this point is expected — WP03 rewires the bridge.
