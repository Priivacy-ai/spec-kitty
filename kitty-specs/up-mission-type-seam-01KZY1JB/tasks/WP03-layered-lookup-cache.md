---
work_package_id: WP03
title: 'New layered mission-type lookup: module-level cache, malformed-YAML loud-fail (red-first)'
dependencies:
- WP02
requirement_refs:
- C-006
- C-007
- C-008
- FR-001
- NFR-001
- NFR-002
- NFR-003
- NFR-004
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
phase: Phase 2 - Layered lookup (IC-01)
assignee: ''
agent: claude
history:
- at: '2026-08-13T00:00:00Z'
  actor: system
  action: Prompt generated during /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/missions/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/missions/mission_type_repository.py
- tests/doctrine/missions/test_mission_type_repository.py
- tests/charter/test_charter_import_time_io.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – New layered mission-type lookup: module-level cache, malformed-YAML loud-fail (red-first)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` and behave according to its guidance
before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Add a **new, separate, module-level, pack-aware layered lookup** in
`src/doctrine/missions/mission_type_repository.py` — sibling to, never a replacement for,
`MissionTypeRepository.default()` (which stays untouched: still a `@classmethod
@functools.cache` keyed on `cls` only, still built-in-only). This is FR-001, the mission's
foundational seam (IC-01).

**Success criteria**:

1. A new module-level `@functools.cache`-decorated factory, keyed on `(mission_types_dirs,
   pack_context)` — a tuple of directories plus the existing structural `_PackContextLike` object
   — living beside (not inside) the `MissionTypeRepository` class, mirroring the sibling module's
   own already-live pattern: `_resolve_all_for_mission_type_cached`
   (`src/doctrine/missions/mission_step_repository.py`, live-verify the exact line range — plan.md
   cites `446-470`), a bare module-level `@functools.cache` function, **not** a classmethod cache.
2. A `cache_clear()` static test seam, mirroring `MissionStepRepository.cache_clear`
   (`mission_step_repository.py`, live-verify — plan.md cites `323-333`, a `@staticmethod` that
   calls `.cache_clear()` on the module-level cached function).
3. It imports the existing structural `_PackContextLike` `Protocol`
   (`mission_step_repository.py`, live-verify — plan.md cites `41-61`, declaring `pack_roots:
   tuple[Path, ...]`, `repo_root: Path`, and an explicit `__hash__`) from its **sibling module in
   the same package** (`doctrine.missions`) — this is not a new cross-layer import; `doctrine`
   still never imports `charter` (NFR-003/C-008).
4. **A red-first regression test for the spec.md malformed-YAML Edge Case** (this is the plan
   ruling's PLAN-FRESH2-003 remediation, binding — see below): a scratch org/project mission-type
   pack whose single `*.yaml` file is syntactically invalid YAML, asserting the new factory's
   resolution raises an error whose message names that file's path. This must be written and
   proven RED against the pre-fix behavior (or, since the factory itself doesn't exist pre-fix,
   RED in the sense of "the test fails to compile/pass until the wrapping+re-raise logic exists")
   before the fix that makes it pass, per the same red-first discipline this mission applies
   everywhere it changes behavior (C-011, ATDD-first).
5. `default()`'s own cache key and returned built-in roster are provably unaffected by any
   activity on the new factory — User Story 3 AC2 — verified by a same-process test exercising both.
6. NFR-001: the new factory's cache key includes both `mission_types_dirs` and `pack_context`; a
   project-A resolution followed by a project-B resolution in the same process returns distinct,
   correct results for each — a same-process, two-project regression test.

## Context & Constraints

- **Read `kitty-specs/up-mission-type-seam-01KZY1JB/plan.md`'s IC-01 section in full** (including
  its "Risks" bullet — the factory's exact per-call signature, whether it mirrors
  `MissionStepRepository`'s per-call `pack_context` parameter shape or bakes org/project
  directories into `MissionTypeRepository.__init__`, is a tasks-phase implementation choice the
  plan deliberately leaves open. **This WP's decision**: mirror the per-call `pack_context`
  parameter shape (matching `_resolve_all_for_mission_type_cached`'s own signature) rather than
  changing `MissionTypeRepository.__init__` — this keeps `_inject_projected_fields`'s existing
  signature least disturbed, which is the property plan.md's "Producer-scan constraint" section
  says CL-001 protects (see below). If you find a strong reason to prefer the alternative shape
  during implementation, document why in your commit message and this WP's Activity Log rather
  than switching silently.
- **Producer-scan constraint (read plan.md's own section by this name in full)**: do NOT move
  `payload["action_sequence"] = ...` (inside `_inject_projected_fields`,
  `mission_type_repository.py`, live-verify — plan.md cites line `209`) out of
  `src/doctrine/missions/mission_type_repository.py`. `tests/architectural/test_no_inert_schema_slots.py`'s
  producer-scan only walks `src/doctrine/` + `packs/built-in/` for a slot's producer; moving this
  assignment to `src/charter/` would red that gate's `assert new == []`. This is CL-001's rejected
  option (b) — do not reintroduce it.
- **Malformed-YAML handling — the exact citation you need**: `MissionTypeRepository._load`
  (`mission_type_repository.py`, live-verify — plan.md cites `130-163`) calls
  `_yaml.load(yaml_file.read_text(encoding="utf-8"))` (live-verify — plan.md cites line `147`) —
  parsing a bare `str`, not a named stream — so a `ruamel.yaml.YAMLError` raised there carries no
  file identity of its own unless the caller wraps it. **Naively reusing this exact call shape
  unmodified for org/project scanning would satisfy "fail loudly" but NOT spec.md's "naming the
  offending file" half of the requirement.** Your new factory's org/project-layer parse call MUST
  wrap and re-raise with the offending file's path named in the error message.
- **This is distinct from, and does not require changing,
  `charter/pack_manager.py`'s unrelated `_declared_id` helper** (live-verify — plan.md cites
  `339-355`), which already catches `YAMLError` and returns `None` for a malformed file during
  WP05's *availability* scan. That helper is shared, generic, kind-agnostic machinery serving
  every charter-activatable artifact kind, not mission-type-specific — changing its
  silent-skip-to-loud-fail behavior would be a materially larger, unrelated-blast-radius change
  outside this mission's scope. **Do not touch `pack_manager.py` in this WP** — that file belongs
  to WP05, which runs concurrently with this WP (see below). The binding "fail loudly, naming the
  file" requirement is satisfied at the point this WP's layered lookup actually *resolves* a
  roster entry's fields, not at the earlier, separate availability-*listing* step WP05 owns.
- **NFR-004 (import-time-IO)**: the factory must never be called at module scope in any
  `charter.*` module — a naive "warm the cache at import" optimization would trip
  `tests/charter/test_charter_import_time_io.py`'s
  `TestHotModulesTriggerZeroImportTimeIo.test_import_charter_mission_type_profiles_and_pack_context_bounded_io`
  test (live-verify — plan.md cites lines `244-291`). Extend that test file to assert the *new*
  factory also respects the ≤1-call-at-import bound (it should currently be zero calls, since
  nothing calls it yet at this WP's point in the sequence — WP04 is what wires a caller in).
- **This WP runs concurrently with WP05** (both depend only on WP02). Confirm your `owned_files`
  (`src/doctrine/missions/mission_type_repository.py`,
  `tests/doctrine/missions/test_mission_type_repository.py`,
  `tests/charter/test_charter_import_time_io.py`) stay disjoint from WP05's
  (`src/charter/activation/pack_manager.py`, `tests/charter/test_pack_manager.py`) — do not reach into
  `pack_manager.py` even for a "quick fix."

## Branch Strategy

- **Strategy**: Planning artifacts for this mission were generated on
  `kitty/mission-up-mission-type-seam-01KZY1JB`. During `/spec-kitty.implement` this WP may branch
  from a dependency-specific base, but completed changes must merge back into
  `kitty/mission-up-mission-type-seam-01KZY1JB` unless the human explicitly redirects the landing
  branch.
- **Planning base branch**: `kitty/mission-up-mission-type-seam-01KZY1JB`
- **Merge target branch**: `main`

## Subtasks & Detailed Guidance

### Subtask T005 – Red-first: malformed-YAML regression test

- **Purpose**: PLAN-FRESH2-003's binding remediation — a real red-first test, not a patched
  sentence.
- **Steps**:
  1. Construct a scratch org (or project) mission-type pack directory containing exactly one
     `*.yaml` file with syntactically invalid YAML content (e.g. unbalanced brackets, a tab
     character where YAML forbids one, or an unterminated flow sequence — pick something ruamel.yaml
     genuinely rejects, verify by hand first).
  2. Write a test in `tests/doctrine/missions/test_mission_type_repository.py` that calls the new
     factory (once it exists — you may write this test in tandem with T006, but the test itself
     must assert the raise-with-path-named behavior, and should fail if that wrapping is missing)
     against that scratch pack, and asserts: (a) an error is raised (not a silent skip, not an
     empty roster), and (b) the error message contains the offending file's path.
  3. Confirm this test is genuinely red before the wrapping/re-raise logic exists (e.g. temporarily
     verify against a version of the factory that uses `MissionTypeRepository._load`'s exact
     unwrapped call shape — the test should fail because the raised error has no file identity, or
     because the file was silently skipped) and green after.
- **Files**: `tests/doctrine/missions/test_mission_type_repository.py`.
- **Parallel?**: Sequenced tightly with T006 (you'll likely write test and implementation
  together, but the test must demonstrably fail against the naive/unwrapped call shape first).
- **Notes**: This is the mission's other red-first test (besides WP06's NFR-005 one) — it does not
  carry NFR-005's "two separate ordered commits" requirement (that's specific to CL-003/FR-004),
  but it should still be committed in a way that a reviewer can see it failing against the
  unwrapped shape if they choose to check.

### Subtask T006 – Implement the layered factory + `cache_clear()` seam

- **Purpose**: FR-001, the mission's foundational seam.
- **Steps**:
  1. Add the module-level `@functools.cache`-decorated factory to
     `src/doctrine/missions/mission_type_repository.py`, keyed on `(mission_types_dirs,
     pack_context)`, mirroring `_resolve_all_for_mission_type_cached`'s shape.
  2. Add the `cache_clear()` `@staticmethod` seam, mirroring `MissionStepRepository.cache_clear`.
  3. Import `_PackContextLike` from `mission_step_repository.py` (sibling module, same package) —
     confirm this is the only new import and it introduces no new cross-layer edge
     (`doctrine.missions` still imports nothing from `charter`).
  4. Wire the malformed-YAML wrap-and-re-raise logic (T005) into this factory's org/project-layer
     parse path.
  5. Confirm `MissionTypeRepository.default()` is untouched — no edit to its body, decorator, or
     cache behavior.
- **Files**: `src/doctrine/missions/mission_type_repository.py`.
- **Parallel?**: Tightly coupled with T005.
- **Notes**: Live-verify every file:line citation in this prompt before relying on it — plan.md
  itself warns these drift.

### Subtask T007 – Cache-key correctness (NFR-001), `default()` non-interference (User Story 3 AC2), import-time-IO extension (NFR-004)

- **Purpose**: prove the new cache is correct under project-scoping and does not leak state or
  interfere with the pre-existing built-in-only cache.
- **Steps**:
  1. Add a test: same `(mission_types_dirs, pack_context)` key called twice returns a cache hit
     (verify via identity or a call-count instrumentation on the underlying filesystem walk).
  2. Add a test: two distinct `pack_context`s (representing two different projects) in the same
     process return distinct, correct results for each (NFR-001's same-process, two-project
     regression).
  3. Add a test: `cache_clear()` actually clears — a subsequent call after `cache_clear()` re-walks
     the filesystem (or otherwise proves the cache was emptied).
  4. Add a test: exercising the new factory does not affect `MissionTypeRepository.default()`'s own
     cache key or returned built-in roster (User Story 3 AC2 — "no shared mutable state, no
     cross-project pollution").
  5. Extend `tests/charter/test_charter_import_time_io.py` to assert the new factory also respects
     the ≤1-call-at-import bound (NFR-004) — confirm it is exercised zero times at import in this
     WP's state (nothing calls it yet; WP04 wires the first caller).
- **Files**: `tests/doctrine/missions/test_mission_type_repository.py`,
  `tests/charter/test_charter_import_time_io.py`.
- **Parallel?**: Can proceed alongside T005/T006 once the factory shape is settled.
- **Notes**: This subtask is where NFR-001's "verified by a same-process, two-project regression
  test" requirement is literally satisfied — do not treat it as implicitly covered by other tests.

## Test Strategy

- **Per-AC / per-SC**: this WP is foundational to **SC-001** (the end-to-end four-CLI-surface
  regression — this WP supplies the layered lookup that makes SC-001 possible, though the
  end-to-end assertion itself lands in WP07) and directly proves **SC-004** ("Zero new cross-layer
  imports from `src/doctrine/` into `src/charter/`" — measured by
  `tests/architectural/test_layer_rules.py` continuing to pass with no new allowlist entries) and
  the malformed-YAML half of spec.md's Edge Cases section.
- **Test surface**: `tests/doctrine/missions/test_mission_type_repository.py` (extended, not
  replaced — preserve the file's existing `MissionType`/`MissionTypeRepository` round-trip test
  classes), `tests/charter/test_charter_import_time_io.py` (extended).
- **Commands**: `uv run pytest tests/doctrine/missions/test_mission_type_repository.py
  tests/charter/test_charter_import_time_io.py -v`

## Risks & Mitigations

- **Risk**: the factory gets called at module scope somewhere in `charter.*`, tripping NFR-004's
  import-time-IO gate. **Mitigation**: this WP adds no caller in `charter.*` at all (WP04 does) —
  confirm this WP's diff contains zero new call sites of the factory outside its own test file.
- **Risk**: the malformed-YAML fix accidentally also changes `pack_manager.py`'s `_declared_id`
  behavior (scope creep into WP05's file). **Mitigation**: do not touch `pack_manager.py` in this
  WP; the fix is scoped to `mission_type_repository.py`'s own parse path.
- **Risk**: producer-scan constraint violation — moving `_inject_projected_fields`'s
  `action_sequence` assignment out of this module. **Mitigation**: this WP does not move that
  assignment; it only adds a new factory beside the existing class.

## Gate Set (this WP's Definition of Done)

- **`fast-tests-doctrine` + `integration-tests-doctrine`** (`--cov=doctrine --cov=charter`) — this
  WP's change to `mission_type_repository.py` is directly in scope.
- **`fast-tests-charter` + `integration-tests-charter`** (`--cov=charter --cov-fail-under=55`) —
  `tests/charter/test_charter_import_time_io.py` extension is directly in scope.
- **`diff-coverage` (critical-path, 90%, `[ENFORCED]`)** over `src/doctrine/*` — every new
  branch/line in this WP's factory (cache-hit path, cache-miss path, malformed-YAML raise path)
  needs a directly-testing unit test (see T007).
- **`arch-adversarial`** — must not regress `test_layer_rules.py`'s
  `test_doctrine_does_not_import_charter` or `test_no_inert_schema_slots.py`'s producer-scan
  assertion.
- **`Typer 0.26 JSON error surface`, `patch() target validation`, `Bandit`, `pip-audit`,
  `commitlint`** — always-on in `lint`.
- `make lint` locally before handing off.

## Review Guidance

- Confirm `MissionTypeRepository.default()` is byte-identical to pre-WP behavior (diff should show
  zero changes to its body/decorator).
- Confirm the malformed-YAML test is genuinely red against the naive/unwrapped call shape — ask
  the implementer to demonstrate this if not obvious from the commit history.
- Confirm the new factory is never called at module scope anywhere in this WP's diff.
- Confirm `_PackContextLike` is imported from `mission_step_repository.py`, not redefined locally
  or imported from `charter.*`.
- Confirm NFR-001's two-project regression test actually constructs two distinct `pack_context`
  objects and asserts distinct results, not merely two calls with the same context.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-08-13T00:00:00Z – system – Prompt created.
