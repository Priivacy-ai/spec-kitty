"""Structural safety invariants for ``.github/workflows/docs-freshness.yml`` (FR-005).

The docs-freshness gate scopes its ``pull_request`` trigger with a positive
``paths:`` *allowlist* — a change is guarded only if it touches a listed path.
Two structural properties keep that scoping safe, and both are silent to break
(a bad edit still parses as valid YAML and CI stays green):

1. The PR allowlist must NOT be widened to include the whole test / spec trees
   (``tests/**`` / ``kitty-specs/**``). Those trees are enormous and mostly
   irrelevant to docs; listing them would run the whole-tree docs scan on
   nearly every PR, defeating the point of the allowlist. NOTE the assertion is
   *absence-from-an-allowlist*, not the presence of a ``!tests/**`` exclusion —
   GitHub ``paths:`` filters have no negation operator, so there is no ``!``
   pattern to look for.
2. An UNFILTERED ``push:`` trigger on ``main`` (no ``paths:`` key) must exist as
   the backstop: the gate's relative-link / related-edge sub-checks read an
   unbounded input set (any file a docs page links to), which no path filter can
   express, so the whole-tree scan on every push to ``main`` is what actually
   catches a red tree.

A documented invariant comment in the trigger block is the third property; it
carries the "why", cross-references this test, and must co-evolve with it.

SCOPE / WHAT THIS TEST CANNOT SEE: this is a static parse of the workflow file.
It does NOT and CANNOT observe the live GitHub branch-protection
required-status-check list. The scoping above is only safe while
``docs-freshness`` is NOT a required check (operator-confirmed, C-003); that
fact is unobservable from CI and is asserted nowhere here — do not add a
``required == {...}`` assertion (it would also conflict with ui-e2e.yml's
"Required-check contract" comment).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.fast

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "docs-freshness.yml"

# Test / spec trees that must never appear in the PR allowlist (property 1).
_FORBIDDEN_ALLOWLIST_ENTRIES = ("tests/**", "kitty-specs/**")

# Stable substrings the invariant comment must carry (property 3). Chosen to be
# resilient to reflow: the marker word, the backstop rationale, and this test's
# own basename so comment and test are cross-referenced.
_INVARIANT_COMMENT_MARKERS = (
    "INVARIANT",
    "backstop",
    "test_docs_freshness_invariant.py",
)


def _get_on(workflow: dict[Any, Any]) -> dict[str, Any]:
    """Return the ``on:`` mapping.

    PyYAML parses the bare key ``on`` as the boolean ``True`` (YAML 1.1), so the
    mapping may be keyed under ``"on"`` or under ``True``. Handle both.
    """
    on = workflow.get("on", workflow.get(True))
    assert isinstance(on, dict), "workflow has no mapping-form `on:` trigger block"
    return on


def _pr_paths(on: dict[str, Any]) -> list[str] | None:
    """The ``pull_request.paths`` allowlist, or ``None`` if unfiltered/absent."""
    pull_request = on.get("pull_request")
    if not isinstance(pull_request, dict):
        return None
    paths = pull_request.get("paths")
    return list(paths) if isinstance(paths, list) else None


def _push_has_unfiltered_main_backstop(on: dict[str, Any]) -> bool:
    """True iff a ``push:`` trigger targets ``main`` with NO ``paths:`` filter."""
    push = on.get("push")
    if not isinstance(push, dict):
        return False
    branches = push.get("branches")
    if not (isinstance(branches, list) and "main" in branches):
        return False
    return "paths" not in push


def _load_workflow(path: Path) -> dict[Any, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


# --------------------------------------------------------------------------- #
# Property tests against the real workflow.
# --------------------------------------------------------------------------- #


def test_pr_allowlist_present_and_excludes_test_trees() -> None:
    """Property 1: PR ``paths:`` allowlist exists and omits the test/spec trees."""
    on = _get_on(_load_workflow(_WORKFLOW))
    paths = _pr_paths(on)
    assert paths, "pull_request.paths allowlist is missing — PR scoping is unguarded"
    for forbidden in _FORBIDDEN_ALLOWLIST_ENTRIES:
        assert forbidden not in paths, (
            f"{forbidden!r} must NOT be in the PR allowlist: it would run the "
            "whole-tree docs scan on nearly every PR. (This is absence-from-an-"
            "allowlist; there is no `!` exclusion pattern to add.)"
        )


def test_unfiltered_push_main_backstop_present() -> None:
    """Property 2: an unfiltered ``push: main`` backstop trigger exists."""
    on = _get_on(_load_workflow(_WORKFLOW))
    assert _push_has_unfiltered_main_backstop(on), (
        "docs-freshness needs an UNFILTERED `push:` trigger on `main` (no "
        "`paths:` key) as the whole-tree backstop for the unbounded link/edge "
        "input set the PR allowlist cannot express."
    )


def test_invariant_comment_present_and_cross_references_this_test() -> None:
    """Property 3: the documented invariant comment exists and names this test."""
    raw = _WORKFLOW.read_text(encoding="utf-8")
    for marker in _INVARIANT_COMMENT_MARKERS:
        assert marker in raw, (
            f"docs-freshness.yml is missing the invariant-comment marker {marker!r}; "
            "the comment must document the trigger-scoping rationale and "
            "cross-reference this test so the two co-evolve (FR-006)."
        )


# --------------------------------------------------------------------------- #
# Red-first negative guards (C-006): the predicates must REJECT a workflow that
# drops the backstop or widens the allowlist. Without these, the property tests
# above could pass vacuously if a helper silently degraded to always-true.
# --------------------------------------------------------------------------- #


def test_backstop_predicate_rejects_missing_push(tmp_path: Path) -> None:
    """A workflow whose ``push`` trigger gained a ``paths:`` filter has no backstop."""
    broken = tmp_path / "broken.yml"
    broken.write_text(
        "on:\n"
        "  pull_request:\n"
        "    paths: ['docs/**']\n"
        "  push:\n"
        "    branches: [main]\n"
        "    paths: ['docs/**']\n",  # filtered push => backstop lost
        encoding="utf-8",
    )
    on = _get_on(_load_workflow(broken))
    assert not _push_has_unfiltered_main_backstop(on)


def test_allowlist_predicate_flags_test_tree_entry(tmp_path: Path) -> None:
    """A widened allowlist that lists ``tests/**`` is detected as forbidden."""
    widened = tmp_path / "widened.yml"
    widened.write_text(
        "on:\n"
        "  pull_request:\n"
        "    paths: ['docs/**', 'tests/**']\n"
        "  push:\n"
        "    branches: [main]\n",
        encoding="utf-8",
    )
    on = _get_on(_load_workflow(widened))
    paths = _pr_paths(on)
    assert paths is not None
    assert "tests/**" in paths  # the exact condition the real-file test forbids
