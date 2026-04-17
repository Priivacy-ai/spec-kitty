# C-1 — Charter Public Import Surface (baseline preservation)

**Kind**: Import API contract
**Covers**: FR-007, NFR-005, SC-002

## Statement

For every symbol reachable through `from specify_cli.charter import X` or `from specify_cli.charter.submodule import Y` at the **pre-mission baseline** (v3.1.5 / v3.1.6), the following MUST remain true after this mission merges:

1. The same import resolves successfully (possibly with a `DeprecationWarning`).
2. The resolved object `is` the same object reachable via the canonical `from charter.… import …` path, i.e., `specify_cli.charter.X is charter.X` for re-exports, or the two import forms return callables that satisfy the same behavioral tests.

## Machine-enforced assertion

A test under `tests/specify_cli/charter/test_import_surface_preservation.py` iterates a frozen baseline list of known public import paths and verifies each resolves. The baseline is computed once during implementation by inspecting `src/specify_cli/charter/__init__.py` and the three `sys.modules`-aliased submodules (`compiler`, `interview`, `resolver`).

```python
LEGACY_IMPORTS: list[tuple[str, str]] = [
    # (legacy_path, canonical_path)
    ("specify_cli.charter", "charter"),
    ("specify_cli.charter.compiler", "charter.compiler"),
    ("specify_cli.charter.interview", "charter.interview"),
    ("specify_cli.charter.resolver", "charter.resolver"),
    # + each public symbol re-exported from __init__.py, frozen at mission time
]

for legacy, canonical in LEGACY_IMPORTS:
    with pytest.warns(DeprecationWarning, match="specify_cli.charter"):
        legacy_obj = importlib.import_module(legacy)
    canonical_obj = importlib.import_module(canonical)
    assert legacy_obj is canonical_obj
```

## Non-contract

- New symbols added to `src/charter/*` after this mission are NOT required to be re-exported through the legacy surface.
- Internal (underscore-prefixed) names under `src/charter/` are NOT part of the contract.

## Breakage response

Any test failure in `test_import_surface_preservation.py` is a P0 for the mission — it means a known legacy caller will break without warning. Remediation is to restore the re-export (add it to the shim `__init__.py` or confirm the `sys.modules` alias); never remove the failing line from the baseline list.
