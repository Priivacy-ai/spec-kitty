# WP03 Review Cycle 1 — Changes Required

**Reviewer**: reviewer-renata (claude:sonnet-4-6)
**Date**: 2026-05-31

## Summary

The implementation is functionally correct and all 24 unit tests pass. However, there is one **blocking** issue that must be fixed before approval: the architectural dead-symbol gate (`test_no_dead_symbols.py`) fails because `charter.invocation_context::ProjectContext` and `charter.invocation_context::ContextPreconditionError` are declared in `__all__` but have no live caller in `src/`.

---

## BLOCKING Issue: Dead-symbol gate failure

**Test that fails**: `tests/architectural/test_no_dead_symbols.py::test_no_public_symbol_in_all_is_unimported`

**Symptoms**:
```
charter.invocation_context::ContextPreconditionError
charter.invocation_context::ProjectContext
```
Both symbols are in `__all__` but have zero `import` occurrences in `src/`. The dead-symbol scanner requires every `__all__` export to have at least one caller in `src/` (or be in the allowlist).

**Root cause**: The WP spec stated `ProjectContext` would not need allowlisting because downstream WPs (WP04–WP09) will add callers. However, those WPs haven't been implemented yet, so the dead-symbol gate fires on this branch right now.

**Required fix** (choose one):

### Option A (preferred by spec, lower risk at merge time): Add both symbols to the allowlist

In `tests/architectural/test_no_dead_symbols.py`, extend `_CATEGORY_C_WP_IN_FLIGHT_CHARTER_SCOPE` to include the two missing symbols. Update `_baselines.yaml` to bump `category_c_wp_in_flight_charter_scope` from `4` to `6`.

Change:
```python
_CATEGORY_C_WP_IN_FLIGHT_CHARTER_SCOPE: frozenset[str] = frozenset(
    {
        "charter.invocation_context::OperationalContext",
        "charter.invocation_context::build_operational_context",
        "charter.invocation_context::OperationalContext.require_active_profile",
        "charter.invocation_context::OperationalContext.require_active_role",
    }
)
```

To:
```python
_CATEGORY_C_WP_IN_FLIGHT_CHARTER_SCOPE: frozenset[str] = frozenset(
    {
        "charter.invocation_context::OperationalContext",
        "charter.invocation_context::build_operational_context",
        "charter.invocation_context::OperationalContext.require_active_profile",
        "charter.invocation_context::OperationalContext.require_active_role",
        # ProjectContext and ContextPreconditionError have no src/ caller yet;
        # callers will be added by WP04–WP09 (charter-pack-activation-layer).
        "charter.invocation_context::ProjectContext",
        "charter.invocation_context::ContextPreconditionError",
    }
)
```

And in `tests/architectural/_baselines.yaml`:
```yaml
  category_c_wp_in_flight_charter_scope: 6  # justification: OperationalContext family + ProjectContext/ContextPreconditionError specced, wiring deferred (charter-pack-activation-layer WP03/WP04-09)
```

### Option B: Re-export through `charter/__init__.py`

If `charter/__init__.py` already imports `ProjectContext` and `ContextPreconditionError` (making them live), verify this is sufficient for the dead-symbol scanner. If not, Option A is the cleaner path.

---

## Non-blocking observations (informational only, do not block)

1. **Pre-existing test failures**: `test_no_dead_symbols.py` has pre-existing failures on the base branch unrelated to WP03 (e.g., `specify_cli.charter_activate::*`, `doctrine.missions.mission_step_repository::*`). The WP03 contribution adds two new failures on top of the pre-existing ones. The fix above addresses only the WP03-introduced failures.

2. **mypy errors**: The 6 `import-untyped` errors for `jsonschema` stubs are pre-existing across the codebase and unrelated to this WP. `src/charter/invocation_context.py` itself has zero mypy errors.

3. **ruff**: All checks pass (`All checks passed!`).

4. **Unit tests**: All 24 tests pass (`24 passed in 0.22s`).

5. **No specify_cli imports**: Confirmed clean.

6. **`_baselines.yaml` ratchet meta-test**: Passes.

---

## Validation commands after fix

```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty/.worktrees/charter-pack-activation-layer-01KSYE4V-lane-c

# Must pass (currently fails — 2 new dead symbols introduced)
python -m pytest tests/architectural/test_no_dead_symbols.py -x -q 2>&1 | tail -10

# Must still pass
python -m pytest tests/charter/test_invocation_context.py -x -v 2>&1 | tail -5
python -m pytest tests/architectural/test_ratchet_baselines.py -x -q 2>&1 | tail -5
```
