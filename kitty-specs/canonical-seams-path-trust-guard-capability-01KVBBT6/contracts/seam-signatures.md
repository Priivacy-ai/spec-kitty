# Contracts — Seam Signatures & CI Invariant

## Goal A — canonical safe-segment validator (`core/paths.py`)
```python
def assert_safe_path_segment(value: str) -> str:
    """Return `value` if it is a single safe path segment; else raise ValueError.

    Rejects: empty/whitespace-only, ".", "..", any "/" or "\\", and any value that is
    not a single path segment under the reconciled grammar. The grammar MUST admit every
    real-format value (full 26-char ULID, "<slug>-<mid8>" dir names, numeric-prefix slugs,
    bare mid8) — proven by the NFR-006 union test — while preserving the traversal guard.
    """
```
- **Callers (validation now inherited):** `primary_feature_dir_for_mission` and `resolve_mission_read_path`
  (`missions/_read_path_resolver.py`) call it before composing `KITTY_SPECS_DIR/<value>`.
- **Delegation (FR-002):** `merge.py::_validate_mission_slug_path_segment` → delegate (keep `ValueError`);
  `coordination/transaction.py::_validate_safe_segment` → delegate, re-wrap as `BookkeepingError` at the call site;
  `status/aggregate.py::_validate_mission_slug` → delegate (keep `InvalidMissionSlug(ValueError)`).

## Goal B — parameterized containment (`core/utils.py`)
```python
def ensure_within_any(path: Path, *, roots: Sequence[Path], files: Sequence[Path] = ()) -> Path:
    """Return path.resolve(strict=False) if it is under any of `roots` OR equals an allowed
    exact file in `files`; else raise ValueError. (Multi-root sibling of ensure_within_directory.)"""
```
- **Delegation (FR-006):** `_assert_status_path_within_target_surface` → `ensure_within_any(roots=[surface_root])`;
  `_assert_bookkeeping_snapshot_path_is_trusted` → `ensure_within_any(roots=[...3 dirs], files=[.kittify/merge-state.json])`.
- **Preserved (NOT collapsed):** `_assert_status_surface_path_is_trusted` selects its single root via
  `is_under_worktrees_segment` (worktrees XOR kitty-specs), THEN delegates — no union-widening.

## Goal C — CI gate invariant (`.github/workflows/ci-quality.yml`)
```
INVARIANT: the `integration-tests-core-misc (architectural)` shard runs the FULL `tests/architectural/**`
suite whenever ANY guarded write-side surface OR an architectural guard's scan-root/allow-list changes.
IMPLEMENTATION: add `src/specify_cli/status/**`, `src/specify_cli/coordination/**`,
`src/specify_cli/core/worktree.py` to the `core_misc` path filter (~:174).
META-TEST: assert (by reading the workflow) that each guarded surface is in a filter that triggers the
architectural shard — keyed on filter-name + path-glob membership, NOT line numbers.
```

## Ratchet re-key contract (`tests/architectural/test_no_worktree_name_guess.py`)
- Allow-list entries are keyed by `(<enclosing-function-qualname>, <normalized-token-line>)` composites (reuse
  `test_no_write_side_rederivation.py`'s token machinery), NOT `file:lineno`.
- A +1-line-drift test proves a semantic-neutral edit does not flip the ratchet.
- `test_no_write_side_rederivation._ALLOW_LIST` (`status_transition.py:295`) is OUT of scope (C-007 / #1716).
