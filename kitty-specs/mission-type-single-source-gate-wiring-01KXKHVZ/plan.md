# Implementation Plan: Mission-Type Single-Source + Gate Wiring

**Branch**: `feat/mission-type-single-source-gate-wiring` | **Date**: 2026-07-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/mission-type-single-source-gate-wiring-01KXKHVZ/spec.md`

## Summary

Close four post-merge follow-ups (#2669 → #2667 → #2666 → #2668) from PR #2664 as one bundle:
route every hardcoded mission-type roster through the single doctrine source of truth
(`MissionTypeRepository`), make malformed doctrine action-indexes fail loud, wire the FR-013 cross-grain
scan into a real runtime surface (`spec-kitty doctor doctrine`) plus a CI structural gate, and promote a
private built-in-root accessor to a public seam. Technical approach and every scope fork are locked in the
spec; this plan translates them into an Implementation Concern Map and a correctness-bearing delivery
order.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer (CLI), ruamel.yaml (YAML parsing), pydantic v2 (models), pytest, mypy --strict, ruff
**Storage**: Filesystem doctrine tree (`src/doctrine/missions/mission_types/*.yaml`, `.../actions/*/index.yaml`); no database
**Testing**: pytest (targeted packages: `tests/charter/`, `tests/doctrine/`, `tests/specify_cli/cli/commands/`, `tests/upgrade/`, `tests/architectural/`); ATDD red-first; arch_shard_1 CI pole for dead-symbol + terminology gates
**Target Platform**: Linux/macOS/Windows CLI (cross-platform)
**Project Type**: single (Python CLI + library, layered `kernel < doctrine < charter < runtime < specify_cli`)
**Performance Goals**: No import-time filesystem I/O regression in `src/charter/`; accessor caches (≤1 scan/process); CLI ops < 2s
**Constraints**: Layer rules enforced (doctrine ⊄ charter, charter ⊄ specify_cli, kernel ⊄ doctrine); ruff + mypy --strict clean, zero new suppressions; complexity ≤ 15
**Scale/Scope**: 4 issues, ~9 source files touched, 5 rosters consolidated, 1 new doctrine exception, 1 CLI wiring, 1 CI gate

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Charter principle | Applies how | Status |
|-------------------|-------------|--------|
| Single canonical authority / unification-not-parity | The whole #2669 thrust: one accessor, true derivation, no keep-the-literal+guard (except the operator-confirmed migration live-read, C-004). No no-canonical-field fallback (C-001). | PASS (by design) |
| Architectural alignment / layer rules | New accessor lives in doctrine (the legal `charter → doctrine` direction); charter never imports specify_cli; kernel never imports doctrine (NFR-006). | PASS (by design) |
| DDD + tiered rigour | Core doctrine/charter logic (accessor, fail-loud loader, scan wiring) gets full rigour + focused tests; the pure accessor-promotion refactor (#2668) is behavior-preserving. | PASS |
| ATDD-first | Each WP commits a failing-first test through the pre-existing entry point before implementation (C-008). | PASS (enforced per-WP) |
| Terminology adherence | "Mission" not "feature"; run the terminology guard pre-push (C-006). | PASS |
| Architectural gate discipline | #2666 adds a non-vacuous runtime + CI enforcer for FR-013 (was pytest-only); #2667 removes the swallow that made it partially vacuous. | PASS (the mission's point) |
| Mission tracer files | Seed 3 tracers at planning; append during implement; assess at close. | PASS (seeded this phase) |

No conflicts with the charter. No charter gates violated.

## Implementation Concern Map

Decomposes the mission into IC-## concerns. The `/spec-kitty.tasks` phase turns these into work packages.
Delivery order is **correctness-bearing** (C-002): IC-1 → IC-2 → IC-3 → IC-4.

### IC-1 — Single-source mission-type accessor + roster derivation (#2669)

- **IC-1a (enabler, doctrine layer):** Introduce ONE canonical accessor next to `MissionTypeRepository`
  (doctrine layer) — a cached function returning the built-in mission-type ids in an **ordered** form
  (sorted) plus a **frozenset** convenience. Wraps `MissionTypeRepository.default().ids()`. `@functools.cache`
  so ≤1 filesystem scan per process (NFR-002). Doctrine must not import charter — safe, it's the source.
- **IC-1b (charter rosters):** Derive Roster A `CANONICAL_MISSION_TYPES` and Roster B
  `_BUILTIN_MISSION_TYPE_IDS` from the accessor. B preserves frozenset semantics. Charter consumers call
  the accessor **lazily inside functions** (function-local import, existing `# noqa: PLC0415` convention) —
  **zero import-time filesystem I/O** (NFR-001). Audit-confirm no order-dependent consumer of A.
- **IC-1c (extra charter rosters, folded in):** Derive Roster D `ALLOWED_MISSION_TYPES` (union `{any, generic}`
  sentinels) and Roster E `_MISSION_IDENTIFIER_ANSWERS` (preserve `software_dev` underscore-alias transform).
- **IC-1d (migration, live-read):** Roster C `_BUILTIN_MISSION_TYPES` resolves from
  `MissionTypeRepository.default().ids()` at `apply()` time (call-time). C-004 trade-off recorded in the
  design-decisions tracer.
