"""Architectural ratchet: no new 2-arg ``is_committed()`` call sites (WP01/FR-003).

``is_committed()`` in ``specify_cli.missions._substantive`` was upgraded in
WP01 to accept a ``placement: CommitTarget | None`` parameter (Issue #1884).
All call sites in ``src/`` MUST pass ``placement=`` so that coordination-branch
topology is respected. Any call with exactly 2 positional args and no
``placement`` keyword is a regression — it anchors the gate to the primary HEAD
and silently fails for coord-topology missions.

This ratchet:
1. Walks every ``.py`` file under ``src/`` using ``ast.parse``.
2. Finds every ``Call`` node where the callee is the bare name ``is_committed``.
3. Asserts that the call either:
   - has a ``placement`` keyword argument (correct), OR
   - is in the grace-list (the wrapper itself, which defaults ``placement=None``
     and exposes it as a keyword-only default — its own definition is NOT a
     call site).

A new call that omits ``placement=`` will fail this test, forcing the author to
make a deliberate, named decision about topology.

WP01 / Issue #1884 / FR-003.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"

# The implementation module's own function definition is not a call site.
# List any grace-listed call sites here as repo-relative POSIX paths.
# Each entry must include a brief rationale in a comment below.
_GRACE_LIST: frozenset[str] = frozenset(
    {
        # The _substantive.py module defines is_committed — not a call site.
        "src/specify_cli/missions/_substantive.py",
    }
)


def _rel(path: Path) -> str:
    return path.relative_to(_REPO_ROOT).as_posix()


def _find_bare_2arg_is_committed_calls(path: Path) -> list[int]:
    """Return line numbers of 2-arg ``is_committed(...)`` calls without ``placement=``.

    A call is flagged when ALL of:
    - The callee is the bare name ``is_committed`` (``ast.Name``).
    - There is no ``placement`` keyword argument.
    - There are 2 or more positional arguments (the original broken form).
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []

    violations: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        # Match bare-name calls only (not method calls like obj.is_committed).
        if not (isinstance(node.func, ast.Name) and node.func.id == "is_committed"):
            continue
        has_placement_kwarg = any(kw.arg == "placement" for kw in node.keywords)
        if has_placement_kwarg:
            continue
        # Flagged: bare is_committed call with no placement= keyword.
        violations.append(node.lineno)
    return violations


def test_no_2arg_is_committed_calls_without_placement() -> None:
    """Every ``is_committed(...)`` call in ``src/`` must pass ``placement=``.

    Flat-topology callers can pass ``placement=None`` explicitly; the default
    preserves backward compatibility but must not be relied upon silently for
    new call sites.
    """
    violations: dict[str, list[int]] = {}

    for py_file in sorted(_SRC_ROOT.rglob("*.py")):
        if "__pycache__" in py_file.parts:
            continue
        rel = _rel(py_file)
        if rel in _GRACE_LIST:
            continue
        lines = _find_bare_2arg_is_committed_calls(py_file)
        if lines:
            violations[rel] = lines

    if violations:
        details = "\n".join(
            f"  {path}: lines {lines}" for path, lines in sorted(violations.items())
        )
        pytest.fail(
            "Found is_committed() calls without placement= keyword.\n"
            "Pass placement=<CommitTarget> (or placement=None for flat topology) "
            "to make topology explicit.\n\n"
            f"Violations:\n{details}"
        )
