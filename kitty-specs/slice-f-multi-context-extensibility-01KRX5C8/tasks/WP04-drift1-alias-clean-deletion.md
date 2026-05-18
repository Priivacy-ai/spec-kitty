---
work_package_id: WP04
title: DRIFT-1 alias clean deletion + tests migration + ImportError regression test
dependencies: []
requirement_refs:
- C-003
- FR-100
- FR-101
- FR-102
- FR-103
- NFR-005
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
- T021
agent: claude:opus-4-7:python-pedro:implementer
history: []
agent_profile: python-pedro
authoritative_surface: src/charter/resolver.py
execution_mode: code_change
owned_files:
- src/charter/resolver.py
- src/charter/__init__.py
- tests/charter/test_resolver.py
- tests/charter/test_alias_deleted_regression.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Scope governance context to Python implementation before reading anything else.

---

## Objective

Per **HiC §5a.1 (binding, C-003)** — clean removal, no `DeprecationWarning`, no sunset docstring. DELETE the `resolve_governance = resolve_project_governance` alias from `src/charter/resolver.py` and its export from `src/charter/__init__.py`. Migrate every test fixture using the legacy name to import the canonical `resolve_project_governance`. Land a regression test asserting `from charter import resolve_governance` raises `ImportError`.

The architect's full-monty rationale (HiC verbatim in C-003): preventing "confusing paths in place". User impact is structurally limited (Assumption 4 — no out-of-tree consumers).

---

## Context

DRIFT-1 from the architect's post-Mission-B debrief: `resolve_governance` was introduced as a transitional alias during Mission B's resolver split. The HiC adjudicated on 2026-05-18 that the alias must be deleted in this mission rather than carried forward — Slice F already touches the charter/doctrine layer extensively, so the cleanup lands here cleanly.

Verbatim HiC rationale (C-003):

> "Do it now, if possible. The 3.2.0 scope will include various changes to the charter/doctrine [layer] already, it seems best to go full monty, rather than leaving confusing paths in place. Our overuse of 'eventual deprecation' and shimming has bit us before, lets avoid that and do the move cleanly. User impact is limited anyway, as most of the internal system is a black-box for them."

Specific source locations from the debrief audit:

- `src/charter/resolver.py:325-326` — the alias assignment itself
- `src/charter/resolver.py:198` — the "Deprecated alias" docstring
- `src/charter/__init__.py:73` — `resolve_governance` in the import block
- `src/charter/__init__.py:124` — `resolve_governance` in `__all__`
- `tests/charter/test_resolver.py:14` — test fixture importing the legacy name

References:
- [spec.md §"Scenario 4 — DRIFT-1 alias removal"](../spec.md)
- [spec.md §"Absorbed remediation — DRIFT-1 alias clean removal"](../spec.md)
- [plan.md §1.4](../plan.md)
- [atdd-coverage.md Scenario 4, AC-5](../atdd-coverage.md)

**Lane B is independent of Lane A** — WP04 can start at mission claim. It can also serialise behind Lane A if the reviewer prefers; the lane graph is intentionally permissive.

**Coordination with WP02:** WP02 introduces `__all__` declarations on every `src/charter/` module including `__init__.py`. The order of operations:

- If WP02 lands first: `__init__.py::__all__` already includes `resolve_governance`; WP04 removes the alias AND removes the entry from `__all__`.
- If WP04 lands first: WP04 removes the alias from the `from .resolver import (...)` block and from any existing `__all__`; WP02 then adds explicit `__all__` declarations to OTHER charter modules (resolver/context/schemas/etc.) without re-adding `resolve_governance`.

Either order works; the final state is the same.

---

## ATDD Discipline

Per **C-011** WP04 is a lane-opening WP for Lane B and lands its failing-first test as its FIRST commit:

1. **Commit A (RED, T017):** `tests/charter/test_alias_deleted_regression.py` asserts `from charter import resolve_governance` raises `ImportError`. On the planning base this test FAILS because the alias still exists. Commit message: `covers: Scenario 4, AC-5 — expected GREEN at: WP04 final commit`.
2. **Commits B..D (GREEN progression, T018-T021):** delete the alias, prune exports, migrate fixtures, add AC-5 coverage assertion.

