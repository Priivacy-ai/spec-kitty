"""Architectural ratchet: GuardCapability call sites in ``src/`` (PR #1850 M1).

``GuardCapability`` is asserted-at-the-surface (FR-008 / C-GUARD-2): each
non-standard member authorizes exactly ONE bookkeeping flow onto a protected
ref. PR #1850 regressed this by sprinkling ``TEST_MODE`` and
``MERGE_BOOKKEEPING`` onto ordinary task/workflow/finalize surfaces, silently
converting "refused on protected main" into "allowed". This ratchet makes the
capability/flow binding structural:

1. **No production module asserts ``TEST_MODE``.** The member exists for test
   fixtures only; the sole ``src/`` reference is the policy module's own
   ``_PROTECTED_FLOW_CAPABILITIES`` set (the enum's home).
2. **Every other protected-flow member has an explicit per-flow allowlist.**
   ``MERGE_BOOKKEEPING`` belongs to the merge done-transitions flow,
   ``UPGRADE_BOOKKEEPING`` to the upgrade flow, ``RELEASE_FLOW`` currently has
   no caller (S6 wire-or-delete debt — adding one requires updating this
   allowlist deliberately).

The scan is AST-based (real ``GuardCapability.<MEMBER>`` attribute
expressions), so prose mentions in docstrings/comments do not trip it.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"

# The policy module that defines the enum and its protected-flow set. It is
# the ONLY src/ file allowed to reference GuardCapability.TEST_MODE.
_ENUM_HOME = "src/specify_cli/core/commit_guard.py"

# Per-flow allowlists for the remaining protected-flow members. Each entry is
# a documented ONE-flow authorization (FR-008); extending a set is an explicit
# policy decision, not a convenience.
_PROTECTED_FLOW_ALLOWLISTS: dict[str, frozenset[str]] = {
    # Test-fixture-only: no production caller, ever.
    "TEST_MODE": frozenset({_ENUM_HOME}),
    # The bona-fide merge done-transitions bookkeeping flow. The safe_commit call
    # site relocated from cli/commands/merge.py to the merge/executor.py seam in
    # mission #2057's god-module decomposition (behavior-preserving move).
    "MERGE_BOOKKEEPING": frozenset({_ENUM_HOME, "src/specify_cli/merge/executor.py"}),
    # The bona-fide upgrade bookkeeping flow.
    "UPGRADE_BOOKKEEPING": frozenset({_ENUM_HOME, "src/specify_cli/cli/commands/upgrade.py"}),
    # No reachable caller today (S6 debt: wire or delete).
    "RELEASE_FLOW": frozenset({_ENUM_HOME}),
}


def _iter_src_python_files() -> list[Path]:
    return sorted(p for p in _SRC_ROOT.rglob("*.py") if "__pycache__" not in p.parts)


def _rel(path: Path) -> str:
    return path.relative_to(_REPO_ROOT).as_posix()


def _guard_capability_members_referenced(path: Path) -> set[str]:
    """Return the ``GuardCapability.<MEMBER>`` attribute names used in ``path``."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    members: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "GuardCapability"
        ):
            members.add(node.attr)
    return members


@pytest.mark.parametrize("member", sorted(_PROTECTED_FLOW_ALLOWLISTS))
def test_protected_flow_capability_call_sites_are_allowlisted(member: str) -> None:
    """Each protected-flow GuardCapability member binds to its ONE flow.

    ``STANDARD`` is freely assertable (it grants nothing on protected refs);
    every other member is restricted to the allowlisted module(s) above. A new
    site must either assert ``STANDARD`` (refused on protected refs — almost
    always correct for status bookkeeping) or extend the allowlist with a
    rationale comment naming the ONE flow it authorizes.
    """
    allowlist = _PROTECTED_FLOW_ALLOWLISTS[member]
    actual = {
        _rel(path)
        for path in _iter_src_python_files()
        if member in _guard_capability_members_referenced(path)
    }

    unexpected = actual - allowlist
    assert not unexpected, (
        f"GuardCapability.{member} is asserted outside its flow: "
        f"{sorted(unexpected)}. Each non-standard capability authorizes "
        "exactly ONE bookkeeping flow (FR-008 / C-GUARD-2); ordinary status "
        "bookkeeping must assert STANDARD so protected destinations are "
        "refused. PR #1850's guard-bypass regression is exactly this misuse."
    )

    stale = {
        entry
        for entry in allowlist - actual
        if entry != _ENUM_HOME  # the enum home may reference members only via the policy set
    }
    if member in {"MERGE_BOOKKEEPING", "UPGRADE_BOOKKEEPING"}:
        assert not stale, (
            f"Allowlisted GuardCapability.{member} flow module(s) no longer "
            f"assert it: {sorted(stale)}. Remove them from "
            "_PROTECTED_FLOW_ALLOWLISTS so the binding stays exact."
        )
