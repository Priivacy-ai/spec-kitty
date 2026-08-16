"""RED-first coord-topology proof for the merge risk/dependency gates (#3439).

Mission ``partition-authority-residuals-01M021K9`` — WP02 (US2 / FR-003).

On a coordination-topology mission the merge flow hands
:func:`~specify_cli.policy.merge_gates.evaluate_merge_gates` the STATUS-only
``-coord`` husk as ``feature_dir``. ``lanes.json`` (LANE_STATE) and ``tasks/``
(WORK_PACKAGE_TASK) are PRIMARY-partition kinds that are ABSENT on that husk, so
before the fix:

* the risk gate ``read_lanes_json(feature_dir)`` returned ``None`` → **SKIP**
  (silent safety-gate degradation), and
* the dependency gate ``build_dependency_graph(feature_dir)`` saw an **empty
  graph** → every dependency falsely satisfied → **PASS**.

The fix reroutes both PRIMARY reads through the canonical placement seam
(``placement_seam(repo_root, mission_slug).read_dir(<kind>)``) while KEEPING the
STATUS_STATE event read on the coord husk (C-002). This test drives the REAL
``evaluate_merge_gates`` against the un-stubbed ``git worktree`` coord fixture
(NFR-001): no resolver is patched; the PRIMARY-vs-coord routing decision is
exercised inside production code.

Falsifiability (revert the WP02 reroute → RED):

* coord risk gate: ``PASS`` after → ``SKIP`` before.
* coord dependency gate: ``FAIL`` (real edge, incomplete dep) after → ``PASS``
  (empty graph, falsely satisfied) before.

The flat/single-branch control asserts the reroute is a NO-OP off coord
topology (``feature_dir`` already equals the seam-resolved PRIMARY dir), so its
verdicts are identical before and after the fix.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.policy.config import MergeGateConfig
from specify_cli.policy.merge_gates import GateVerdict, evaluate_merge_gates
from tests.integration.coord_topology_fixture import (
    CoordTopologyContext,
    FlatTopologyContext,
    coord_topology_mission,
    flat_topology_mission,
)

# Re-export the fixtures so pytest discovers them in this module.
__all__ = ["coord_topology_mission", "flat_topology_mission"]

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def _add_dependent_wp(feature_dir: Path, repo: Path) -> None:
    """Add a ``WP02`` task depending on ``WP01`` to the PRIMARY tasks dir.

    Gives the dependency graph a real edge so the dependency gate is
    falsifiable: on the coord husk the graph is empty (WP02 has no deps →
    PASS); on PRIMARY the edge WP02→WP01 is present and WP01 is only
    ``claimed`` in the coord status log → FAIL.
    """
    tasks_dir = feature_dir / "tasks"
    (tasks_dir / "WP02.md").write_text(
        "---\nwork_package_id: WP02\ntitle: WP02 dependent\n"
        "dependencies:\n- WP01\nsubtasks: []\n---\n# WP02\n",
        encoding="utf-8",
    )
    subprocess.run(
        ["git", "-C", str(repo), "add", "."], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "test: add WP02 dependent"],
        check=True,
        capture_output=True,
    )


def _gate(result, name: str):
    return next(g for g in result.gates if g.gate_name == name)


def test_coord_risk_gate_reads_primary_lanes_not_husk(
    coord_topology_mission: CoordTopologyContext,
) -> None:
    """Risk gate resolves LANE_STATE via the seam → real data, not a false SKIP."""
    ctx = coord_topology_mission

    result = evaluate_merge_gates(
        ctx.coord_feature_dir,  # what the merge flow hands in on a coord mission
        ctx.slug,
        ["WP01"],
        MergeGateConfig(mode="warn"),
        ctx.repo,
    )

    risk = _gate(result, "risk")
    # AFTER the fix: real lanes.json (PRIMARY) evaluated → PASS (low risk).
    # BEFORE the fix: read off the husk → None → SKIP. This assertion is the
    # red→green signal.
    assert risk.verdict == GateVerdict.PASS, (
        "Risk gate must evaluate real PRIMARY lanes.json on a coord mission, "
        f"not SKIP off the coord husk. Got {risk.verdict}: {risk.details}"
    )


def test_coord_dependency_gate_sees_real_graph_not_empty(
    coord_topology_mission: CoordTopologyContext,
) -> None:
    """Dependency gate builds the graph from PRIMARY tasks/ → real edge honored."""
    ctx = coord_topology_mission
    _add_dependent_wp(ctx.primary_feature_dir, ctx.repo)

    result = evaluate_merge_gates(
        ctx.coord_feature_dir,
        ctx.slug,
        ["WP02"],
        MergeGateConfig(mode="block"),
        ctx.repo,
    )

    dependency = _gate(result, "dependency")
    # AFTER the fix: graph off PRIMARY → WP02 depends on WP01 which is only
    # 'claimed' in the coord status log → FAIL. BEFORE the fix: empty graph off
    # the husk → dependency falsely satisfied → PASS.
    assert dependency.verdict == GateVerdict.FAIL, (
        "Dependency gate must see the real WP02→WP01 edge from PRIMARY tasks/ "
        f"on a coord mission, not an empty husk graph. Got {dependency.verdict}: "
        f"{dependency.details}"
    )
    assert "WP01" in dependency.details


def test_flat_topology_control_unchanged(
    flat_topology_mission: FlatTopologyContext,
) -> None:
    """Non-coord control: reroute is a no-op — verdicts identical before/after.

    On a single-branch mission ``feature_dir`` already equals the seam-resolved
    PRIMARY dir, so routing the LANE_STATE / WORK_PACKAGE_TASK reads through the
    seam resolves to the same directory. The risk gate sees real lanes (PASS)
    and the dependency gate sees the real WP02→WP01 edge (FAIL) both before and
    after the WP02 change.
    """
    ctx = flat_topology_mission
    _add_dependent_wp(ctx.primary_feature_dir, ctx.repo)

    result = evaluate_merge_gates(
        ctx.primary_feature_dir,
        ctx.slug,
        ["WP02"],
        MergeGateConfig(mode="block"),
        ctx.repo,
    )

    assert _gate(result, "risk").verdict == GateVerdict.PASS
    assert _gate(result, "dependency").verdict == GateVerdict.FAIL
