"""Static model of the Makefile's ``FAST_TIER_MARKERS`` vocabulary (spec-kitty#21).

``make test-fast`` selects tests under ``FAST_TIER_DIRS`` by the Makefile's
``FAST_TIER_MARKERS`` expression: ``(fast or unit) and not slow and not e2e
and not integration and not regression and not distribution and not
live_adapter and not stress and not windows_ci and not platform_darwin`` --
a *positive* selection on ``{fast, unit}``. A test placed under one of those
roots that carries NONE of the vocabulary names this expression references is
silently deselected, not loudly skipped: it never runs in the
implementer/CI fast-tier baseline and nothing says so (controller-qa audit of
PR #15, spec-kitty#21).

This module parses the Makefile -- the single source of truth for both
values, never hand-copied here -- into the ``FAST_TIER_DIRS`` root list and
the marker vocabulary ``FAST_TIER_MARKERS`` references, so the completeness
test in ``test_fast_tier_marker_completeness.py`` can assert every collected
test under those roots carries at least one vocabulary marker.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from _pytest.mark.expression import Expression

REPO_ROOT = Path(__file__).resolve().parents[2]
MAKEFILE_PATH = REPO_ROOT / "Makefile"

_DIRS_RE = re.compile(r"^FAST_TIER_DIRS\s*:=\s*(?P<value>.+)$", re.MULTILINE)
_MARKERS_RE = re.compile(r"^FAST_TIER_MARKERS\s*=\s*(?P<value>.+)$", re.MULTILINE)


def fast_tier_dirs(makefile_path: Path | None = None) -> tuple[str, ...]:
    """The ``FAST_TIER_DIRS`` roots, read from the Makefile."""
    text = (makefile_path or MAKEFILE_PATH).read_text(encoding="utf-8")
    match = _DIRS_RE.search(text)
    if not match:
        raise RuntimeError("Makefile has no `FAST_TIER_DIRS := ...` line to parse")
    return tuple(match.group("value").split())


def fast_tier_markers_expr(makefile_path: Path | None = None) -> str:
    """The raw ``FAST_TIER_MARKERS`` expression string, read from the Makefile."""
    text = (makefile_path or MAKEFILE_PATH).read_text(encoding="utf-8")
    match = _MARKERS_RE.search(text)
    if not match:
        raise RuntimeError("Makefile has no `FAST_TIER_MARKERS = ...` line to parse")
    return match.group("value").strip()


def fast_tier_marker_vocabulary(makefile_path: Path | None = None) -> frozenset[str]:
    """Every marker name ``FAST_TIER_MARKERS`` references, positive or negated.

    Compiled first with pytest's own expression grammar (guarantees this
    module's reading matches what ``-m`` actually selects on -- a breaking
    change to that private API fails loudly at import time here, the same
    contract ``_gate_coverage.py`` relies on) then walked with stdlib ``ast``
    to collect every identifier regardless of ``not``: a test opted OUT of
    the fast tier by carrying ``slow`` is exactly as *explicitly marked* as
    one opted IN by carrying ``fast`` -- only a test with ZERO of these names
    is the silent drop this module exists to catch.
    """
    expr = fast_tier_markers_expr(makefile_path)
    Expression.compile(expr)  # loud fail on a grammar this module can't model
    tree = ast.parse(expr, mode="eval")
    names: set[str] = set()
    _collect_names(tree.body, names)
    return frozenset(names)


def _collect_names(node: ast.expr, names: set[str]) -> None:
    if isinstance(node, ast.Name):
        names.add(node.id)
    elif isinstance(node, ast.UnaryOp):
        _collect_names(node.operand, names)
    elif isinstance(node, ast.BoolOp):
        for value in node.values:
            _collect_names(value, names)
    else:
        raise RuntimeError(
            f"unsupported marker-expression node {ast.dump(node)} in FAST_TIER_MARKERS -- extend _collect_names before trusting this module's vocabulary.",
        )
