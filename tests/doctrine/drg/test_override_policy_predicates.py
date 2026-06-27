"""Focused unit tests for the promoted override-adjudication predicates.

These pin :func:`doctrine.drg.override_policy.find_overridden_builtin_urns` and
:func:`doctrine.drg.override_policy.find_unsanctioned_overrides` directly at
their production home (WP07 promotion). Inputs are built from the real
``DRGGraph`` / ``DRGNode`` / ``ReplaceableBuiltinsPolicy`` constructors — no
placeholder stubs (C-007) — so a regression in the pure predicates fails here
without needing a live merge.
"""

from __future__ import annotations

from doctrine.drg.models import DRGGraph, DRGNode, NodeKind
from doctrine.drg.override_policy import (
    ReplaceableBuiltin,
    ReplaceableBuiltinsPolicy,
    UnsanctionedOverride,
    find_overridden_builtin_urns,
    find_unsanctioned_overrides,
)
import pytest

pytestmark = pytest.mark.fast


def _node(urn: str, kind: NodeKind, provenance: str | None) -> DRGNode:
    return DRGNode(urn=urn, kind=kind, label="Node", provenance=provenance)


def _graph(*nodes: DRGNode) -> DRGGraph:
    return DRGGraph(
        schema_version="1.0",
        generated_at="2026-06-27T00:00:00Z",
        generated_by="unit-test",
        nodes=list(nodes),
        edges=[],
    )


def _policy(*entries: tuple[str, str]) -> ReplaceableBuiltinsPolicy:
    return ReplaceableBuiltinsPolicy(
        entries=tuple(ReplaceableBuiltin(urn=u, reason=r) for u, r in entries)
    )


# ---------------------------------------------------------------------------
# find_overridden_builtin_urns — provenance + built-in scope
# ---------------------------------------------------------------------------


def test_org_provenance_at_builtin_urn_is_detected() -> None:
    built_in_urns = frozenset({"tactic:shared"})
    merged = _graph(_node("tactic:shared", NodeKind.TACTIC, "org:rogue"))
    assert find_overridden_builtin_urns(merged, built_in_urns) == {
        "tactic:shared": "tactic"
    }


def test_project_provenance_at_builtin_urn_is_out_of_scope() -> None:
    # FR-012 boundary: project-tier overrides are the trusted operator tier and
    # are deliberately NOT adjudicated by the consumer-facing allowlist.
    built_in_urns = frozenset({"tactic:shared"})
    merged = _graph(_node("tactic:shared", NodeKind.TACTIC, "project"))
    assert find_overridden_builtin_urns(merged, built_in_urns) == {}


def test_org_provenance_at_non_builtin_urn_is_ignored() -> None:
    built_in_urns = frozenset({"tactic:shared"})
    merged = _graph(_node("tactic:novel", NodeKind.TACTIC, "org:rogue"))
    assert find_overridden_builtin_urns(merged, built_in_urns) == {}


def test_builtin_provenance_node_is_not_an_override() -> None:
    built_in_urns = frozenset({"tactic:shared"})
    merged = _graph(_node("tactic:shared", NodeKind.TACTIC, "built-in"))
    assert find_overridden_builtin_urns(merged, built_in_urns) == {}


# ---------------------------------------------------------------------------
# find_unsanctioned_overrides — fail-closed adjudication
# ---------------------------------------------------------------------------


def test_unlisted_urn_is_flagged_fail_closed() -> None:
    targets = {"tactic:shared": "tactic"}
    findings = find_unsanctioned_overrides(targets, _policy())
    assert [f.urn for f in findings] == ["tactic:shared"]
    assert isinstance(findings[0], UnsanctionedOverride)
    assert "replaceable-builtins" in findings[0].why


def test_allowlisted_non_directive_is_cleared() -> None:
    targets = {"tactic:shared": "tactic"}
    assert find_unsanctioned_overrides(targets, _policy(("tactic:shared", ""))) == []


def test_directive_override_with_blank_reason_is_flagged() -> None:
    targets = {"directive:shared": "directive"}
    findings = find_unsanctioned_overrides(
        targets, _policy(("directive:shared", "   "))
    )
    assert [f.urn for f in findings] == ["directive:shared"]
    assert "reason" in findings[0].why


def test_directive_override_with_real_reason_is_cleared() -> None:
    targets = {"directive:shared": "directive"}
    sanctioned = _policy(("directive:shared", "org tightened this directive"))
    assert find_unsanctioned_overrides(targets, sanctioned) == []


def test_empty_policy_sanctions_nothing() -> None:
    # Malformed/absent allowlist collapses to ``entries=()`` upstream; a fully
    # empty policy must sanction nothing (no false-sanction, no crash).
    targets = {"tactic:a": "tactic", "directive:b": "directive"}
    findings = find_unsanctioned_overrides(targets, _policy())
    assert sorted(f.urn for f in findings) == ["directive:b", "tactic:a"]


def test_findings_are_sorted_by_urn() -> None:
    targets = {"tactic:zeta": "tactic", "tactic:alpha": "tactic"}
    findings = find_unsanctioned_overrides(targets, _policy())
    assert [f.urn for f in findings] == ["tactic:alpha", "tactic:zeta"]
