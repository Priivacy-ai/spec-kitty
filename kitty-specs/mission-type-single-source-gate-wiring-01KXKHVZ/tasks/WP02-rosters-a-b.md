---
work_package_id: WP02
title: '#2669 — Charter Rosters A+B: retire CANONICAL, lazy frozenset'
dependencies:
- WP01
requirement_refs:
- C-011
- FR-002
- FR-003
- NFR-001
tracker_refs:
- '2669'
planning_base_branch: feat/mission-type-single-source-gate-wiring
merge_target_branch: feat/mission-type-single-source-gate-wiring
branch_strategy: Planning artifacts for this mission were generated on feat/mission-type-single-source-gate-wiring. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-type-single-source-gate-wiring unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
agent: "claude"
shell_pid: "3300788"
shell_pid_created_at: "1784145033.37"
history:
- at: '2026-07-15T19:00:00Z'
  actor: claude
  note: WP authored post-plan squad — Roster A retirement is a public-API change (architect MED-1); NFR-001 lazy-call.
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent:
- tests/charter/test_charter_import_time_io.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/charter/mission_type_profiles.py
- src/charter/pack_context.py
- src/charter/__init__.py
- tests/charter/test_pack_context.py
- tests/charter/test_mission_type_profile_override.py
- tests/charter/test_action_grain.py
- tests/doctrine/drg/test_cross_grain_integrity.py
- tests/charter/test_charter_import_time_io.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, governance scope, boundaries, and initialization declaration. You are the **implementer**.

## Objective

