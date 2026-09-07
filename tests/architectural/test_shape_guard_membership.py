"""Enforcement-allowlist-vs-shape-guard membership guard (E4/C-007/FR-014/NFR-007).

Mission ``ci-pipeline-reinstatement-01M1X35E`` WP16 (closes #3458). The P2
shape-guard demotion needs a **committed, machine-checkable partition** so the
distinction between "always-on P1 enforcement" and "demoted-off-the-gate P2
shape guard" is never a per-PR judgment call, and relabeling the committed
``tests/architectural/shape_guard_membership.yaml`` alone cannot move a test on
or off the blocking gate in either direction:

* An **enforcement allowlist** (``test_no_dead_symbols``/
  ``test_no_retired_subsystems``/``test_no_dead_modules``/
  ``test_integration_boundary``) catches real defects and is ALWAYS-ON. This
  module's own :data:`_ENFORCEMENT_ALLOWLIST_FILES` tuple — a canonical source
  living in test *code*, not the yaml — is what
  :func:`test_enforcement_allowlist_set_is_exactly_the_c007_canon` checks the
  yaml against; editing the yaml alone can neither drop one of these four out
  of ``enforcement-allowlist`` nor add a fifth entry into that class (the
  "gutting P1" and "shape-guard silently promoted" footguns this mission's
  Risks section names).
* A **shape guard** (the golden-count frozen-ceiling ratchet) is demoted OFF
  the blocking gate: a breach is reported as advisory telemetry, never raised.
  :func:`test_shape_guard_demotion_does_not_raise_under_a_manufactured_breach`
  proves this behaviorally — it imports the real function, forces the exact
  ceiling-breach shape that used to hard-fail, and asserts nothing raises. A
  future edit that silently re-adds a hard ``assert violations == []`` reds
  this test immediately, so the yaml label alone cannot re-litigate the gate
  without the code actually changing back.
* **Behavioral** entries (the golden-count module's own pure-helper unit
  tests, and the already-narrowed twelve-agent-parity structural/content
  tests, #3447 WP05) are ordinary tests: neither ratchet class, no special
  treatment.

Every membership key is tied to a real file (and, for a ``::``-qualified key,
a real function defined in it) via AST/import introspection — never a
free-text label with nothing backing it.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.architectural]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MEMBERSHIP_PATH = Path(__file__).resolve().with_name("shape_guard_membership.yaml")

_VALID_CLASSES = frozenset({"enforcement-allowlist", "shape-guard", "behavioral"})

# The C-007 enforcement-allowlist canon. Deliberately hardcoded here (in test
# *code*, reviewed like any other diff) rather than derived from the yaml
# itself -- this is the guard's own canonical source, so a yaml-only edit
# cannot silently add or remove a member of the always-on P1 set.
_ENFORCEMENT_ALLOWLIST_FILES: tuple[str, ...] = (
    "tests/architectural/test_no_dead_symbols.py",
    "tests/architectural/test_no_retired_subsystems.py",
    "tests/architectural/test_no_dead_modules.py",
    "tests/architectural/test_integration_boundary.py",
)


def _load_membership() -> dict[str, str]:
    data = yaml.safe_load(_MEMBERSHIP_PATH.read_text(encoding="utf-8"))
    membership = data["membership"]
    if not isinstance(membership, dict):
        raise TypeError(f"{_MEMBERSHIP_PATH}: 'membership' must be an object, got {type(membership)!r}")
    return {str(k): str(v) for k, v in membership.items()}


def _module_relpath(entry: str) -> str:
    """The bare module-path portion of a membership key (strips a `::func` suffix)."""
    return entry.split("::", 1)[0]


def _module_name_for(relpath: str) -> str:
    """Dotted import name for a `tests/...py` relpath (e.g. `tests.architectural.test_x`)."""
    assert relpath.endswith(".py"), relpath
    return relpath[: -len(".py")].replace("/", ".")


# ---------------------------------------------------------------------------
# Schema + real-code-binding checks.
# ---------------------------------------------------------------------------


def test_membership_file_exists_and_parses() -> None:
    assert _MEMBERSHIP_PATH.exists(), (
        f"{_MEMBERSHIP_PATH} is missing -- the P2 shape-guard demotion (C-007/FR-014/E4) requires a committed, machine-checkable membership partition."
    )
    membership = _load_membership()
    assert membership, "membership partition must not be empty"


def test_every_entry_has_exactly_one_recognized_class() -> None:
    membership = _load_membership()
    for entry, cls in membership.items():
        assert cls in _VALID_CLASSES, f"{entry!r} has class {cls!r}, expected one of {sorted(_VALID_CLASSES)}"


def test_every_membership_key_resolves_to_a_real_module_or_function() -> None:
    """A membership entry is tied to real code, not free text: the module file
    must exist, and a `::`-qualified entry's function must actually be defined
    in it.
    """
    membership = _load_membership()
    for entry in membership:
        module_relpath, _, func_name = entry.partition("::")
        module_path = _REPO_ROOT / module_relpath
        assert module_path.is_file(), f"{entry!r}: no such module {module_path}"
        if func_name:
            tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=module_relpath)
            defined = {node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
            assert func_name in defined, f"{entry!r}: no function named {func_name!r} defined in {module_relpath}"


# ---------------------------------------------------------------------------
# C-007 boundary: enforcement allowlists are the fixed, always-on canon.
# ---------------------------------------------------------------------------


def test_enforcement_allowlist_set_is_exactly_the_c007_canon() -> None:
    """Neither direction of relabeling is possible via a yaml-only edit: the
    set of entries classed ``enforcement-allowlist`` must exactly match
    :data:`_ENFORCEMENT_ALLOWLIST_FILES` -- no member can be moved OUT (the
    "gutting P1" footgun) and no other test can be moved IN (a shape guard
    silently "promoted" into the always-on canon without actually being one).
    """
    membership = _load_membership()
    classified_enforcement = {_module_relpath(entry) for entry, cls in membership.items() if cls == "enforcement-allowlist"}
    assert classified_enforcement == set(_ENFORCEMENT_ALLOWLIST_FILES), (
        f"enforcement-allowlist classification drifted from the C-007 canon: got {sorted(classified_enforcement)}, expected {sorted(_ENFORCEMENT_ALLOWLIST_FILES)}"
    )


def test_enforcement_allowlists_still_carry_real_blocking_assertions() -> None:
    """Reverse relabeling guard: an enforcement-allowlist module cannot be
    silently gutted into advisory-only telemetry while the yaml still reads
    ``enforcement-allowlist``. Each must define at least one real ``assert``
    inside a ``test_*`` function -- a mechanical, AST-derived proxy for
    "still actually blocks on failure", not a free-text/docstring claim.
    """
    for relpath in _ENFORCEMENT_ALLOWLIST_FILES:
        module_path = _REPO_ROOT / relpath
        tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=relpath)
        found_assert = False
        for node in ast.walk(tree):
            is_test_func = isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")
            if is_test_func and any(isinstance(inner, ast.Assert) for inner in ast.walk(node)):
                found_assert = True
                break
        assert found_assert, f"{relpath!r} is classed enforcement-allowlist but no test_* function contains a real `assert` -- it may have been silently demoted"


# ---------------------------------------------------------------------------
# P2 demotion: a shape guard must behave as off-the-gate, not merely say so.
# ---------------------------------------------------------------------------


def test_shape_guard_demotion_does_not_raise_under_a_manufactured_breach() -> None:
    """T082/T087 core proof: a ``shape-guard``-classed test must not hard-fail
    even when the exact real-world breach it used to catch is manufactured --
    proving it is genuinely off the blocking gate, not merely relabeled in the
    yaml while still asserting underneath. Also guards against a future
    regression silently re-adding the hard assertion: this test would red the
    moment that happened, independent of what the yaml label claims.
    """
    membership = _load_membership()
    shape_guard_entries = [entry for entry, cls in membership.items() if cls == "shape-guard" and "::" in entry]
    assert shape_guard_entries, "expected at least one `::`-qualified shape-guard entry"

    for entry in shape_guard_entries:
        module_relpath, _, func_name = entry.partition("::")
        module = importlib.import_module(_module_name_for(module_relpath))
        target = getattr(module, func_name)
        assert callable(target), f"{entry!r}: {func_name!r} is not callable in {module_relpath}"

        monkeypatch = pytest.MonkeyPatch()
        try:
            # Force the exact ceiling-breach shape this guard used to
            # hard-block on, regardless of the real repo tree's current state.
            if hasattr(module, "convert_counts_by_dir"):
                monkeypatch.setattr(module, "convert_counts_by_dir", lambda _sites: {"tests/manufactured_breach": 999})
            if hasattr(module, "load_baseline"):
                monkeypatch.setattr(module, "load_baseline", lambda: {"tests/manufactured_breach": 0})
            target()  # must not raise -- that is the demotion
        finally:
            monkeypatch.undo()
