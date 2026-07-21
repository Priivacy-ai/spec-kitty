"""Tests for the ``tension_unreconciled`` finding (WP05, T029).

Contract: ``kitty-specs/doctrine-tension-edges-01KY1WPC/contracts/tension-finding.md``.
Requirements: FR-009, FR-010, NFR-001, SC-001, SC-002 (spec.md US1/US2).

Covers:
- ``test_positive_finding_for_co_activated_unreconciled_pair``: NFR-001's
  named trap ("a no-op checker returning [] fails this requirement") --
  asserts on an actual positive finding, not merely absence-of-error.
- ``test_non_finding_when_only_one_side_active``: US1 Acceptance Scenario 3.
- ``test_sc002_live_before_after_real_built_in_pack``: the mission's
  headline acceptance criterion, exercised against the real bundled
  doctrine pack (not a synthetic fixture) -- deactivating/reactivating the
  built-in reconciler makes both findings appear/clear.
- ``test_half_reconciled_pair_still_flagged``: US2 Acceptance Scenario 2.
- ``test_dedup_symmetric_authoring``: Edge Case -- a pair authored/queryable
  from both directions still yields exactly one finding (INV-001).
- ``test_fail_closed_on_scan_error``: FR-009 fail-closed -- a forced error
  lands in ``verification_errors``, never a silently empty finding list.
- ``test_to_json_includes_tension_unreconciled_shape``: SC-001 JSON shape.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import charter._drg_helpers as drg_helpers
from charter import consistency_check
from charter.consistency_check import (
    ConsistencyReport,
    TensionFinding,
    run_consistency_check,
    scan_unreconciled_tensions,
)
from charter.drg import DRGEdge, DRGGraph, DRGNode, NodeKind, Relation
from charter.invocation_context import ProjectContext

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Real built-in doctrine identifiers used throughout (see WP02's hand-
# authored edges in src/doctrine/directive.graph.yaml):
#   directive:DIRECTIVE_024 <-> directive:DIRECTIVE_025
#   directive:DIRECTIVE_025 <-> tactic:change-apply-smallest-viable-diff
#   directive:RECONCILE_CHANGE_SCOPE_TENSIONS reconciles both pairs.
# ---------------------------------------------------------------------------
_STEM_024 = "024-locality-of-change"
_STEM_025 = "025-boy-scout-rule"
_STEM_TACTIC = "change-apply-smallest-viable-diff"
_STEM_RECONCILER = "reconcile-change-scope-tensions"

_URN_024 = "directive:DIRECTIVE_024"
_URN_025 = "directive:DIRECTIVE_025"
_URN_TACTIC = "tactic:change-apply-smallest-viable-diff"
_URN_RECONCILER = "directive:RECONCILE_CHANGE_SCOPE_TENSIONS"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_config(tmp_path: Path, content: str) -> None:
    """Write a .kittify/config.yaml with the given content."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir(exist_ok=True)
    (kittify / "config.yaml").write_text(content, encoding="utf-8")


def _ctx_with_config(tmp_path: Path, config_yaml: str) -> ProjectContext:
    """Build a fully-populated ProjectContext (real built-in pack) with *config_yaml*."""
    _write_config(tmp_path, config_yaml)
    return ProjectContext.from_repo(tmp_path)


def _make_graph(nodes: list[DRGNode], edges: list[DRGEdge]) -> DRGGraph:
    """Build a minimal, schema-valid DRGGraph for synthetic edge scenarios."""
    return DRGGraph(
        schema_version="1.0",
        generated_at="TEST",
        generated_by="test",
        nodes=nodes,
        edges=edges,
    )


# ---------------------------------------------------------------------------
# Positive assertion (NFR-001)
# ---------------------------------------------------------------------------


