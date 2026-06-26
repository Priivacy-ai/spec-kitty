# Tasks: Retire mission_read_path Backcompat Shim

**Mission**: `retire-mission-read-path-shim-01KVZNDS`
**Planning base branch**: `feat/retire-mission-read-path-shim`
**Final merge target**: `main` (via PR from the feature branch)
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md)

## Overview

A single atomic work package. The change retires the dead `specify_cli.mission_read_path` shim and
restores the SHRINK ratchet. IC-01 (repoint + delete) and IC-02 (ratchet) are **deliberately not
split** into separate WPs: the dead-module gate fails if the allowlist entry is removed while the
module still exists, and `test_ratchet_baselines.py` fails if the baseline count drifts from the live
frozenset size (C-001). The whole set is consistent only when applied together, so it lands as one
reviewable, atomic unit.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Repoint the 7 shim imports in `test_coord_reader_fixes.py` to the canonical resolver (alias the private worker) | WP01 | |
| T002 | Delete `src/specify_cli/mission_read_path.py` | WP01 | |
| T003 | Drop `"specify_cli.mission_read_path"` from `_CATEGORY_4_BACKCOMPAT_SHIMS` (`test_no_dead_modules.py`) | WP01 | |
| T004 | Drop `"specify_cli.mission_read_path::resolve_mission_read_path"` from `_CATEGORY_C_BACKCOMPAT_SHIM_REEXPORT` (`test_no_dead_symbols.py`) | WP01 | |
| T005 | Decrement `category_4_backcompat_shims: 9 → 8` in `_baselines.yaml` with a `# justification:` comment | WP01 | |
| T006 | Tidy the stale shim docstring in `test_single_mission_surface_resolver.py` | WP01 | |
| T007 | Verify: architectural suite + repointed tests + `ruff` + `mypy` all green | WP01 | |

## Work Packages

### WP01 — Retire the shim and restore the ratchet

- **Goal**: Delete the dead `specify_cli.mission_read_path` module, re-point its only real importer to
  the canonical seam, drop its two architectural allowlist entries, and reverse the
  `category_4_backcompat_shims` ratchet bump (9 → 8) — leaving the full test suite green with no
  production behavior change.
- **Priority**: P1 (the whole mission)
- **Dependencies**: none
- **Prompt**: [tasks/WP01-retire-shim-restore-ratchet.md](./tasks/WP01-retire-shim-restore-ratchet.md)
- **Estimated prompt size**: ~300 lines (7 subtasks)
- **Independent test**: `PWHEADLESS=1 pytest tests/architectural/ tests/specify_cli/cli/commands/test_coord_reader_fixes.py -q` passes; `grep -rn "specify_cli.mission_read_path" src/` returns zero matches; `category_4_backcompat_shims` resolves to 8.

**Included subtasks**:

- [x] T001 Repoint the 7 shim imports in `test_coord_reader_fixes.py` to `specify_cli.missions._read_path_resolver`, aliasing `_resolve_mission_read_path as resolve_mission_read_path` (WP01)
- [x] T002 Delete `src/specify_cli/mission_read_path.py` (WP01)
- [x] T003 Drop `"specify_cli.mission_read_path"` from `_CATEGORY_4_BACKCOMPAT_SHIMS` in `tests/architectural/test_no_dead_modules.py` (WP01)
- [x] T004 Drop `"specify_cli.mission_read_path::resolve_mission_read_path"` from `_CATEGORY_C_BACKCOMPAT_SHIM_REEXPORT` in `tests/architectural/test_no_dead_symbols.py` (WP01)
- [x] T005 Decrement `category_4_backcompat_shims: 9 → 8` in `tests/architectural/_baselines.yaml` with a `# justification:` comment (WP01)
- [x] T006 Tidy the stale shim docstring (~line 100) in `tests/architectural/test_single_mission_surface_resolver.py` (WP01)
- [x] T007 Verify: run `pytest tests/architectural/`, the repointed test file, `ruff check .`, and `mypy src/specify_cli`; confirm all green and the `src/` grep is clean (WP01)

**Implementation sketch**:
1. Repoint imports first (T001) so no commit references a missing module.
2. Delete the module (T002).
3. Drop both allowlist entries and decrement the baseline together (T003–T005).
4. Tidy the docstring (T006).
5. Verify the whole suite + gates (T007).

**Parallel opportunities**: none — single atomic unit.

**Risks**:
- Importing the privatized worker by the wrong name. The canonical module exposes `_resolve_mission_read_path` (private); import it aliased to `resolve_mission_read_path` (C-002). There is NO public `resolve_mission_read_path` on the canonical module.
- Baseline off-by-one (C-001): the declared count must equal the live frozenset size after removal (8).
- Touching files that should stay unchanged (C-003): files importing from the canonical resolver, or asserting only the symbol-name string, must NOT be edited.

## Requirement coverage

All FRs map to WP01 (FR-001 … FR-007). NFR-001…004 and C-001…004 are verified by T007 and the
constraints baked into the WP prompt.
