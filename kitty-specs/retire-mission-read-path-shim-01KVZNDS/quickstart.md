# Quickstart / Verification: Retire mission_read_path Backcompat Shim

A reviewer or implementer can verify the mission end-to-end with these steps. No API contracts
exist (no `contracts/` directory) — this is an internal code-retirement mission.

## Preconditions

- On branch `feat/retire-mission-read-path-shim` (or its execution worktree).
- For a fresh tracker-backed implementation, assign issue #2048 to the HiC per DIR-003 before work begins; reviewers should verify the live tracker state instead of treating this artifact as assignment evidence.

## The change (what the implementer does)

1. **Repoint** the 7 import sites in `tests/specify_cli/cli/commands/test_coord_reader_fixes.py`:
   ```python
   from specify_cli.missions._read_path_resolver import (
       StatusReadPathNotFound,                                 # only where the test imports it
       _resolve_mission_read_path as resolve_mission_read_path,
   )
   ```
   (Single-symbol sites that only import `resolve_mission_read_path` become
   `from specify_cli.missions._read_path_resolver import _resolve_mission_read_path as resolve_mission_read_path`.)
2. **Delete** `src/specify_cli/mission_read_path.py`.
3. **Drop** `"specify_cli.mission_read_path"` from `_CATEGORY_4_BACKCOMPAT_SHIMS` in
   `tests/architectural/test_no_dead_modules.py`.
4. **Drop** `"specify_cli.mission_read_path::resolve_mission_read_path"` from
   `_CATEGORY_C_BACKCOMPAT_SHIM_REEXPORT` in `tests/architectural/test_no_dead_symbols.py`.
5. **Decrement** `category_4_backcompat_shims: 9 → 8` in `tests/architectural/_baselines.yaml`,
   adding a `# justification:` comment (per the file's edit policy, lines 11–17), e.g.
   `# justification: #2048 retired dead shim specify_cli.mission_read_path (zero src callers); reverses the 01KVJPEQ 8→9 bump.`
6. **Tidy** the stale docstring in `tests/architectural/test_single_mission_surface_resolver.py`
   (~line 100) that names the shim as a live debt source.

## Verification commands

```bash
# 1. No production reference to the retired module path remains (expect zero matches):
grep -rn "specify_cli.mission_read_path" src/

# 2. The module is gone:
test ! -f src/specify_cli/mission_read_path.py && echo "shim deleted OK"

# 3. The architectural gate passes with the restored ratchet:
PWHEADLESS=1 pytest tests/architectural/test_no_dead_modules.py \
                    tests/architectural/test_no_dead_symbols.py \
                    tests/architectural/test_ratchet_baselines.py -q

# 4. The repointed behavioral tests still pass:
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/test_coord_reader_fixes.py -q

# 5. Full architectural suite + lint/type gates:
PWHEADLESS=1 pytest tests/architectural/ -q
ruff check .
mypy src/specify_cli
```

## Pass criteria (maps to Success Criteria)

- `grep` in step 1 returns **0** matches. (SC-1, NFR-002)
- Step 3 passes; `category_4_backcompat_shims` resolves to **8**. (SC-2, FR-006, C-001)
- Step 4 passes with unchanged test count. (NFR-003)
- Step 5 is fully green. (SC-3, SC-4, NFR-001, NFR-004)

## Terminal-state expectation

The PR (feat → main) closes #2048 and unblocks the #2049 immediate burn-down step.
