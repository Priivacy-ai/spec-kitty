---
work_package_id: WP01
title: '#2669 — canonical mission-type accessor (doctrine enabler)'
dependencies: []
requirement_refs:
- C-010
- FR-001
- NFR-002
tracker_refs:
- '2669'
planning_base_branch: feat/mission-type-single-source-gate-wiring
merge_target_branch: feat/mission-type-single-source-gate-wiring
branch_strategy: Planning artifacts for this mission were generated on feat/mission-type-single-source-gate-wiring. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-type-single-source-gate-wiring unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: "claude"
shell_pid: "3271347"
shell_pid_created_at: "1784144098.5"
history:
- at: '2026-07-15T19:00:00Z'
  actor: claude
  note: WP authored post-plan squad — accessor cache-vs-SC001 seam pinned (architect HIGH-2, C-010).
agent_profile: python-pedro
authoritative_surface: src/doctrine/missions/
create_intent:
- tests/doctrine/missions/test_builtin_mission_type_ids.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/doctrine/missions/mission_type_repository.py
- tests/doctrine/missions/test_builtin_mission_type_ids.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, governance scope, boundaries, and initialization declaration. You are the **implementer**.

## Objective

Introduce the ONE canonical accessor that every mission-type roster in the codebase will derive from
(#2669). It lives in the **doctrine** layer next to `MissionTypeRepository`
(`src/doctrine/missions/mission_type_repository.py`) and returns the built-in mission-type ids read from the
`mission_types/*.yaml` source of truth — no hardcoded list. This is the enabler for WP02/WP03; it ships
first and alone.

## Context — READ BEFORE CODING

- `MissionTypeRepository` (`mission_type_repository.py`) already loads `mission_types/*.yaml`, validates
  `id == filename-stem` and schema (loud-fail), and exposes `.ids()` (sorted list) and `.default()`
  (bundled root via `importlib.resources`).
- **Layer rule:** doctrine MUST NOT import `charter`/`specify_cli`. The accessor stays layer-clean; charter
  will call it lazily later.
- **Cache-vs-test trap (architect HIGH-2 / C-010):** a `@functools.cache` on a parameterless accessor bound
  to `default()` would make the SC-001 "add a synthetic type → universal pickup" test impossible — a tmp
  dir is invisible (no injection seam) and a real-dir write is defeated by the cache AND races xdist workers
  (per CLAUDE.md, workers share the repo tree; only HOME is isolated). You MUST provide a test seam and the
  SC-001 test MUST NOT mutate `src/doctrine/missions/mission_types/`.

## Subtasks

### T001 — Add the canonical accessor

In `mission_type_repository.py`, add module-level:

```python
import functools

@functools.cache
def builtin_mission_type_ids() -> tuple[str, ...]:
    """The built-in mission-type ids, derived from the doctrine mission_types/*.yaml source.

    Single canonical authority for "which mission types ship". Sorted (lexicographic).
    Cached: one filesystem scan per process (NFR-002). Raises transitively if the
    repository loud-fails on an id/stem mismatch or invalid schema.
    """
    return tuple(MissionTypeRepository.default().ids())


def builtin_mission_type_id_set() -> frozenset[str]:
    """Frozenset projection of :func:`builtin_mission_type_ids` for membership/default consumers."""
    return frozenset(builtin_mission_type_ids())
```

Add both to `__all__`. Keep them the ONLY new public surface.

### T002 — Test seam (root injection + cache_clear)

`functools.cache` auto-provides `builtin_mission_type_ids.cache_clear()`. Confirm the SC-001 test can
inject a synthetic root by monkeypatching `MissionTypeRepository.default` (or the root it resolves) to a
tmp dir, then calling `cache_clear()`. Do NOT add a bespoke global-mutable-root; rely on
monkeypatch + `cache_clear`. Document the seam in the docstring.

### T003 — [ATDD, RED FIRST] SC-001 synthetic-type pickup

New file `tests/doctrine/missions/test_builtin_mission_type_ids.py`:
- Copy the four shipped `mission_types/*.yaml` into a `tmp_path` dir plus a synthetic `analysis.yaml`
  (valid schema, `id: analysis`); monkeypatch `MissionTypeRepository.default` to load that tmp root;
  call `builtin_mission_type_ids.cache_clear()`; assert `"analysis"` is in the result and the result is
  sorted. **Must NOT write into the real `src/doctrine/missions/mission_types/`.**
- Assert the un-monkeypatched accessor returns exactly the four shipped ids (sorted).
- Add a `cache_clear()` in a fixture teardown so the process cache never leaks a monkeypatched value to
  other tests.

### T004 — [ATDD, RED FIRST] loud-fail transitivity

- Point the accessor (via monkeypatch) at a tmp root containing a YAML whose `id` ≠ filename stem (or
  invalid schema); assert `builtin_mission_type_ids()` raises (the `MissionTypeRepository` `ValueError`
  propagates, not swallowed).

### T005 — Quality gate

- `uv run ruff check src/doctrine/missions/mission_type_repository.py`
- `uv run mypy --strict src/doctrine/missions/mission_type_repository.py`
- `uv run pytest tests/doctrine/missions/test_builtin_mission_type_ids.py -q`
- Complexity ≤ 15 (both functions are trivial).

## Branch Strategy

Planning base and merge target: `feat/mission-type-single-source-gate-wiring`. Execution worktrees are
allocated per computed lane from `lanes.json`; complete the WP in your lane and it merges back to the
mission branch (the operator performs the mainline merge).

## Definition of Done

- [ ] `builtin_mission_type_ids()` (cached, sorted) + `builtin_mission_type_id_set()` in doctrine, in `__all__`.
- [ ] SC-001 test injects a synthetic type via monkeypatch + `cache_clear` WITHOUT touching the shared tree, and is green.
- [ ] Loud-fail transitivity test green.
- [ ] ruff + mypy --strict clean; no new suppressions.
- [ ] ATDD: T003/T004 committed RED before T001/T002 implementation.

## Reviewer guidance

Verify the accessor is layer-clean (no charter/specify_cli import), the cache seam does not mutate the
shared doctrine tree, and the SC-001 test would actually FAIL if the accessor were hardcoded. Confirm
`cache_clear` teardown prevents cross-test leakage under `-n auto`.

## Activity Log

- 2026-07-15T19:35:05Z – claude – shell_pid=3271347 – Assigned agent via action command
- 2026-07-15T19:46:39Z – claude – shell_pid=3271347 – WP01 accessor: reviewer-renata APPROVE; ATDD red→green, C-010 seam verified
- 2026-07-15T19:50:10Z – user – shell_pid=3271347 – reviewer-renata APPROVE
