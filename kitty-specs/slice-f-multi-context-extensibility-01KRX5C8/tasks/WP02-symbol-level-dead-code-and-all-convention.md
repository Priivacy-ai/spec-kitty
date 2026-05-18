---
work_package_id: WP02
title: Symbol-level dead-code gate (`__all__` walk) + `__all__` on src/charter/ + src/kernel/
dependencies:
- WP01
requirement_refs:
- C-007
- FR-120
- FR-121
- FR-122
- NFR-005
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
- T012
agent: "claude:sonnet-4-6:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: tests/architectural/
execution_mode: code_change
owned_files:
- tests/architectural/test_no_dead_symbols.py
- tests/architectural/test_all_declarations_required.py
- src/charter/activations.py
- src/charter/_activation_render.py
- src/charter/bundle.py
- src/charter/catalog.py
- src/charter/compact.py
- src/charter/compiler.py
- src/charter/context_renderers/**
- src/charter/corpus/**
- src/charter/_diagnostics.py
- src/charter/_doctrine_paths.py
- src/charter/_drg_helpers.py
- src/charter/evidence/**
- src/charter/extractor.py
- src/charter/generator.py
- src/charter/hasher.py
- src/charter/interview.py
- src/charter/_io.py
- src/charter/language_scope.py
- src/charter/mission_steps.py
- src/charter/mission_type_profiles.py
- src/charter/neutrality/**
- src/charter/parser.py
- src/charter/primitives.py
- src/charter/profiles.py
- src/charter/reference_resolver.py
- src/charter/resolution.py
- src/charter/schemas.py
- src/charter/sync.py
- src/charter/synthesizer/**
- src/charter/template_resolver.py
- src/charter/versioning.py
- src/kernel/**
role: implementer
tags: []
shell_pid: "2249698"
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Scope your governance context to Python implementation. Required reading before touching any files.

---

## Objective

Extend the dead-code architectural ratchet from module-level to symbol-level: introduce `tests/architectural/test_no_dead_symbols.py` that walks every name declared in a module's `__all__` and asserts at least one `from <module> import <name>` site exists somewhere in `src/`. Require `__all__` on every module under `src/charter/` and `src/kernel/` so the walk has a closed set to traverse.

This closes the architect's MED-3 finding (a live module exposing a public class with zero callers is invisible to the existing file-level check — the failure mode that bit Mission B WP08 cycle-1).

---

## Context

`test_no_dead_modules` (lines 273-485 of the implementation) scans at file-level: a module passes if ANY OTHER `src/` file imports ANY name from it. A subtler failure mode — a public class declared in `__all__` with zero callers — slips past. The architect's MED-3 remediation: walk `__all__` if declared, and assert every name in `__all__` appears in another file's import.

Per **C-007** (binding via C-004), every module under `src/charter/` and `src/kernel/` MUST declare `__all__`. This bounded scope (charter + kernel only) proves the convention works at the two architectural boundary subpackages. Expansion to other subpackages is a future-mission concern (FR-121 explicit scope statement).

References:
- [spec.md §"Absorbed remediation — MED-3 symbol-level dead-code gate"](../spec.md)
- [plan.md §1.6](../plan.md)
- [atdd-coverage.md AC-8](../atdd-coverage.md)

**Ownership boundary note:** WP01 also modifies `tests/architectural/test_no_dead_modules.py` (the per-category refactor). This WP creates a NEW sibling test file `test_no_dead_symbols.py` rather than extending `test_no_dead_modules.py` to avoid file-level ownership collision with WP01. The two tests coexist; both must pass.

---

## ATDD Discipline

Per **C-011** WP02 lands two failing-first tests as its FIRST two commits:

1. **Commit A (RED, T008):** `tests/architectural/test_no_dead_symbols.py` — the `__all__` walk. On the planning base, this test fails because (a) `src/charter/` + `src/kernel/` modules lack `__all__` declarations, and (b) any pre-existing public symbol in `__all__` without a caller fails the assertion. Commit message: `covers: AC-8 — expected GREEN at: WP02 final commit`.
2. **Commit B (RED, T009):** `tests/architectural/test_all_declarations_required.py` — asserts every module under `src/charter/` and `src/kernel/` declares `__all__`. Fails on planning base because those modules don't yet declare it.
3. **Commits C..E (GREEN progression, T010-T012):** add `__all__` to charter modules, then kernel modules, then wire/remove any unimported public symbols.

ATDD anchor per [atdd-coverage.md](../atdd-coverage.md):
- AC-8: `test_every_charter_module_declares_all` AND `test_every_kernel_module_declares_all` AND `test_no_public_symbol_in_all_is_unimported`

---

## Subtasks

### T008 — Land failing-first `tests/architectural/test_no_dead_symbols.py`

**File:** `tests/architectural/test_no_dead_symbols.py` (new)

The test walks every module in `src/` and, when `__all__` is declared, asserts each name appears in at least one `from <module> import <name>` site in `src/` (excluding the declaring module itself).

```python
"""Symbol-level dead-code gate (FR-120).

Where module-level gates ensure every module has at least one importer,
this gate ensures every name in a module's `__all__` declaration has at
least one importer. A public class with zero callers — the failure mode
that bit Mission B WP08 cycle-1 — fails here.
"""
from __future__ import annotations

import ast
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"


def _modules_with_all_decl() -> dict[str, frozenset[str]]:
    """Walk src/, return {module_dotted_name: frozenset(__all__ names)}."""
    ...

def _all_imports_in_src() -> dict[str, set[str]]:
    """Walk src/, return {module_dotted_name: {imported_name, ...}} for every
    `from X import a, b` site."""
    ...

def test_no_public_symbol_in_all_is_unimported():
    decls = _modules_with_all_decl()
    imports = _all_imports_in_src()
    offenders: list[tuple[str, str]] = []
    for mod_name, names in decls.items():
        observed = imports.get(mod_name, set())
        for name in names:
            if name not in observed:
                offenders.append((mod_name, name))
    assert not offenders, (
        "Public symbols in __all__ with no caller in src/:\n  "
        + "\n  ".join(f"{m}::{n}" for m, n in offenders)
    )
```

**Validation:** `pytest tests/architectural/test_no_dead_symbols.py` MUST FAIL on planning base. Capture failing list (likely includes any orphaned charter/kernel public symbols).

### T009 — Land failing-first `tests/architectural/test_all_declarations_required.py`

**File:** `tests/architectural/test_all_declarations_required.py` (new)

```python
"""Convention gate: every module under src/charter/ and src/kernel/
MUST declare __all__ (C-007 binding via C-004 / FR-121)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"


def _modules_under(subpackage: str) -> list[Path]:
    root = SRC_ROOT / subpackage
    return [
        p for p in root.rglob("*.py")
        if p.name != "__init__.py" or True   # include __init__.py too
    ]


def _has_all_decl(path: Path) -> bool:
    tree = ast.parse(path.read_text())
    return any(
        isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets)
        for node in tree.body
    )


@pytest.mark.parametrize("path", _modules_under("charter"), ids=lambda p: str(p))
def test_every_charter_module_declares_all(path: Path) -> None:
    assert _has_all_decl(path), f"{path} missing __all__ declaration (C-007/FR-121)"


@pytest.mark.parametrize("path", _modules_under("kernel"), ids=lambda p: str(p))
def test_every_kernel_module_declares_all(path: Path) -> None:
    assert _has_all_decl(path), f"{path} missing __all__ declaration (C-007/FR-121)"
```

**Validation:** RED on planning base — most charter/kernel modules do not yet declare `__all__`. Commit RED.

Also update `tests/architectural/_baselines.yaml` (owned by WP01) is NOT touched here; WP02 only sets `charter_without_all` + `kernel_without_all` to a current count IF needed for ratcheting, but the preferred path is full migration so the baselines stay at 0. Coordinate with WP01 by editing `_baselines.yaml` ONLY if a deferred-migration entry surfaces; otherwise leave at 0.

### T010 — Add `__all__` to every module under `src/charter/`

**Files:** every `.py` under `src/charter/` (including `__init__.py`)

For each module, audit the module's public surface, then add an explicit `__all__` at the top of the module after imports:

```python
__all__ = [
    "OrgDRGFragment",
    "OrgDRGConflict",
    "load_org_drg",
    "merge_three_layers",
]
```

Rules:

- Include every name intended to be public (referenced from outside the module).
- Exclude names prefixed with `_` (private convention).
- Order alphabetically for review legibility.
- If a name is currently public but has no caller, decide: either remove (preferred) or document why it stays. The T012 gate enforces no orphan symbols.

Modules to update: enumerate via `rg --files src/charter/ -t py` and iterate. Likely includes `__init__.py`, `resolver.py`, `context.py`, `schemas.py`, `drg.py`, `activations.py`, `_catalog_miss.py`, and any others.

### T011 — Add `__all__` to every module under `src/kernel/`

**Files:** every `.py` under `src/kernel/`

Same procedure as T010. Audit `rg --files src/kernel/ -t py`; for each module declare `__all__` listing the public surface; exclude underscored names; alphabetise.

### T012 — Wire or remove unimported public symbols; both gates GREEN

After T010-T011, run T008's test (`test_no_dead_symbols.py`). For each remaining offender:

- **Preferred:** add a live caller in `src/` that imports the symbol.
- **Acceptable:** remove the symbol from `__all__` (it stays in the module as an unexported internal).
- **Acceptable:** delete the symbol entirely if truly dead.

Re-run:

```bash
pytest tests/architectural/test_no_dead_symbols.py tests/architectural/test_all_declarations_required.py -v
```

Both MUST be GREEN. Run full sweep:

```bash
PWHEADLESS=1 pytest tests/architectural/ -v
```

Exit 0 (NFR-005).

---

## Definition of Done

The following tests turn GREEN with this WP:

- ✅ `tests/architectural/test_no_dead_symbols.py::test_no_public_symbol_in_all_is_unimported` (was RED on planning base)
- ✅ `tests/architectural/test_all_declarations_required.py::test_every_charter_module_declares_all` (parameterised across every charter module)
- ✅ `tests/architectural/test_all_declarations_required.py::test_every_kernel_module_declares_all` (parameterised across every kernel module)
- ✅ Existing `tests/architectural/test_no_dead_modules.py` — coexists; both gates pass (FR-122)
- ✅ `PWHEADLESS=1 pytest tests/architectural/ -v` exit 0 (NFR-005)

FR coverage:

- ✅ FR-120 — `__all__` walk extends the module-level gate
- ✅ FR-121 — every module under `src/charter/` and `src/kernel/` declares `__all__`
- ✅ FR-122 — coexists with module-level gate; both must pass
- ✅ C-007 — convention is enforced; WP12 will pin it in the charter

AC coverage:

- ✅ AC-8 — symbol-level dead-code gate passes; every charter + kernel module declares `__all__`

---

## Risks

1. **A module's `__all__` declaration accidentally widens the public surface** (a previously-private name gets exported). Mitigation: T010-T011 explicitly enumerate intentional public surface; reviewer checks each module's `__all__` against actual external callers (`rg "from charter.X import"` per module).
2. **`ast.parse` misses dynamically-set `__all__`** (e.g. `__all__ = list(...)` computed at import time). Mitigation: T009's `_has_all_decl` walks for any `ast.Assign` targeting `__all__`, including computed values — assignment presence is the contract, not literal content.
3. **An existing module re-exports symbols from a sibling and the sibling has them in `__all__`** — the re-export site counts as a caller. Mitigation: T008's `_all_imports_in_src` captures `from sibling import name` regardless of where the import lands; re-exports count.
4. **Adding `__all__` to `__init__.py` changes `from charter import *` semantics for downstream consumers** (Slice F isn't `import *`-heavy, but defensive). Mitigation: each `__init__.py`'s `__all__` MUST contain every name currently re-exported by the file; reviewer verifies via `rg "from charter import" src/ tests/`.
5. **WP04 deletes the `resolve_governance` alias from `src/charter/__init__.py::__all__`** — overlap of intent. Mitigation: WP02 lands `__all__` containing all CURRENT exports; WP04 removes `resolve_governance` from that `__all__` as part of its alias deletion. No file ownership collision because WP04 owns `src/charter/__init__.py` for the alias removal; WP02 owns the `__all__` introduction for other charter modules. Sequence: WP02 adds `__all__` (including `resolve_governance` initially); WP04 then deletes the alias and the corresponding `__all__` entry.

---

## Reviewer Guidance

**ATDD red→green verification (mandatory per C-011):**

```bash
# 1. RED on planning base:
git checkout feat/org-doctrine-layer
pytest tests/architectural/test_no_dead_symbols.py tests/architectural/test_all_declarations_required.py -v
# EXPECTED: failures (no __all__ declarations yet)

# 2. GREEN on WP final commit:
git checkout <wp_branch>
pytest tests/architectural/test_no_dead_symbols.py tests/architectural/test_all_declarations_required.py -v
# EXPECTED: exit 0
```

**Substantive review checks:**

- Walk every `__all__` declaration in `src/charter/**` and `src/kernel/**` — confirm names are intentionally public and ordered alphabetically.
- Confirm no symbol in any `__all__` is referenced only by the declaring module's own tests (the test-file callers should NOT count — `_all_imports_in_src` walks `src/` only). The reviewer can spot-check by running `rg "from charter\.X import <name>" src/` per public symbol.
- Confirm WP01's `_ALLOWLIST` refactor in `test_no_dead_modules.py` is untouched by this WP (file-level coordination).
- Confirm full architectural sweep: `PWHEADLESS=1 pytest tests/architectural/ -v` exit 0 (NFR-005).
- Confirm layer-rule unchanged: `pytest tests/architectural/test_layer_rules.py -v` (NFR-003).

**FR-304 commit-message check:** T008 + T009 RED commits cite `covers: AC-8` and `expected GREEN at: WP02 final commit`.

## Activity Log

- 2026-05-18T12:35:44Z – claude:opus-4-7:python-pedro:implementer – shell_pid=2224539 – Started implementation via action command
- 2026-05-18T13:00:01Z – claude:opus-4-7:python-pedro:implementer – shell_pid=2224539 – Symbol-level dead-code gate + __all__ declarations on src/charter/ + src/kernel/ per C-007
- 2026-05-18T13:00:53Z – claude:sonnet-4-6:reviewer-renata:reviewer – shell_pid=2249698 – Started review via action command
- 2026-05-18T13:08:59Z – claude:sonnet-4-6:reviewer-renata:reviewer – shell_pid=2249698 – Review passed: __all__ on 34 charter + 3 kernel modules (C-007 scope respected); symbol-level gate GREEN (ATDD red->green verified on both RED commits); walker scans all src/ by design — enforces only on modules with __all__, which is charter+kernel-only by mandate; Cat-B=276 grandfathered entries justified by C-007/FR-121 scope boundary; Cat-A=13 deferred entries with block-level Slice G attribution and target=0 burndown policy; 3 sample pruned names (BOOTSTRAP_HEADER, LANGUAGE_INDICATORS, YAML_HEADER) verified internal-only; WP01 gates pass; 234 passed / 1 skipped sweep verified; ruff clean on WP02 scope. AC-8 satisfied.
