# Tasks: Mission-Type Single-Source + Gate Wiring

**Mission**: `mission-type-single-source-gate-wiring-01KXKHVZ`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) (IC-1..IC-4)
**Delivery order (correctness-bearing, C-002)**: IC-1 (#2669) → IC-2 (#2667) → IC-3 (#2666) → IC-4 (#2668)

## Dependency graph

```
WP01 (accessor, doctrine) ──┬─► WP02 (Rosters A+B) ──┐
                            └─► WP03 (Rosters C+D+E) ─┤
WP04 (fail-loud) ─► WP05 (doctor+gate) ──────────────┴─► WP06 (promote + noqa drops, LAST)
```

- WP01 and WP04 have no dependencies → start in parallel.
- WP02 ∥ WP03 (both depend on WP01, touch disjoint files).
- WP05 depends on WP04 (gate is vacuous over a silently-degraded index until fail-loud lands).
- WP06 is terminal (depends on WP02, WP03, WP05) — it consumes the promoted accessor and drops the two
  `# noqa: SLF001` bypasses as small documented out-of-map edits after the file owners are done.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Add `builtin_mission_type_ids()` (`@functools.cache`, sorted) + frozenset convenience in doctrine | WP01 | |
| T002 | Expose a root-injection + `cache_clear` test seam (no shared-tree mutation) | WP01 | |
| T003 | [ATDD] SC-001 synthetic-type pickup test (monkeypatch root→tmp, `cache_clear`) — RED first | WP01 | |
| T004 | [ATDD] loud-fail transitivity test (bad mission-type YAML → accessor raises) | WP01 | |
| T005 | ruff/mypy/complexity + targeted test run | WP01 | |
| T006 | [ATDD] import-time-I/O guard: importing charter modules triggers zero `mission_types/` reads — RED | WP02 | |
| T007 | Retire `CANONICAL_MISSION_TYPES`; remove from `charter/__init__.__all__`; migrate 3 test consumers | WP02 | |
| T008 | Derive `_BUILTIN_MISSION_TYPE_IDS` lazily inside `_read_activated_mission_types` (preserve frozenset) | WP02 | |
| T009 | Confirm frozenset-equality contract preserved (`test_pack_context`) | WP02 | |
| T010 | ruff/mypy/complexity + targeted tests + arch_shard_1 pole | WP02 | |
| T011 | [ATDD] behavioral test: a `software-dev` identifier answer still resolves after E is derived — RED | WP03 | |
| T012 | Roster C: migration reads `MissionTypeRepository.default().ids()` at `apply()`; update migration tests | WP03 | [P] |
| T013 | Roster D: `ALLOWED_MISSION_TYPES = frozenset(ids) \| {any,generic}`; keep frozenset; refresh body_hash | WP03 | |
| T014 | Roster E: derive `_MISSION_IDENTIFIER_ANSWERS`, preserve `software_dev` underscore alias | WP03 | |
| T015 | ruff/mypy/complexity + targeted tests + arch_shard_1 dead-symbol body_hash | WP03 | |
| T016 | [ATDD] fail-loud tests: present-but-invalid raises; missing→fallback; empty-well-formed→empty — RED | WP04 | |
| T017 | Add `ActionIndexError(ValueError)`; raise on non-mapping root / non-list field / unparseable YAML | WP04 | |
| T018 | Re-pin the 2 lenient `test_action_index.py` tests to `pytest.raises` (re-pin, not delete) | WP04 | |
| T019 | ruff/mypy/complexity + targeted tests | WP04 | |
| T020 | [ATDD] CLI test: `doctor doctrine --json` shape + RC=1 on a synthetic collision — RED | WP05 | |
| T021 | Wire scan into `doctrine_check` (catch `CrossGrainDoubleDeclarationError` → unhealthy + RC=1 + json) | WP05 | |
| T022 | Re-add `scan_builtin_cross_grain_duplicates` to `action_grain.__all__` (same change — C-003) | WP05 | |
| T023 | Add a dedicated CI structural gate test (arch tier), independent of the broad run | WP05 | |
| T024 | ruff/mypy/complexity + targeted tests + arch_shard_1 dead-symbol gate green | WP05 | |
| T025 | [ATDD] test: `builtin_missions_root()` returns `src/doctrine/missions` — RED | WP06 | |
| T026 | Promote `builtin_missions_root()` (module-level fn; classmethod delegates) | WP06 | |
| T027 | Drop `# noqa: SLF001` at `action_grain.py:202` → `builtin_missions_root()` (out-of-map, documented) | WP06 | |
| T028 | Drop `# noqa: SLF001` at `mission_type_profiles.py:649` → `builtin_missions_root()` (out-of-map) | WP06 | |
| T029 | ruff/mypy/complexity + full arch_shard_1 pole + terminology guard | WP06 | |

---

## WP01 — Canonical mission-type accessor (doctrine enabler)

- **Goal**: One cached doctrine-layer accessor deriving the built-in mission-type ids from
  `MissionTypeRepository`, with a test seam that lets the SC-001 guard inject a synthetic type without
  mutating the shared doctrine tree. Foundation for all roster derivations.
- **Priority**: P0 (enabler). **Dependencies**: none. **Independent test**: `uv run pytest tests/doctrine/missions -k builtin_mission_type_ids -q`.
- **Requirements**: FR-001, NFR-002, C-010.
- **Estimated prompt size**: ~260 lines.

- [x] T001 Add `builtin_mission_type_ids()` (`@functools.cache`, sorted) + frozenset convenience (WP01)
- [x] T002 Expose a root-injection + `cache_clear` test seam (WP01)
- [x] T003 [ATDD] SC-001 synthetic-type pickup test — RED first (WP01)
- [x] T004 [ATDD] loud-fail transitivity test (WP01)
- [x] T005 ruff/mypy/complexity + targeted test run (WP01)

## WP02 — Charter Rosters A + B (retire the constant; lazy frozenset)

- **Goal**: Retire `CANONICAL_MISSION_TYPES` as a public constant and derive `_BUILTIN_MISSION_TYPE_IDS`
  lazily, with zero import-time filesystem I/O in charter.
- **Priority**: P1. **Dependencies**: WP01. **Independent test**: `uv run pytest tests/charter -q`.
- **Requirements**: FR-002, FR-003, NFR-001, C-011.
- **Estimated prompt size**: ~300 lines.

- [x] T006 [ATDD] import-time-I/O guard — RED (WP02)
- [x] T007 Retire `CANONICAL_MISSION_TYPES` + remove from `__all__` + migrate 3 test consumers (WP02)
- [x] T008 Derive `_BUILTIN_MISSION_TYPE_IDS` lazily (frozenset) (WP02)
- [x] T009 Confirm frozenset-equality contract preserved (WP02)
- [x] T010 ruff/mypy/complexity + targeted tests + arch_shard_1 pole (WP02)

## WP03 — Charter Rosters C + D + E (migration live-read; sentinels; alias)

- **Goal**: Derive the migration roster (live-read), `ALLOWED_MISSION_TYPES` (frozenset + sentinels, with
  the dead-symbol body_hash refreshed), and `_MISSION_IDENTIFIER_ANSWERS` (underscore alias preserved).
- **Priority**: P1. **Dependencies**: WP01. **Independent test**: `uv run pytest tests/charter tests/upgrade -q`.
- **Requirements**: FR-004, FR-005, FR-006, C-004, C-011.
- **Estimated prompt size**: ~320 lines.

- [x] T011 [ATDD] behavioral test: `software-dev` identifier answer resolves after E derived — RED (WP03)
- [x] T012 Roster C: migration live-read at `apply()`; update migration tests (WP03)
- [x] T013 Roster D: `ALLOWED_MISSION_TYPES` derive + keep frozenset + refresh body_hash (WP03)
- [x] T014 Roster E: derive `_MISSION_IDENTIFIER_ANSWERS`, preserve `software_dev` alias (WP03)
- [x] T015 ruff/mypy/complexity + targeted tests + arch_shard_1 dead-symbol body_hash (WP03)

## WP04 — `load_action_index` fails loud (IC-2)

- **Goal**: A present-but-malformed action index raises a structured `ActionIndexError`; a missing file
  stays a silent fallback; an intentionally-empty well-formed index stays empty.
- **Priority**: P1 (must precede WP05). **Dependencies**: none. **Independent test**: `uv run pytest tests/doctrine/missions/test_action_index.py -q`.
- **Requirements**: FR-007, FR-008.
- **Estimated prompt size**: ~240 lines.

- [x] T016 [ATDD] fail-loud tests (present-invalid raises; missing→fallback; empty→empty) — RED (WP04)
- [x] T017 Add `ActionIndexError`; raise on the 3 present-but-invalid cases (WP04)
- [x] T018 Re-pin the 2 lenient tests to `pytest.raises` (WP04)
- [x] T019 ruff/mypy/complexity + targeted tests (WP04)

## WP05 — Wire the FR-013 scan into `doctor doctrine` + CI gate (IC-3)

- **Goal**: The cross-grain scan runs from `spec-kitty doctor doctrine` (RC=1 + json finding on collision)
  and a dedicated CI structural gate; the symbol is re-added to `__all__` alongside its new src caller.
- **Priority**: P1. **Dependencies**: WP04. **Independent test**: `uv run pytest tests/specify_cli/cli/commands -k doctrine -q && uv run pytest tests/doctrine/drg/test_cross_grain_integrity.py -q`.
- **Requirements**: FR-009, FR-010, FR-011, C-003.
- **Estimated prompt size**: ~300 lines.

- [x] T020 [ATDD] CLI test: `doctor doctrine --json` + RC=1 on synthetic collision — RED (WP05)
- [x] T021 Wire scan into `doctrine_check` (unhealthy + RC=1 + json finding) (WP05)
- [x] T022 Re-add `scan_builtin_cross_grain_duplicates` to `action_grain.__all__` (C-003) (WP05)
- [x] T023 Add a dedicated CI structural gate test (WP05)
- [x] T024 ruff/mypy/complexity + targeted tests + arch_shard_1 dead-symbol gate green (WP05)

## WP06 — Promote `builtin_missions_root()` + drop SLF001 (IC-4, terminal campsite)

- **Goal**: Promote the private built-in-root accessor to a public seam and remove both `# noqa: SLF001`
  bypasses. Pure refactor; single-class scope; lands last.
- **Priority**: P2 (campsite). **Dependencies**: WP02, WP03, WP05. **Independent test**: `uv run pytest tests/charter -k "builtin_missions_root or action_grain" -q`.
- **Requirements**: FR-012, C-005.
- **Estimated prompt size**: ~220 lines.

- [ ] T025 [ATDD] test: `builtin_missions_root()` returns `src/doctrine/missions` — RED (WP06)
- [ ] T026 Promote `builtin_missions_root()` (module-level fn; classmethod delegates) (WP06)
- [ ] T027 Drop `# noqa: SLF001` at `action_grain.py:202` (out-of-map, documented) (WP06)
- [ ] T028 Drop `# noqa: SLF001` at `mission_type_profiles.py:649` (out-of-map, documented) (WP06)
- [ ] T029 ruff/mypy/complexity + full arch_shard_1 pole + terminology guard (WP06)

---

## MVP scope

WP01 is the enabler; the smallest coherent shippable slice is WP01 → WP02 → WP03 (#2669 fully closed).
WP04 → WP05 (#2667 + #2666) and WP06 (#2668) complete the bundle.
