---
work_package_id: WP04
title: Shim Deprecation Signaling
dependencies: []
requirement_refs:
- C-005
- FR-004
- FR-005
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts were generated on main; completed changes must merge back into main.
subtasks:
- T014
- T015
- T016
- T017
phase: Phase 1 — Foundational
assignee: ''
agent: ''
history:
- timestamp: '2026-04-17T09:03:02Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/charter/__init__.py
execution_mode: code_change
owned_files:
- src/specify_cli/charter/__init__.py
- tests/specify_cli/charter/test_shim_deprecation.py
tags: []
---

# Work Package Prompt: WP04 – Shim Deprecation Signaling

## Objective

Install the single `DeprecationWarning` + metadata contract on the legacy `specify_cli.charter` **package `__init__.py`**. Submodule shims stay silent. Add the test that asserts the contract and verify the three intentional C-005 compatibility tests still pass.

## Context

Contract: `contracts/shim-deprecation-contract.md` (C-2). Key shape: **package speaks, submodules stay silent.** The reasoning is detailed in the contract — per-submodule warnings double-fire on common `from specify_cli.charter.X import Y` imports because Python evaluates the parent `__init__.py` on the way to resolving any submodule.

Submodule shims currently use `sys.modules[__name__] = sys.modules["charter.X"]` aliasing. They may carry informational `__deprecated__ = True` and `__canonical_import__` attributes for documentation, but MUST NOT call `warnings.warn` themselves.

Three intentional C-005 compatibility tests exist and MUST continue to pass unchanged:

- `tests/specify_cli/charter/test_defaults_unit.py`
- `tests/charter/test_sync_paths.py`
- `tests/charter/test_chokepoint_coverage.py`

These are occurrence-map exceptions (see `occurrence_map.yaml` — `do_not_change`) and they are the deliberate proof that the deprecation window works.

## Branch Strategy

Planning base branch is `main`; merge target is `main`. Execution worktree path is resolved by the runtime from `lanes.json`.

## Implementation Sketch

### Subtask T014 — Edit `src/specify_cli/charter/__init__.py`

Current state: 108 lines of pure re-exports from `charter.*`.

Add at the very top (after the module docstring, before any re-export `from charter... import ...`):

```python
"""Deprecated legacy import surface for charter services.

Import from ``charter`` instead. This package is scheduled for removal in
release 3.3.0; see CHANGELOG.md and docs/migration/charter-ownership-consolidation.md.
"""

import warnings as _warnings

__deprecated__ = True
__canonical_import__ = "charter"
__removal_release__ = "3.3.0"
__deprecation_message__ = (
    "specify_cli.charter is deprecated; import from 'charter' instead. "
    "Scheduled removal: 3.3.0."
)

_warnings.warn(__deprecation_message__, DeprecationWarning, stacklevel=2)

# Existing re-exports follow unchanged.
...
```

Notes:

- Prefix the `warnings` import with `_` so the name does not leak into the package's public re-export surface.
- `stacklevel=2` is required — the warning should point at the *caller* (the file issuing the import), not at this `__init__.py`.
- The warning fires on first import of the package; subsequent imports in the same Python process will not re-warn, because the package body executes exactly once.
- Do NOT guard the warning with `if not __deprecated_warned__:` or similar — Python's `__init__.py` caching already provides the once-per-process semantics.
- Keep every existing re-export exactly as it is today. This WP adds the warning; it does not refactor the re-export list.

### Subtask T015 — Verify submodule shims stay silent

Inspect `src/specify_cli/charter/compiler.py`, `interview.py`, `resolver.py`. Current content (baseline): each is 9 lines using `sys.modules[__name__] = sys.modules["charter.X"]`. None currently calls `warnings.warn`.

**Required action**: confirm these files do NOT call `warnings.warn` and do not gain one during this WP. If you find one (added in a merge conflict, for example), remove it. The package-level warning is the sole warning site per C-2.

**Permitted**: adding module-level `__deprecated__ = True` and `__canonical_import__ = "charter.<submod>"` constants to each submodule shim for reader clarity. These are informational; they do not emit anything. Keep them optional — prefer leaving the submodule shims untouched unless a review explicitly asks for the attributes.

The guard in WP05 will enforce that these three files remain small and shim-shaped.

### Subtask T016 — Author `tests/specify_cli/charter/test_shim_deprecation.py`

Follow contract C-2's "Machine-enforced assertion" verbatim:

