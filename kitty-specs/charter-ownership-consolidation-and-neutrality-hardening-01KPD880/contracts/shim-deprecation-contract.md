# C-2 — Shim Deprecation Warning Contract

**Kind**: Runtime warning contract
**Covers**: FR-005, NFR-004, SC-006

## Statement

Importing *any* module under the legacy `specify_cli.charter.*` path MUST raise a single `DeprecationWarning` with the properties below. The warning is emitted from the **package `__init__.py` only**; submodule shims (`compiler.py`, `interview.py`, `resolver.py`) stay silent because Python evaluates the parent package's `__init__.py` on the way to resolving any submodule, so a single warning site is sufficient — and emitting per-submodule would produce a cascade of duplicate warnings for the common `from specify_cli.charter.compiler import X` pattern.

### Warning properties

1. `category` is exactly `DeprecationWarning` (not `FutureWarning`, `UserWarning`, `PendingDeprecationWarning`, etc.).
2. `message` (string form) contains all three of:
   - The canonical replacement package name (`charter`).
   - The legacy path being deprecated (`specify_cli.charter`).
   - The target removal release (e.g., `3.3.0`).
3. The warning is raised **once** per Python process under the default warning filter — repeated imports in the same process do not re-warn, because the package `__init__.py` body executes only on first import.
4. `stacklevel=2` — the warning's reported location points at the *caller* (the file doing the import), not at `specify_cli/charter/__init__.py` itself.
5. Module-level metadata attributes on the package (`__deprecated__`, `__canonical_import__`, `__removal_release__`, `__deprecation_message__`) are present on `specify_cli.charter` and match the warning text (cross-validated).

### Why package-only, not per-submodule

If every submodule shim also called `warnings.warn`, the common import idiom

```python
from specify_cli.charter.compiler import X
```

would trigger two warnings (one when Python evaluates `specify_cli/charter/__init__.py` during package initialization, one when the submodule shim body runs). That would be:

- noisy for callers who can only act on one signal,
- test-hostile (the test cannot meaningfully assert "exactly N warnings" across all N import shapes),
- and redundant (the package-level warning already names every submodule's canonical replacement).

The contract is therefore: the package speaks; submodules remain silent.

## Machine-enforced assertion

Test under `tests/specify_cli/charter/test_shim_deprecation.py`:

```python
import importlib, sys, warnings
import pytest

LEGACY_IMPORT_SHAPES = [
    "specify_cli.charter",
    "specify_cli.charter.compiler",
    "specify_cli.charter.interview",
    "specify_cli.charter.resolver",
]

def _reset_modules():
    for m in list(sys.modules):
        if m.startswith("specify_cli.charter") or m == "charter" or m.startswith("charter."):
            sys.modules.pop(m, None)

@pytest.mark.parametrize("module_path", LEGACY_IMPORT_SHAPES)
def test_legacy_import_emits_deprecation_warning(module_path):
    _reset_modules()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        importlib.import_module(module_path)
    depr = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert len(depr) >= 1, (
        f"Importing {module_path} produced zero DeprecationWarnings; "
        f"expected at least one from the specify_cli.charter package __init__."
    )
    # The package-level warning is the one we mandate. Other libraries may emit
    # their own unrelated DeprecationWarnings during import; we only require that
    # ours fires, not that it is the only one.
    ours = [w for w in depr if "specify_cli.charter" in str(w.message)]
    assert ours, f"No DeprecationWarning mentioning 'specify_cli.charter' was emitted."
    assert len(ours) == 1, (
        f"Expected exactly one specify_cli.charter DeprecationWarning across "
        f"all import shapes; got {len(ours)}. Submodule shims must not re-warn."
    )
    msg = str(ours[0].message)
    assert "charter" in msg
    assert "specify_cli.charter" in msg
    assert "3.3.0" in msg                                   # removal release

def test_package_carries_deprecation_metadata():
    _reset_modules()
    pkg = importlib.import_module("specify_cli.charter")
    assert getattr(pkg, "__deprecated__", False) is True
    assert pkg.__canonical_import__ == "charter"
    assert pkg.__removal_release__ == "3.3.0"
    assert "specify_cli.charter" in pkg.__deprecation_message__
    assert pkg.__removal_release__ in pkg.__deprecation_message__
```

## Non-contract

- External callers that explicitly suppress `DeprecationWarning` via `warnings.filterwarnings("ignore", category=DeprecationWarning)` before import will not see the warning — that is standard Python behavior and not a failure of this contract.
- Submodule shims (`compiler.py`, `interview.py`, `resolver.py`) are permitted to carry `__deprecated__` / `__canonical_import__` attributes for documentation, but they MUST NOT call `warnings.warn` themselves.
- The **content** of `__canonical_import__` / `__removal_release__` is authored on the package `__init__.py` in this mission; future missions may update the removal release across the package atomically.

## Breakage response

If the package fails to emit the warning (forgotten during a refactor, filter re-enabled, stacklevel broken), the parametrized test fails with a message naming the offending import shape. Fix is always in `src/specify_cli/charter/__init__.py`, never in the test. If a submodule shim starts emitting its own DeprecationWarning (reintroducing the duplicate-warning bug), the `len(ours) == 1` assertion will catch it.