@pytest.mark.doctrine
def test_positive_finding_for_co_activated_unreconciled_pair(tmp_path: Path) -> None:
    """Co-activated 024/025 with no reconciler active -> exactly one finding.

    NFR-001: "a no-op checker returning [] fails this requirement" -- this
    test asserts on the actual positive finding content, not merely that the
    call did not raise.
    """
    ctx = _ctx_with_config(
        tmp_path,
        f"activated_directives:\n  - {_STEM_024}\n  - {_STEM_025}\n"
        "activated_tactics: []\n",
    )

    findings = scan_unreconciled_tensions(ctx)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.pair == tuple(sorted((_URN_024, _URN_025)))
    assert finding.resolution_paths == (
        "deactivate one side",
        "activate a reconciler",
    )

    report = run_consistency_check(ctx)
    assert report.unreconciled_tensions == [finding]
    # NFR-001: additive/advisory -- must not flip coherent on its own.
    assert report.coherent is True


# ---------------------------------------------------------------------------
# Non-finding case (US1 Acceptance Scenario 3)
# ---------------------------------------------------------------------------


@pytest.mark.doctrine
def test_non_finding_when_only_one_side_active(tmp_path: Path) -> None:
    """Only one side of a declared tension pair active -> zero findings."""
    ctx = _ctx_with_config(
        tmp_path,
        f"activated_directives:\n  - {_STEM_024}\n"
        "activated_tactics: []\n",
    )

    findings = scan_unreconciled_tensions(ctx)

    assert findings == []


# ---------------------------------------------------------------------------
# SC-002 live before/after (real built-in pack, not a synthetic fixture)
# ---------------------------------------------------------------------------


@pytest.mark.doctrine
def test_sc002_live_before_after_real_built_in_pack(tmp_path: Path) -> None:
    """Deactivating/reactivating the built-in reconciler flips both findings.

    This is the mission's headline acceptance criterion (SC-002): exercised
    against the REAL bundled doctrine pack (024, 025,
    change-apply-smallest-viable-diff, reconcile-change-scope-tensions),
    never a synthetic fixture graph.
    """
    with_reconciler = (
        f"activated_directives:\n"
        f"  - {_STEM_024}\n"
        f"  - {_STEM_025}\n"
        f"  - {_STEM_RECONCILER}\n"
        f"activated_tactics:\n  - {_STEM_TACTIC}\n"
    )
    without_reconciler = (
        f"activated_directives:\n"
        f"  - {_STEM_024}\n"
        f"  - {_STEM_025}\n"
        f"activated_tactics:\n  - {_STEM_TACTIC}\n"
    )

    # 1. Out of the box (reconciler active): coherent, zero findings.
    ctx_before = _ctx_with_config(tmp_path, with_reconciler)
    report_before = run_consistency_check(ctx_before)
    assert report_before.coherent is True
    assert report_before.verification_errors == []
    assert report_before.unreconciled_tensions == []

    # 2. Deactivate the reconciler: both pairs reappear.
    ctx_deactivated = _ctx_with_config(tmp_path, without_reconciler)
    report_deactivated = run_consistency_check(ctx_deactivated)
    pairs = {f.pair for f in report_deactivated.unreconciled_tensions}
    assert pairs == {
        tuple(sorted((_URN_024, _URN_025))),
        tuple(sorted((_URN_025, _URN_TACTIC))),
    }
    # NFR-001: still additive/advisory, coherent stays True.
    assert report_deactivated.coherent is True

    # 3. Reactivate the reconciler: both findings clear again.
    ctx_after = _ctx_with_config(tmp_path, with_reconciler)
    report_after = run_consistency_check(ctx_after)
    assert report_after.unreconciled_tensions == []
    assert report_after.coherent is True


# ---------------------------------------------------------------------------
# Half-reconciled (US2 Acceptance Scenario 2)
# ---------------------------------------------------------------------------


