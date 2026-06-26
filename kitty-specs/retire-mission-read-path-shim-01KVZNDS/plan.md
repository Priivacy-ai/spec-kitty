# Implementation Plan: Retire mission_read_path Backcompat Shim

**Branch**: `feat/retire-mission-read-path-shim` | **Date**: 2026-06-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/retire-mission-read-path-shim-01KVZNDS/spec.md`

## Summary

Retire the dead `specify_cli.mission_read_path` backcompat shim. The last production importer was
already re-pointed to the canonical seam by mission 01KVJPEQ, leaving the module with zero `src/`
callers but a `8→9` SHRINK-ratchet bump to keep it passing the dead-module gate. The technical
approach is a pure deletion-and-repoint: re-point the only real importer (7 sites in one test
file) to `specify_cli.missions._read_path_resolver`, delete the module, remove its two
architectural allowlist entries, decrement the baseline `9→8` with a justification comment, and
tidy one stale docstring. No production behavior changes.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pytest (architectural gate suite), ruff, mypy — no new runtime dependencies
**Storage**: N/A (no data layer touched)
**Testing**: pytest; the authoritative gates are `tests/architectural/test_no_dead_modules.py`, `test_no_dead_symbols.py`, and `test_ratchet_baselines.py`; behavioral coverage of the resolver lives in `tests/specify_cli/cli/commands/test_coord_reader_fixes.py`
**Target Platform**: Linux/macOS developer + CI environments
**Project Type**: single (Python CLI package `specify_cli`)
**Performance Goals**: N/A — no hot path affected
**Constraints**: Zero supported-canonical-consumer runtime behavior change (NFR-002); baseline count MUST exactly match live frozenset size (C-001); `_baselines.yaml` edit MUST carry a `# justification:` comment (C-004)
**Scale/Scope**: 7 source/test/ratchet files (1 deletion, 1 test repoint, 2 allowlist edits, 1 baseline edit, 2 prose/allowlist tidies) plus mission artifacts documenting the backcompat decision

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter present at `.kittify/charter/charter.md`. Relevant gates:

- **Burn-down Policy (C-004) / SHRINK ratchet** — This mission *advances* the policy (restores the
  downward trend by decrementing `category_4_backcompat_shims`); fully compliant. ✅
- **`__all__` Declaration Convention (C-007)** — `_resolve_mission_read_path` remains private and
  absent from `_read_path_resolver.__all__`; white-box tests alias the private worker locally, while
  supported callers use `resolve_handle_to_read_path` / `resolve_feature_dir_for_mission`. No
  `__all__` regression. ✅
- **ATDD-First (C-011)** — The acceptance gate is the existing architectural suite; the change is
  validated by making `pytest tests/architectural/` pass with count = 8. No new product behavior to
  test-drive; existing behavioral tests are preserved via repoint (NFR-003). ✅
- **DIR-003 (tracker ticket assignment)** — For fresh tracker-backed implementation, issue #2048
  should be assigned to the HiC before work begins. Assignment must be verified from the tracker and
  is not inferred from this artifact. ⚠️
- **Identifier Safety (DIR-001/002)** — No slug/identifier normalization touched. N/A.

No violations. No Complexity Tracking entries required.

## Project Structure

### Documentation (this mission)

```
kitty-specs/retire-mission-read-path-shim-01KVZNDS/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (minimal — no data entities)
├── quickstart.md        # Phase 1 output (verification recipe)
└── spec.md              # Mission specification
```

### Source Code (repository root)

```
src/specify_cli/
├── mission_read_path.py                 # DELETE (the shim)
└── missions/
    └── _read_path_resolver.py           # canonical seam (unchanged; importers repoint here)

tests/
├── architectural/
│   ├── _baselines.yaml                  # category_4_backcompat_shims: 9 → 8 (+ justification)
│   ├── test_no_dead_modules.py          # drop "specify_cli.mission_read_path" from _CATEGORY_4_BACKCOMPAT_SHIMS
│   ├── test_no_dead_symbols.py          # drop "...::resolve_mission_read_path" from _CATEGORY_C_BACKCOMPAT_SHIM_REEXPORT
│   └── test_single_mission_surface_resolver.py  # tidy stale docstring (cosmetic, FR-007)
└── specify_cli/cli/commands/
    └── test_coord_reader_fixes.py        # repoint 7 imports to specify_cli.missions._read_path_resolver
```

**Structure Decision**: Single Python package. All edits are localized to the shim module, one
test file that imports it, and the three architectural-gate files that allowlist/count it. Files
that import the symbol from the canonical resolver, or only assert the symbol-name string in
production source, are explicitly left untouched (C-003).

## Complexity Tracking

*No Charter Check violations — section intentionally empty.*

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Repoint and delete the shim

- **Purpose**: Remove the dead module without breaking its remaining importer, so the canonical
  seam is the single entry point.
- **Relevant requirements**: FR-002, FR-003, NFR-002, NFR-003, C-002, C-003
- **Affected surfaces**: `src/specify_cli/mission_read_path.py` (delete), `tests/specify_cli/cli/commands/test_coord_reader_fixes.py` (repoint 7 imports — including the `_COMPAT_ATTRS` error-contract names where imported, to the canonical `specify_cli.missions._read_path_resolver`)
- **Sequencing/depends-on**: Repoint imports first (or atomically with the delete) so no test references a missing module at any commit.
- **Risks**: Importing the privatized worker name by mistake — must import the public re-export `resolve_mission_read_path`, not `_resolve_mission_read_path` (C-002). Verify the error-contract names (`STATUS_READ_PATH_NOT_FOUND_CODE`, `StatusReadPathNotFound`) are reachable from the canonical resolver if the test imports them.

### IC-02 — Restore the architectural ratchet

- **Purpose**: Drop the now-obsolete allowlist exemptions and reverse the baseline bump so the
  SHRINK ratchet validates downward.
- **Relevant requirements**: FR-004, FR-005, FR-006, FR-007, NFR-001, C-001, C-004
- **Affected surfaces**: `tests/architectural/test_no_dead_modules.py`, `tests/architectural/test_no_dead_symbols.py`, `tests/architectural/_baselines.yaml`, `tests/architectural/test_single_mission_surface_resolver.py` (docstring)
- **Sequencing/depends-on**: Must land together with IC-01 in the same change — the dead-module gate fails if the allowlist entry is removed while the module still exists, and the ratchet test fails if the baseline count drifts from the live frozenset size (C-001).
- **Risks**: Off-by-one between the declared baseline (8) and the actual frozenset count after removal; the `# justification:` comment must be present per the `_baselines.yaml` edit policy (C-004).