```python
"""Assert the package-level DeprecationWarning contract on specify_cli.charter.

Contract: kitty-specs/charter-ownership-consolidation-and-neutrality-hardening-01KPD880/
         contracts/shim-deprecation-contract.md (C-2)
"""

from __future__ import annotations

import importlib
import sys
import warnings

import pytest

LEGACY_IMPORT_SHAPES = [
    "specify_cli.charter",
    "specify_cli.charter.compiler",
    "specify_cli.charter.interview",
    "specify_cli.charter.resolver",
]


def _reset_modules() -> None:
    for m in list(sys.modules):
        if m.startswith("specify_cli.charter") or m == "charter" or m.startswith("charter."):
            sys.modules.pop(m, None)


@pytest.mark.parametrize("module_path", LEGACY_IMPORT_SHAPES)
def test_legacy_import_emits_deprecation_warning(module_path: str) -> None:
    _reset_modules()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        importlib.import_module(module_path)
    depr = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert depr, (
        f"Importing {module_path} produced zero DeprecationWarnings; "
        f"expected at least one from the specify_cli.charter package __init__."
    )
    ours = [w for w in depr if "specify_cli.charter" in str(w.message)]
    assert ours, "No DeprecationWarning mentioning 'specify_cli.charter' was emitted."
    assert len(ours) == 1, (
        f"Expected exactly one specify_cli.charter DeprecationWarning; got {len(ours)}. "
        f"Submodule shims must not re-warn."
    )
    msg = str(ours[0].message)
    assert "charter" in msg
    assert "specify_cli.charter" in msg
    assert "3.3.0" in msg


def test_package_carries_deprecation_metadata() -> None:
    _reset_modules()
    pkg = importlib.import_module("specify_cli.charter")
    assert getattr(pkg, "__deprecated__", False) is True
    assert pkg.__canonical_import__ == "charter"
    assert pkg.__removal_release__ == "3.3.0"
    assert "specify_cli.charter" in pkg.__deprecation_message__
    assert pkg.__removal_release__ in pkg.__deprecation_message__
```

The `len(ours) == 1` assertion is load-bearing: it catches any regression that reintroduces per-submodule warnings.

Type-annotate every helper. `mypy --strict` must pass.

### Subtask T017 — Re-run C-005 compatibility tests

From the worktree root:

```bash
pytest tests/specify_cli/charter/test_defaults_unit.py \
       tests/charter/test_sync_paths.py \
       tests/charter/test_chokepoint_coverage.py -v
```

Expected: **all pass**. They will emit `DeprecationWarning` (that's the point), and they use `pytest.warns` or simply suppress warnings — either way, the shim still returns the correct symbol.

If any of these three tests fail, the fix is in the shim implementation, not in these tests. They are the guarantee C-005 is honored.

## Files

- **Edited**: `src/specify_cli/charter/__init__.py` (add ~15 lines at top).
- **New**: `tests/specify_cli/charter/test_shim_deprecation.py` (~80 lines).

## Definition of Done

- [ ] `src/specify_cli/charter/__init__.py` declares `__deprecated__`, `__canonical_import__`, `__removal_release__`, `__deprecation_message__` and calls `warnings.warn(...)` exactly once.
- [ ] No `warnings.warn` calls in `compiler.py`, `interview.py`, or `resolver.py`.
- [ ] `tests/specify_cli/charter/test_shim_deprecation.py` passes all 5 parametrized cases + the metadata test.
- [ ] The three C-005 compatibility tests still pass unchanged.
- [ ] `mypy --strict` passes on the edited `__init__.py` and new test file.
- [ ] Re-exports in `__init__.py` are byte-identical to baseline below the warning block.

## Risks

- **Warning filter interference**: if pytest's default warning filter is too aggressive, the `catch_warnings` block in T016 may not see the warning. Use `warnings.simplefilter("always", DeprecationWarning)` inside the block as the code above shows.
- **Stacklevel drift**: setting `stacklevel` wrong (0 or 1) points the warning at the `__init__.py` itself, which is not useful for callers. `stacklevel=2` is correct.
- **Removal release drift**: `3.3.0` is the coordinated value with CHANGELOG.md and migration guide. If project versioning policy changes between this WP and WP07, the test's `assert "3.3.0" in msg` needs coordinated updates across all three artifacts. WP07 cross-validates.
- **Submodule shim regression**: a well-meaning contributor might add `warnings.warn` to `compiler.py` "to be safe". The `len(ours) == 1` assertion catches it. WP05's guard is the longer-term safety net.

## Reviewer Checklist

- [ ] Exactly one `warnings.warn` call in the package `__init__.py`, at the top before re-exports.
- [ ] `stacklevel=2`, category is `DeprecationWarning` literal (not a subclass).
- [ ] All 4 metadata attributes present with the exact values spec'd above.
- [ ] `compiler.py`, `interview.py`, `resolver.py` contain zero `warnings.warn` calls.
- [ ] The test asserts both `>= 1` warning emitted AND `== 1` warning mentioning `specify_cli.charter`.
- [ ] The three C-005 tests still pass.