@pytest.mark.doctrine
def test_half_reconciled_pair_still_flagged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A reconciler with only ONE reconciles_tension edge still leaves the pair flagged.

    Uses real doctrine stems/URNs (024, 025, the built-in reconciler) so the
    per-ID activation resolution stays real, but swaps in a synthetic edge
    set via a monkeypatched graph load so only ONE side (024) is bridged --
    something the real, fully-authored built-in graph never exercises on
    its own (WP02's reconciler always bridges both sides).
    """
    half_reconciled_graph = _make_graph(
        nodes=[
            DRGNode(urn=_URN_024, kind=NodeKind.DIRECTIVE),
            DRGNode(urn=_URN_025, kind=NodeKind.DIRECTIVE),
            DRGNode(urn=_URN_RECONCILER, kind=NodeKind.DIRECTIVE),
        ],
        edges=[
            DRGEdge(source=_URN_024, target=_URN_025, relation=Relation.IN_TENSION_WITH),
            DRGEdge(
                source=_URN_RECONCILER,
                target=_URN_024,
                relation=Relation.RECONCILES_TENSION,
            ),
            # NOTE: no reconciles_tension edge to _URN_025 -- half-reconciled.
        ],
    )
    monkeypatch.setattr(
        drg_helpers, "load_validated_graph", lambda repo_root: half_reconciled_graph
    )

    ctx = _ctx_with_config(
        tmp_path,
        f"activated_directives:\n"
        f"  - {_STEM_024}\n"
        f"  - {_STEM_025}\n"
        f"  - {_STEM_RECONCILER}\n"
        "activated_tactics: []\n",
    )

    findings = scan_unreconciled_tensions(ctx)

    assert len(findings) == 1
    assert findings[0].pair == tuple(sorted((_URN_024, _URN_025)))


# ---------------------------------------------------------------------------
# Dedup (Edge Case: symmetric authoring drift, INV-001)
# ---------------------------------------------------------------------------


@pytest.mark.doctrine
def test_dedup_symmetric_authoring(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A tension pair authored (or discoverable) from both directions dedupes to one finding."""
    both_directions_graph = _make_graph(
        nodes=[
            DRGNode(urn=_URN_024, kind=NodeKind.DIRECTIVE),
            DRGNode(urn=_URN_025, kind=NodeKind.DIRECTIVE),
        ],
        edges=[
            DRGEdge(source=_URN_024, target=_URN_025, relation=Relation.IN_TENSION_WITH),
            DRGEdge(source=_URN_025, target=_URN_024, relation=Relation.IN_TENSION_WITH),
        ],
    )
    monkeypatch.setattr(
        drg_helpers, "load_validated_graph", lambda repo_root: both_directions_graph
    )

    ctx = _ctx_with_config(
        tmp_path,
        f"activated_directives:\n  - {_STEM_024}\n  - {_STEM_025}\n"
        "activated_tactics: []\n",
    )

    findings = scan_unreconciled_tensions(ctx)

    assert len(findings) == 1
    assert findings[0].pair == tuple(sorted((_URN_024, _URN_025)))


# ---------------------------------------------------------------------------
# Fail-closed (FR-009)
# ---------------------------------------------------------------------------


@pytest.mark.doctrine
def test_fail_closed_on_scan_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A forced scan error lands in verification_errors, never a silently empty list."""
    ctx = _ctx_with_config(
        tmp_path,
        f"activated_directives:\n  - {_STEM_024}\n  - {_STEM_025}\n"
        "activated_tactics: []\n",
    )

    def _boom(_ctx: ProjectContext) -> list[TensionFinding]:
        raise RuntimeError("simulated tension-scan failure")

    monkeypatch.setattr(consistency_check, "scan_unreconciled_tensions", _boom)

    report = run_consistency_check(ctx)

    assert report.unreconciled_tensions == []
    assert any("tension" in err for err in report.verification_errors), (
        f"Expected a tension-scan failure in verification_errors, got: "
        f"{report.verification_errors}"
    )
    assert report.coherent is False


# ---------------------------------------------------------------------------
# JSON contract shape (SC-001)
# ---------------------------------------------------------------------------


def test_to_json_includes_tension_unreconciled_shape() -> None:
    """``ConsistencyReport.to_json()`` renders the exact contract shape."""
    report = ConsistencyReport(
        coherent=True,
        unreconciled_tensions=[TensionFinding(pair=(_URN_024, _URN_025))],
    )

    payload = report.to_json()

    assert '"type": "tension_unreconciled"' in payload
    assert f'"{_URN_024}"' in payload
    assert f'"{_URN_025}"' in payload
    assert '"deactivate one side"' in payload
    assert '"activate a reconciler"' in payload
