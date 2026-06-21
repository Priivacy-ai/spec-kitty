# Quickstart: Verifying the Strangler-Finish

The differential equivalence gate is the deletion-safety net. Verification is "does it read 31/0 with the
invariants intact?"

## The one command that proves the collapse

```bash
.venv/bin/python -m pytest tests/missions/test_surface_resolution_equivalence.py -p no:cacheprovider -q
# Before:  27 passed, 6 xfailed
# After IC-01: 29 passed, 4 xfailed   (read-path mid8 cells drained)
# After IC-04: coord-empty cells drained
# After IC-05: 31 passed, 0 xfailed   (coord-deleted cells drained)
```

A strict-xfail that XPASSes is a failure — so the gate proves each cell drains exactly when its WP lands.

## Per-invariant checks

- **INV-1 (create-window → primary):** the existing create-window equivalence cells + regression tests stay
  green; no new hard-fail in that state.
- **INV-2 (coord-deleted hard-fail):** all three legs raise `CoordinationBranchDeleted`
  (`COORDINATION_BRANCH_DELETED`); the read-path leg uses the `_coord_branch_exists` discriminator.
- **INV-3 (loud warning):** a focused test asserts the coord-empty fallback emits the warning (caplog /
  captured stderr) naming both recovery commands.
- **INV-4 (zero callers):** `grep -rn "resolve_mission_read_path\b" src/ | grep -v "_resolve_mission_read_path\|resolve_handle_to_read_path"` returns nothing outside the defining module.
- **INV-5 (gate not weakened):** the equivalence test still asserts `type(a) is type(b)` and equal
  `error_code`; only `_XFAIL_*` allowlist constants shrink.

## Full safety sweep before merge

```bash
.venv/bin/python -m pytest tests/missions/test_surface_resolution_equivalence.py \
  tests/architectural/test_single_mission_surface_resolver.py \
  tests/architectural/ -p no:cacheprovider -q
.venv/bin/ruff check . && .venv/bin/mypy src/specify_cli/missions/_read_path_resolver.py \
  src/specify_cli/coordination/surface_resolver.py src/specify_cli/status/aggregate.py
# Public-contract migration (IC-05): the agent status CLI tests for coord-empty/coord-deleted must be green.
```
