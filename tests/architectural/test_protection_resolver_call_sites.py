"""Architectural ratchet: ``protected_branches(`` call sites in ``src/`` (WP05/FR-010).

FR-010 / #1868: The protected-branch **decision** must be made in exactly one
place.  :meth:`ProtectionPolicy.resolve` in ``git/protection_policy.py`` is the
single-authority resolver; :func:`protected_branches` in ``git/commit_helpers.py``
is the one sanctioned public delegate (kept for backward-compatible callers and
the FR-010 import allowlist).

Any other production module calling ``protected_branches(...)`` directly bypasses
the resolver boundary — the caller gets a stale/misconfigured value, and any
operator-hatch state, config-file overrides, or remote-default-branch fallback
logic is silently skipped.  WP01/WP03/WP04 rerouted all call sites; this guard
makes the boundary structural by failing CI if one is reintroduced.

Detection strategy
------------------
The guard AST-walks every ``*.py`` file under ``src/`` and collects every
``ast.Call`` node whose callee is the **bare name** ``protected_branches``
(``ast.Name`` with ``id == "protected_branches"``).  This deliberately excludes:

* **Attribute access** (``self.protected_branches``, ``policy.protected_branches``)
  — these are field reads on the :class:`ProtectionPolicy` value object, not
  resolution decisions.
* **Definitions** (``def protected_branches(...):``) — the ``ast.FunctionDef``
  node is not an ``ast.Call``; it never trips the scanner.
* **Default-branch detection sites** — ``git_ops.py:313``,
  ``stale_detection.py:113``, and ``vcs/git.py:966`` iterate over
  ``["main", "master", "develop"]`` to discover which branch *exists* in a
  repo; that is detection, not a protection *decision*, and none of these sites
  call ``protected_branches()``.
* **Classification sets** — ``_WELL_KNOWN_INTEGRATION_BRANCHES``
  (``acceptance/__init__.py:1193``) and ``common_primary_branches``
  (``mission.py:598``, a local tuple) categorise branches for reporting; again,
  neither calls ``protected_branches()``.

Matching the ``protected_branches(`` call form (bare ``ast.Name``) sidesteps
all of these cleanly — none of them emit a bare-name call node.

Allowlist (FR-010 sanctioned sites)
-------------------------------------
Only these two ``src/`` files are permitted to contain a bare
``protected_branches(...)`` call:

* ``src/specify_cli/git/protection_policy.py`` — the resolver module;
  internally calls ``_resolve_protected_branches()`` (private helper) and may
  reference the public name in its own docstrings / internal logic.
* ``src/specify_cli/git/commit_helpers.py`` — the demoted public delegate;
  the function definition lives here and may forward-call
  ``ProtectionPolicy.resolve(...).protected_branches`` (attribute, not a bare
  Name call), but the module is in the allowlist so future internal
  self-references are permitted without requiring an allowlist update.

Extending the allowlist requires a deliberate policy decision: the new site must
be documented with a rationale comment naming the ONE flow it authorises.

WP05 / FR-010 / #1868.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"

# ---------------------------------------------------------------------------
# Sanctioned call sites (FR-010 allowlist)
# ---------------------------------------------------------------------------
# Only these src/ files may contain a bare protected_branches(...) call.
# Adding a new entry is a policy decision — document the one flow it authorises.
_ALLOWLIST: frozenset[str] = frozenset(
    {
        # The single-authority resolver module (ProtectionPolicy.resolve).
        "src/specify_cli/git/protection_policy.py",
        # The demoted public delegate (backward-compatible entry point).
        "src/specify_cli/git/commit_helpers.py",
    }
)


def _rel(path: Path) -> str:
    return path.relative_to(_REPO_ROOT).as_posix()


def _find_bare_protected_branches_calls(path: Path) -> list[int]:
    """Return line numbers of bare ``protected_branches(...)`` call nodes.

    Only bare-name calls (``ast.Name`` with ``id == "protected_branches"``) are
    flagged.  Attribute reads (``policy.protected_branches``) and function
    definitions (``def protected_branches```) are NOT call nodes and are never
    returned.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []

    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "protected_branches"
    ]


def test_protected_branches_calls_confined_to_resolver_and_delegate() -> None:
    """All bare ``protected_branches(...)`` calls in ``src/`` must be in the allowlist.

    A bare call outside the resolver (``protection_policy.py``) or its delegate
    (``commit_helpers.py``) means the caller bypasses operator-hatch state,
    config-file overrides, and remote-default-branch fallback — silently
    returning a stale or misconfigured protection set (FR-010 / #1868).

    To add a new sanctioned call site: extend ``_ALLOWLIST`` above and document
    the ONE flow the call authorises with a rationale comment.
    """
    violations: dict[str, list[int]] = {}

    for py_file in sorted(_SRC_ROOT.rglob("*.py")):
        if "__pycache__" in py_file.parts:
            continue
        rel = _rel(py_file)
        if rel in _ALLOWLIST:
            continue
        lines = _find_bare_protected_branches_calls(py_file)
        if lines:
            violations[rel] = lines

    if violations:
        details = "\n".join(
            f"  {path}: lines {lines}" for path, lines in sorted(violations.items())
        )
        pytest.fail(
            "Found bare protected_branches(...) calls outside the FR-010 allowlist.\n"
            "Use ProtectionPolicy.resolve(repo_root) instead, which applies config-file\n"
            "overrides, remote-default-branch fallback, and operator-hatch state.\n"
            "To add a new sanctioned call site: extend _ALLOWLIST in this module and\n"
            "document the ONE flow the call authorises.\n\n"
            f"Violations:\n{details}"
        )