ATDD anchors per [atdd-coverage.md](../atdd-coverage.md):
- Scenario 4: `tests/charter/test_alias_deleted_regression.py::test_resolve_governance_import_raises_import_error`
- AC-5: same test + `test_no_test_fixture_still_imports_legacy_alias`

---

## Subtasks

### T017 — Land failing-first `tests/charter/test_alias_deleted_regression.py`

**File:** `tests/charter/test_alias_deleted_regression.py` (new)

```python
"""DRIFT-1 alias deletion regression (FR-103, AC-5).

Per HiC §5a.1 (C-003), the resolve_governance alias is DELETED in this
mission. This test asserts the deletion holds: importing the legacy name
must raise ImportError. There is no DeprecationWarning, no sunset
docstring -- clean removal.
"""
from __future__ import annotations

import importlib
import pathlib
import subprocess
import sys

import pytest


def test_resolve_governance_import_raises_import_error() -> None:
    """The alias is gone; importing it must fail with ImportError."""
    with pytest.raises(ImportError):
        from charter import resolve_governance  # noqa: F401


def test_resolver_module_does_not_define_alias() -> None:
    """Defensive: even direct module access must not yield the alias."""
    from charter import resolver
    assert not hasattr(resolver, "resolve_governance"), (
        "resolve_governance alias is meant to be DELETED per HiC §5a.1 (C-003); "
        "found it still defined in charter.resolver. "
        "Clean removal — no shim, no DeprecationWarning."
    )


def test_no_test_fixture_still_imports_legacy_alias() -> None:
    """Guard the migration: no test file should still reference the legacy name."""
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["rg", "-l", r"resolve_governance", str(repo_root / "tests"), str(repo_root / "src")],
        capture_output=True, text=True,
    )
    # Only this test file (the regression) should reference the legacy name
    offenders = [
        line for line in result.stdout.splitlines()
        if not line.endswith("test_alias_deleted_regression.py")
    ]
    assert not offenders, (
        "Files still reference legacy `resolve_governance`:\n  " + "\n  ".join(offenders)
    )
```

**Validation:** `pytest tests/charter/test_alias_deleted_regression.py -v` MUST FAIL on planning base. All three tests fail — the import succeeds (alias exists), the attribute exists, and `rg` finds offending references. Commit RED.

### T018 — DELETE the alias

**File:** `src/charter/resolver.py`

Delete lines 325-326 (the `resolve_governance = resolve_project_governance` assignment). Delete the "Deprecated alias" docstring at line 198 (or wherever the docstring currently resides). Verify with `rg "resolve_governance" src/charter/resolver.py` — should return 0 matches.

**Edge case:** if the docstring is interleaved with other comment blocks (e.g. one big module-level docstring section), remove only the alias-related lines.

### T019 — Remove from `__init__.py` exports

**File:** `src/charter/__init__.py`

- Remove `resolve_governance` from the `from .resolver import (...)` block (line 73 per the audit).
- Remove `resolve_governance` from `__all__` (line 124 per the audit).

Verify with `rg "resolve_governance" src/charter/__init__.py` — should return 0 matches.

### T020 — Migrate test fixtures to canonical name

**Files:** `tests/charter/test_resolver.py` (audit-identified) + any others surfaced by `rg "resolve_governance" tests/`

For each offender:

```python
# BEFORE
from charter import resolve_governance
governance = resolve_governance(repo_root, feature_dir)

# AFTER
from charter import resolve_project_governance
governance = resolve_project_governance(repo_root, feature_dir)
```

Run `rg "resolve_governance" tests/` after the migration. Only `tests/charter/test_alias_deleted_regression.py` (the regression test itself) should remain — it intentionally references the legacy name in its `pytest.raises(ImportError)` block.

### T021 — Confirm AC-5 GREEN; run regression suite

After T018-T020, run:

```bash
pytest tests/charter/test_alias_deleted_regression.py -v
# EXPECTED: all three tests GREEN

pytest tests/charter/ -v
# EXPECTED: full charter test suite GREEN (migrated fixtures still pass with canonical name)

PWHEADLESS=1 pytest tests/architectural/ -v
# EXPECTED: full architectural sweep exit 0 (NFR-005)
```

If WP02 has already merged, also run:

```bash
pytest tests/architectural/test_all_declarations_required.py tests/architectural/test_no_dead_symbols.py -v
# EXPECTED: GREEN -- removing the alias does not break the __all__ convention
```

