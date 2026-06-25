# Mission Specification: Retire mission_read_path Backcompat Shim

**Mission**: `retire-mission-read-path-shim-01KVZNDS`
**Type**: software-dev
**Status**: Draft
**Source**: [GitHub issue #2048](https://github.com/Priivacy-ai/spec-kitty/issues/2048) — "Retire dead backcompat shim: specify_cli.mission_read_path (01KVJPEQ follow-up)"

## Purpose

Mission 01KVJPEQ re-pointed the last production importer (`runtime/next/runtime_bridge.py`)
off the `specify_cli.mission_read_path` backcompat shim and onto the canonical
`resolve_handle_to_read_path` seam. That left the shim with **zero `src/` callers**, but the
same mission bumped the SHRINK ratchet for backcompat shims from 8 to 9 to keep the now-orphaned
module passing the architectural gate. This mission retires the dead shim and reverses that bump,
restoring the ratchet's intended downward trend.

## Domain Language

| Term | Meaning |
|------|---------|
| **Shim** | `src/specify_cli/mission_read_path.py` — a backward-compatibility module that re-exports the canonical worker `_resolve_mission_read_path` under its historical public name `resolve_mission_read_path`. |
| **Canonical seam** | `specify_cli.missions._read_path_resolver` — the authoritative home of the read-path resolution logic. |
| **SHRINK ratchet** | The architectural baseline policy in `tests/architectural/_baselines.yaml` where each category count is only ever allowed to decrease (per Slice F C-004 burn-down policy). |
| **Allowlist entry** | A frozenset member in an architectural test that exempts a specific dead module/symbol from failing the dead-code gate. |

## User Scenarios & Testing

### Primary scenario

**Actor**: Maintainer running the architectural test suite after the shim is retired.
**Trigger**: `pytest tests/architectural/` is executed on the feature branch.
**Success outcome**: The suite passes, including `test_ratchet_baselines.py`, with
`category_4_backcompat_shims` at 8 — proving the shim is gone, its allowlist exemptions are
removed, and the ratchet trend is restored downward.

### Acceptance scenarios

1. **Given** the shim module has been deleted, **when** the full test suite runs, **then** no
   test fails on a missing-import or missing-module error (every former importer resolves the
   symbol from the canonical seam instead).
2. **Given** the two allowlist entries have been removed, **when** `test_no_dead_modules.py` and
   `test_no_dead_symbols.py` run, **then** they pass without reporting an unexpected dead module
   or an orphaned allowlist entry.
3. **Given** `_baselines.yaml` is decremented to 8, **when** `test_ratchet_baselines.py` runs,
   **then** the count matches the live frozenset size and the ratchet validates (no GROW
   violation).
4. **Given** a developer greps `src/` for `specify_cli.mission_read_path`, **when** the mission is
   complete, **then** only zero results are returned (no production code references the retired
   module path).

### Edge cases

- A test file imports `resolve_mission_read_path` from the **canonical** resolver, not the shim
  (e.g. `tests/integration/test_cli_status_mediation.py`): such files MUST remain unchanged.
- A test asserts only the **string** `resolve_mission_read_path` appears in a production file
  (e.g. `tests/specify_cli/regression/test_issue_1615_1616_1617_1618.py`): the canonical symbol
  name is unchanged, so these assertions MUST continue to pass without edits.
- A docstring or comment in a test references the shim as a historical debt source (e.g.
  `tests/architectural/test_single_mission_surface_resolver.py`): such stale prose SHOULD be
  tidied for accuracy but is non-blocking.

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The external/back-compat consumer question for `specify_cli.mission_read_path` is resolved as "safe to delete": the module path is internal, undocumented as public API, and has zero in-repo `src/` callers; external direct-importers are treated as unsupported. | Confirmed |
| FR-002 | The module `src/specify_cli/mission_read_path.py` is deleted from the repository. | Pending |
| FR-003 | Every test import of `from specify_cli.mission_read_path import resolve_mission_read_path` (and the `_COMPAT_ATTRS` error-contract names, if imported) is re-pointed to `specify_cli.missions._read_path_resolver`, importing the private worker `_resolve_mission_read_path` under the local test alias `resolve_mission_read_path`. | Pending |
| FR-004 | The entry `"specify_cli.mission_read_path"` is removed from `_CATEGORY_4_BACKCOMPAT_SHIMS` in `tests/architectural/test_no_dead_modules.py`. | Pending |
| FR-005 | The entry `"specify_cli.mission_read_path::resolve_mission_read_path"` is removed from `_CATEGORY_C_BACKCOMPAT_SHIM_REEXPORT` in `tests/architectural/test_no_dead_symbols.py`. | Pending |
| FR-006 | `category_4_backcompat_shims` in `tests/architectural/_baselines.yaml` is decremented from 9 to 8, with a `# justification:` comment per the file's edit policy (lines 11–17). | Pending |
| FR-007 | Stale prose in `tests/architectural/test_single_mission_surface_resolver.py` that names the retired shim as a live debt source is updated to reflect its removal. | Pending |

### Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | The full architectural test suite passes after the change. | `pytest tests/architectural/` exits 0, including `test_ratchet_baselines.py`, `test_no_dead_modules.py`, `test_no_dead_symbols.py`. | Pending |
| NFR-002 | No production runtime behavior changes for supported canonical consumers. | Zero edits to any file under `src/` other than deleting the shim module; no `src/` import of the retired path remains (grep returns 0 matches). The unsupported old import path intentionally no longer imports. | Pending |
| NFR-003 | Repointed test files retain their original assertions and coverage. | The 7 import sites in `test_coord_reader_fixes.py` execute the same `resolve_mission_read_path` behavior via the canonical seam; the file's test count is unchanged and all pass. | Pending |
| NFR-004 | Lint and type gates stay green. | `ruff check .` and `mypy` report zero new issues on the diff. | Pending |

### Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | The baseline decrement MUST exactly match the live frozenset size (8). The ratchet test cross-checks the declared count against the actual allowlist contents; a mismatch fails the gate. | Active |
| C-002 | The canonical worker is privatized as `_resolve_mission_read_path` and dropped from the resolver's `__all__`; repointed white-box tests MAY import that private worker under the local alias `resolve_mission_read_path`, while supported production callers MUST use public seams such as `resolve_handle_to_read_path` or `resolve_feature_dir_for_mission`. | Active |
| C-003 | Files that already import from the canonical resolver, or that only assert the symbol-name string in production source, MUST NOT be modified. | Active |
| C-004 | Per `_baselines.yaml` edit policy, the PR diff touching that file MUST carry a `# justification:` comment explaining why the decrement is safe. | Active |

## Success Criteria

1. `grep -rn "specify_cli.mission_read_path" src/` returns zero matches (the production module path is fully retired).
2. `pytest tests/architectural/` passes with `category_4_backcompat_shims` resolving to 8.
3. The full project test suite (`pytest tests/`) shows no new failures attributable to the shim removal.
4. `ruff check .` and `mypy` are clean on the diff.
5. The PR closes issue #2048 and unblocks the #2049 immediate burn-down step.

## Key Entities

- **`mission_read_path.py`** — the shim module being deleted (re-exports `resolve_mission_read_path` plus `_COMPAT_ATTRS` error-contract names via `__getattr__`).
- **`_read_path_resolver.py`** — the canonical resolver module; public callers use its public seams, while low-level white-box tests may alias `_resolve_mission_read_path`.
- **`_baselines.yaml`** — the architectural ratchet baseline ledger.
- **`test_no_dead_modules.py` / `test_no_dead_symbols.py`** — the dead-code gates holding the allowlist entries to remove.

## Assumptions

- No external/downstream package imports `specify_cli.mission_read_path` as a supported public API (confirmed safe-to-delete decision, FR-001). If any external consumer is later discovered, it must migrate to the canonical seam.
- The canonical `resolve_mission_read_path` re-export and its behavior are unchanged by this mission; only the redundant shim entry point is removed.

## Out of Scope

- The broader allowlist burn-down audit across all categories (`category_7_grandfathered_orphans`, `category_b_grandfathered_legacy`, `legacy_contract_allowlist`, etc.) — that is tracked by sister issue #2049.
- Any change to the read-path resolution logic itself.