- **Tests:** single-source guard (add a synthetic type → universal pickup, SC-001); import-time-I/O guard
  (SC-005); frozenset-semantics preserved; migration derivation; sentinel/alias preservation.

### IC-2 — `load_action_index` fails loud (#2667)  *(before IC-3)*

- Add co-located `ActionIndexError(ValueError)` in `action_index.py`; message names index path + offending
  key + found type (mirrors `MissionTypeRepository._load` phrasing).
- Raise on present-but-invalid: non-mapping root, non-list artifact-kind field, unparseable YAML. Missing
  file → keep silent fallback; intentionally-empty-but-well-formed → empty content, no raise (FR-007/008).
- **Blast radius:** sole src caller `aggregate_action_grain` (no try/except) → propagates to scan/resolver/doctor.
- **Tests:** re-pin the 2 lenient tests in `test_action_index.py` to `pytest.raises` (stale-contract re-pin,
  not deletion); add explicit missing-file-stays-fallback + empty-well-formed-index tests.

### IC-3 — Wire the FR-013 scan loud outside pytest (#2666)  *(depends on IC-2 for non-vacuity)*

- Wire `scan_builtin_cross_grain_duplicates` into `doctrine_check()` (`doctor.py`): call before computing
  `exit_code`, catch `CrossGrainDoubleDeclarationError`, fold into `report.healthy`/RC=1 and `--json`
  (template: `_render_unsanctioned_override_findings`). Re-add the symbol to `__all__` in `action_grain.py`
  (justified by the new src caller — C-003, must land together).
- Add a CI structural gate asserting built-in cross-grain disjointness independent of the broad run; keep
  `tests/doctrine/drg/test_cross_grain_integrity.py` as the structural home.
- **Tests:** CLI test (`doctor doctrine` JSON shape + RC=1 on a synthetic collision); the dead-symbol gate
  (`test_no_dead_symbols.py`, arch_shard_1) auto-verifies the `__all__` re-add once the caller exists.

### IC-4 — Promote built-in-root accessor (#2668, campsite, last)

- Promote `MissionTypeProfileRepository._default_built_in_dir` → public `builtin_missions_root()`
  (module-level function; classmethod delegates). Drop the 2 `# noqa: SLF001` bypasses (`action_grain.py`,
  `mission_type_profiles.py`). Pure refactor; only `MissionTypeProfileRepository` (C-005). Lands last to
  absorb churn on the two shared lines IC-1/IC-3 also touch.
- **Tests:** `builtin_missions_root()` returns `src/doctrine/missions`; no behavior change.

## Project Structure

### Documentation (this mission)

```
kitty-specs/mission-type-single-source-gate-wiring-01KXKHVZ/
├── plan.md              # This file
├── spec.md              # Committed (30b8ab3)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
├── issue-matrix.md      # Mission hygiene (authored)
├── traces/              # 3 tracer files (seeded this phase)
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT this command)
```

### Source Code (repository root) — files this mission touches

```
src/
├── doctrine/missions/
│   ├── mission_type_repository.py      # IC-1a: home of the new canonical accessor
│   └── action_index.py                 # IC-2: ActionIndexError + fail-loud
├── charter/
│   ├── mission_type_profiles.py        # IC-1b (Roster A) + IC-4 (drop SLF001)
│   ├── pack_context.py                 # IC-1b (Roster B, frozenset)
│   ├── activations.py                  # IC-1c (Roster D + sentinels)
│   ├── synthesizer/interview_mapping.py# IC-1c (Roster E + alias)
│   ├── action_grain.py                 # IC-3 (__all__ re-add) + IC-4 (drop SLF001)
│   └── mission_type_profile_repository.py # IC-4: promote builtin_missions_root()
└── specify_cli/
    ├── upgrade/migrations/m_3_2_0rc35_activate_builtin_mission_types.py  # IC-1d (live-read)
    └── cli/commands/doctor.py          # IC-3: doctrine_check wiring

tests/
├── doctrine/missions/test_action_index.py     # IC-2 re-pin + new
├── doctrine/drg/test_cross_grain_integrity.py # IC-3 structural gate
├── charter/                                    # IC-1 roster + accessor tests
├── upgrade/test_activate_builtin_types_migration.py  # IC-1d
├── specify_cli/cli/commands/                   # IC-3 doctor CLI test
└── architectural/test_no_dead_symbols.py       # IC-3 __all__ gate (auto)
```

## Phase 0 — Research

See [research.md](./research.md). The design is locked; research consolidates the confirmed decisions
(accessor seam + layer, exception shape, doctor wiring point, migration live-read trade-off) and the
squad-verified facts (consumer inventory, blast radius, CI-gate coupling) rather than resolving open
unknowns. No `[NEEDS CLARIFICATION]` markers remain.

## Phase 1 — Design & Contracts

- [data-model.md](./data-model.md) — the accessor's return contracts, `ActionIndex`/`ActionIndexError`
  shapes, doctrine-health finding shape.
- [contracts/](./contracts/) — the accessor contract, the fail-loud loader contract, the `doctor doctrine`
  integrity-check contract.
- [quickstart.md](./quickstart.md) — how to verify each of the four outcomes locally.

## Complexity Tracking

No charter gate violations; no complexity deviations requested. All touched functions kept ≤ 15
(NFR-005); repeated literals hoisted to module constants (Sonar S1192).