---

## Definition of Done

The following tests turn GREEN with this WP:

- ✅ `tests/charter/test_alias_deleted_regression.py::test_resolve_governance_import_raises_import_error` (was RED on planning base)
- ✅ `tests/charter/test_alias_deleted_regression.py::test_resolver_module_does_not_define_alias` (was RED on planning base)
- ✅ `tests/charter/test_alias_deleted_regression.py::test_no_test_fixture_still_imports_legacy_alias` (was RED on planning base)
- ✅ `tests/charter/test_resolver.py` — all fixtures migrated; full suite GREEN
- ✅ `PWHEADLESS=1 pytest tests/architectural/ -v` exit 0 (NFR-005)

FR coverage:

- ✅ FR-100 — alias DELETED in `src/charter/resolver.py`
- ✅ FR-101 — export removed from `src/charter/__init__.py`
- ✅ FR-102 — all test fixtures migrated to canonical `resolve_project_governance`
- ✅ FR-103 — `from charter import resolve_governance` raises `ImportError`, asserted by regression test
- ✅ C-003 — HiC §5a.1 honoured: no `DeprecationWarning`, no sunset docstring

AC coverage:

- ✅ AC-5 — alias is DELETED; ImportError on import; no fixture still uses legacy name

---

## Risks

1. **An out-of-tree consumer imports `resolve_governance`** — would break. Mitigation: Assumption 4 documents no out-of-tree consumers exist; HiC §5a.1 accepted user impact. Internal-only API.
2. **`rg` is not installed on a contributor's machine** (T017's `test_no_test_fixture_still_imports_legacy_alias`). Mitigation: skip the test with `pytest.importorskip` if `rg` missing, OR rewrite using `pathlib.Path.rglob` + `read_text()` (preferred). Use the pure-Python implementation to keep CI portable.
3. **WP02 lands after WP04 and re-introduces `resolve_governance` in some `__all__` declaration** by accident. Mitigation: WP02's review checklist explicitly verifies `resolve_governance` does NOT appear in any new `__all__`. The regression test catches it if it slips through.
4. **A site uses `getattr(charter, "resolve_governance")` dynamically** — not caught by static `rg`. Mitigation: T017's `test_resolver_module_does_not_define_alias` exercises `hasattr(charter.resolver, "resolve_governance")` directly. Any dynamic site that depends on the alias will fail at runtime with `AttributeError`.
5. **An IDE auto-import config lingers and re-suggests `resolve_governance`** to future contributors. Mitigation: the `__init__.py::__all__` change removes the name from `from charter import *` and from IDE auto-import suggestions sourced from `__all__`.

---

## Reviewer Guidance

**ATDD red→green verification (mandatory per C-011):**

```bash
# 1. RED on planning base:
git checkout feat/org-doctrine-layer
pytest tests/charter/test_alias_deleted_regression.py -v
# EXPECTED: all three tests FAIL (alias still exists, attribute present, rg finds offenders)

# 2. GREEN on WP final commit:
git checkout <wp_branch>
pytest tests/charter/test_alias_deleted_regression.py -v
# EXPECTED: exit 0
```

**Substantive review checks:**

- Confirm `src/charter/resolver.py` no longer contains `resolve_governance` (verify by `rg "resolve_governance" src/charter/resolver.py` — empty result).
- Confirm `src/charter/__init__.py` no longer imports or exports `resolve_governance`.
- Confirm `tests/` no longer references `resolve_governance` outside the regression test file.
- Confirm NO `DeprecationWarning` or sunset docstring was added anywhere (C-003 binding — clean removal, not deprecation). Reject if any deprecation shim slipped in.
- Confirm `tests/charter/test_resolver.py` was migrated (not just patched with a try/except shim).
- Confirm full charter test suite passes: `pytest tests/charter/ -v` exit 0.
- Confirm full architectural sweep: `PWHEADLESS=1 pytest tests/architectural/ -v` exit 0 (NFR-005).

**FR-304 commit-message check:** T017 RED commit cites `covers: Scenario 4, AC-5` and `expected GREEN at: WP04 final commit`. The alias deletion commit (T018-T019) cites `closes: FR-100, FR-101, C-003 (HiC §5a.1 binding)`.
