# Contract — `doctor doctrine` cross-grain integrity check (IC-3 / #2666)

**Location:** `src/specify_cli/cli/commands/doctor.py` (`doctrine_check`), consuming
`charter.action_grain.scan_builtin_cross_grain_duplicates`.

## Behavior

1. `doctrine_check` calls `scan_builtin_cross_grain_duplicates()` before computing the exit code.
2. On `CrossGrainDoubleDeclarationError`:
   - the doctrine report is marked **unhealthy**;
   - the command exits **RC=1**;
   - `--json` output carries a structured finding (mission type + colliding artifact URN);
   - human output renders a loud finding (mirroring `_render_unsanctioned_override_findings`).
3. On success: the check contributes a healthy result; exit code unchanged.

## `__all__` coupling (C-003)

`scan_builtin_cross_grain_duplicates` is re-added to `__all__` in `src/charter/action_grain.py` in the SAME
change as this wiring — the CI dead-symbol gate
(`tests/architectural/test_no_dead_symbols.py::test_no_public_symbol_in_all_is_unimported`, arch_shard_1)
only passes once a real `src/` importer exists.

## CI structural gate (FR-011)

A structural test asserts the built-in tree is cross-grain-disjoint, independent of the broad pytest run.
`tests/doctrine/drg/test_cross_grain_integrity.py` remains the structural home.

## Scope boundary

Built-in tree only. Project/org override collision coverage is a tracked follow-up (blocked on the
multi-root action-index engine `action_grain.py` declares out of scope).

## Test obligations

- CLI test: `doctor doctrine --json` shape + RC=1 on a synthetic collision (constructed via
  `MissionTypeProfileRepository(built_in_dir=tmp)` as the integrity-gate twin does).
- Dead-symbol gate auto-verifies the `__all__` re-add.