Route the two "core" charter mission-type rosters through the WP01 accessor (#2669), with **zero
import-time filesystem I/O** in charter (NFR-001):
- **Roster A** `CANONICAL_MISSION_TYPES` (`mission_type_profiles.py:91`) — **retire** the module constant.
- **Roster B** `_BUILTIN_MISSION_TYPE_IDS` (`pack_context.py:49`) — derive lazily, **preserve frozenset**.

## Context — READ BEFORE CODING

- **Roster A is a public-API retirement (architect MED-1 / C-011).** A module-level constant cannot be
  "derived lazily" — deriving it at module scope reintroduces import-time I/O (violates NFR-001), and
  keeping it hardcoded violates single-source. So **delete the constant** and convert every consumer to call
  `builtin_mission_type_ids()`. Consumers (all safe — set/iteration, no order dependence, verified by the
  squad):
  - the re-export at `charter/__init__.py:74` and the `__all__` entry at `charter/__init__.py:147` — REMOVE both.
  - the `__all__` entry at `mission_type_profiles.py:71` — REMOVE.
  - tests: `test_cross_grain_integrity.py:104`, `test_action_grain.py:201,206`, `test_mission_type_profile_override.py:97` — migrate `set(CANONICAL_MISSION_TYPES)` → `set(builtin_mission_type_ids())` (import from `doctrine.missions.mission_type_repository`).
- **Roster B is trivially lazy:** `_BUILTIN_MISSION_TYPE_IDS` is private and read only inside
  `_read_activated_mission_types` (`pack_context.py:271`), whose return type is `frozenset[str]`. Replace the
  module constant with a lazy call to `builtin_mission_type_id_set()` **inside that function**
  (function-local import, `# noqa: PLC0415` per the existing convention — for import-time-I/O timing, NOT
  cycle avoidance; there is no cycle). `tests/charter/test_pack_context.py:31,88,105` assert
  `ctx.activated_mission_types == _BUILTIN_MISSION_TYPE_IDS` (frozenset equality) — migrate those assertions
  to `builtin_mission_type_id_set()`.

## Subtasks

### T006 — [ATDD] single-source RED-first driver + import-time-I/O regression guard

New file `tests/charter/test_charter_import_time_io.py` with TWO tests:
1. **RED-first single-source driver:** monkeypatch the accessor root (a tmp dir with a synthetic `analysis`
   type; `cache_clear()`) and assert the default activation set derived by `_read_activated_mission_types`
   (i.e. `PackContext.from_config` with no `mission_type_activations` key) then contains `analysis` — RED
   before T008 (today `_BUILTIN_MISSION_TYPE_IDS` is a hardcoded literal that ignores the accessor). This is
   the genuine red-first behavior for #2669 in this WP. `cache_clear()` teardown.
2. **Import-time-I/O regression guard (green-stays-green):** assert importing the HOT modules
   `charter.mission_type_profiles` and `charter.pack_context` triggers ZERO reads of `mission_types/`
   (spy: patch `builtin_mission_type_ids` to raise if called during a fresh import in a subprocess, or count
   `MissionTypeRepository.default` calls). It passes today (literals) and must keep passing (lazy). Do **NOT**
   assert this for `charter.activations` / `interview_mapping` — those are the C-012 carve-out (they derive at
   module scope by design; a ≤1 cached read there is expected).

### T007 — Retire Roster A

Delete `CANONICAL_MISSION_TYPES` from `mission_type_profiles.py`; remove it from that module's `__all__` and
from `charter/__init__.py` (both the import and the `__all__` entry). Migrate the 3 test consumers to
`builtin_mission_type_ids()`.

### T008 — Derive Roster B lazily (frozenset)

Replace `_BUILTIN_MISSION_TYPE_IDS` with a lazy `builtin_mission_type_id_set()` call inside
`_read_activated_mission_types`. Keep the `frozenset[str]` return type and the `None`→default /
`[]`→`frozenset()` three-state semantics exactly (FR-039 behavior). **No `if x is None:` hardcoded fallback**
(C-001) — the default IS the accessor call.

### T009 — Confirm frozenset contract

Update `test_pack_context.py` assertions to compare against `builtin_mission_type_id_set()`; confirm the
default remains a frozenset and equality holds.

### T010 — Quality gate

- `uv run ruff check src/charter/ && uv run mypy --strict src/charter/mission_type_profiles.py src/charter/pack_context.py src/charter/__init__.py`
- `uv run pytest tests/charter tests/doctrine/drg/test_cross_grain_integrity.py -q`
- Reproduce the arch pole (dead-symbol + terminology): `uv run python -m pytest tests/adversarial tests/architectural tests/architecture tests/lint -m 'arch_shard_1 and not windows_ci and (git_repo or integration or architectural) and not timing' -q -n auto --dist loadfile`

## Branch Strategy

Base/merge target `feat/mission-type-single-source-gate-wiring`. Depends on WP01 (the accessor). Execution
worktree per `lanes.json` lane.

## Definition of Done

- [ ] `CANONICAL_MISSION_TYPES` deleted; removed from `mission_type_profiles.__all__` and `charter/__init__.__all__`; 3 test consumers migrated.
- [ ] `_BUILTIN_MISSION_TYPE_IDS` derived lazily (frozenset preserved), no hardcoded fallback (C-001).
- [ ] Import-time-I/O regression guard green for the hot modules (NFR-001); activations/interview_mapping excluded (C-012).
- [ ] ruff + mypy --strict clean; arch_shard_1 pole green.
- [ ] ATDD: the T006 **single-source driver** committed RED first (the import-time-I/O guard is a green-stays-green regression guard, per C-008).

## Reviewer guidance

Confirm no charter module reads `mission_types/` at import time; confirm the retirement removed BOTH `__all__`
sites; confirm Roster B's three-state (None/[]/list) semantics are byte-identical and frozenset-typed.

## Activity Log

- 2026-07-15T19:50:40Z – claude – shell_pid=3300788 – Assigned agent via action command
- 2026-07-15T20:14:21Z – claude – shell_pid=3300788 – WP02 Rosters A+B: reviewer-renata APPROVE; retirement + lazy frozenset, three-state byte-identical
- 2026-07-15T20:14:23Z – user – shell_pid=3300788 – reviewer-renata APPROVE
