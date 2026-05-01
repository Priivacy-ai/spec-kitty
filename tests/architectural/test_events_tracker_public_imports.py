"""Architectural: public-import freeze for ``spec_kitty_events`` / ``spec_kitty_tracker``.

WP05 of mission ``stability-and-hygiene-hardening-2026-04-01KQ4ARB``
implements FR-024 by freezing the public surface CLI consumes from the two
external packages. Updating either contract requires a paired edit:

- ``kitty-specs/stability-and-hygiene-hardening-2026-04-01KQ4ARB/contracts/events-envelope.md``
- ``kitty-specs/stability-and-hygiene-hardening-2026-04-01KQ4ARB/contracts/tracker-public-imports.md``

The test enforces two invariants:

1. No CLI source file imports from a private ``spec_kitty_events._internal``
   or ``spec_kitty_tracker._internal`` path.
2. Every imported top-level symbol from either package belongs to the
   documented public-surface allow-list (a superset of the contracts'
   required minimum, kept in sync as CLI usage grows).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.architectural]


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src" / "specify_cli"

# The contract markdown files referenced by this test. If they move, this
# pointer set must move with them so reviewers can cross-check.
_CONTRACT_DOCS = (
    _REPO_ROOT / "kitty-specs" / "stability-and-hygiene-hardening-2026-04-01KQ4ARB" / "contracts" / "events-envelope.md",
    _REPO_ROOT / "kitty-specs" / "stability-and-hygiene-hardening-2026-04-01KQ4ARB" / "contracts" / "tracker-public-imports.md",
)

# Public surface CLI is allowed to import from. Sub-modules (``module.subname``)
# are matched by *prefix*, so any symbol under an allow-listed sub-module is
# considered public. This list intentionally tracks current real CLI usage.
# A net-new sub-module needs both an entry here and an update to the contract.
_EVENTS_PUBLIC_PREFIXES = frozenset(
    (
        "spec_kitty_events",
        "spec_kitty_events.decisionpoint",
        "spec_kitty_events.decision_moment",
        "spec_kitty_events.mission_next",
        "spec_kitty_events.glossary.events",
        "spec_kitty_events.persistence",
    )
)

_TRACKER_PUBLIC_PREFIXES = frozenset(
    (
        "spec_kitty_tracker",
        "spec_kitty_tracker.models",
        "spec_kitty_tracker.errors",
    )
)

_FORBIDDEN_INTERNAL_RE = re.compile(r"^spec_kitty_(events|tracker)(\._internal\b|\._internal\.)")


def _python_files() -> list[Path]:
    return [p for p in _SRC_ROOT.rglob("*.py") if "__pycache__" not in p.parts]


def _module_is_public(module: str, prefixes: frozenset[str]) -> bool:
    return any(module == p or module.startswith(p + ".") for p in prefixes)


def _iter_imports(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                yield node.module, node.lineno
        elif isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, node.lineno


def test_contract_docs_present() -> None:
    """The contract markdown files referenced by this test MUST exist.

    Updating the public surface requires updating both this test AND the
    contract docs. If the docs are removed or relocated, future reviewers
    lose the second half of the cross-check.
    """
    missing = [str(p) for p in _CONTRACT_DOCS if not p.is_file()]
    assert not missing, f"Contract markdown files referenced by this test are missing: {missing}. Update _CONTRACT_DOCS or restore the docs."


def test_no_cli_source_imports_internal_events_or_tracker_paths() -> None:
    """FR-024: CLI MUST NOT reach into ``_internal`` modules of either package."""
    offenders: list[str] = []
    for path in _python_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover - test infra only
            continue
        for module, lineno in _iter_imports(tree):
            if _FORBIDDEN_INTERNAL_RE.match(module):
                offenders.append(f"{path.relative_to(_REPO_ROOT)}:{lineno} -> {module}")
    assert not offenders, (
        "Found CLI imports reaching into private package internals "
        "(spec_kitty_events._internal / spec_kitty_tracker._internal). "
        "Switch to the public surface documented in "
        "kitty-specs/stability-and-hygiene-hardening-2026-04-01KQ4ARB/"
        "contracts/. Offenders:\n  " + "\n  ".join(offenders)
    )


def test_cli_events_imports_are_subset_of_public_surface() -> None:
    """FR-024: every ``spec_kitty_events.*`` import must hit the public surface."""
    offenders: list[str] = []
    for path in _python_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover
            continue
        for module, lineno in _iter_imports(tree):
            if (module == "spec_kitty_events" or module.startswith("spec_kitty_events.")) and not _module_is_public(module, _EVENTS_PUBLIC_PREFIXES):
                offenders.append(f"{path.relative_to(_REPO_ROOT)}:{lineno} -> {module}")
    assert not offenders, (
        "CLI imports a spec_kitty_events sub-module that is not in the "
        "public-surface allow-list. Either use a public alternative or "
        "extend _EVENTS_PUBLIC_PREFIXES + the events contract markdown "
        "in the same change. Offenders:\n  " + "\n  ".join(offenders)
    )


def test_cli_tracker_imports_are_subset_of_public_surface() -> None:
    """FR-024: every ``spec_kitty_tracker.*`` import must hit the public surface."""
    offenders: list[str] = []
    for path in _python_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover
            continue
        for module, lineno in _iter_imports(tree):
            if (module == "spec_kitty_tracker" or module.startswith("spec_kitty_tracker.")) and not _module_is_public(module, _TRACKER_PUBLIC_PREFIXES):
                offenders.append(f"{path.relative_to(_REPO_ROOT)}:{lineno} -> {module}")
    assert not offenders, (
        "CLI imports a spec_kitty_tracker sub-module that is not in the "
        "public-surface allow-list. Either use a public alternative or "
        "extend _TRACKER_PUBLIC_PREFIXES + the tracker contract markdown "
        "in the same change. Offenders:\n  " + "\n  ".join(offenders)
    )
