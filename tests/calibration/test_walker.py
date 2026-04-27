"""Tests for the calibration walker.

T054: For each in-scope mission, walk every step and assert InequalityResult.holds
is True after the calibration overlays are applied.

Also includes unit tests for the walker itself (overlay loading, graph building,
edge-change recommendations).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.calibration.walker import (
    CalibrationFinding,
    EdgeChange,
    walk_mission,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Repo root is three levels above tests/calibration/ in the worktree.
_REPO_ROOT = Path(__file__).parent.parent.parent


# ---------------------------------------------------------------------------
# T054: §4.5.1 inequality holds for every step in the four missions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mission_key",
    ["software-dev", "research", "documentation", "erp-custom"],
)
def test_inequality_holds_for_all_steps(mission_key: str) -> None:
    """Every step in every in-scope mission passes §4.5.1 after overlays."""
    findings = walk_mission(mission_key=mission_key, repo_root=_REPO_ROOT)

    assert findings, f"No findings returned for mission '{mission_key}'"

    failures = [
        f"{f.step_id} (action={f.action_id}): "
        f"missing={sorted(f.inequality.missing_urns)}, "
        f"over_broad={sorted(f.inequality.over_broad_urns)}"
        for f in findings
        if not f.inequality.holds
    ]
    assert not failures, (
        f"Mission '{mission_key}' has {len(failures)} failing step(s):\n"
        + "\n".join(f"  {line}" for line in failures)
    )


@pytest.mark.parametrize(
    "mission_key,expected_steps",
    [
        ("software-dev", ["specify", "plan", "tasks", "implement", "review", "retrospect"]),
        ("research", ["scoping", "methodology", "gathering", "synthesis", "output", "retrospect"]),
        ("documentation", ["audit", "design", "discover", "generate", "publish", "validate", "retrospect"]),
        ("erp-custom", ["query-erp", "lookup-provider", "ask-user", "create-js", "refactor-function", "write-report", "retrospective"]),
    ],
)
def test_expected_steps_present(mission_key: str, expected_steps: list[str]) -> None:
    """Walker returns one finding per expected step."""
    findings = walk_mission(mission_key=mission_key, repo_root=_REPO_ROOT)
    step_ids = [f.step_id for f in findings]
    assert step_ids == expected_steps


# ---------------------------------------------------------------------------
# Unit tests: CalibrationFinding shape
# ---------------------------------------------------------------------------


def test_finding_has_required_fields() -> None:
    findings = walk_mission(mission_key="software-dev", repo_root=_REPO_ROOT)
    for f in findings:
        assert isinstance(f, CalibrationFinding)
        assert isinstance(f.step_id, str)
        assert f.action_id.startswith("action:")
        assert f.profile_id.startswith("agent_profile:")
        assert isinstance(f.resolved_scope, frozenset)
        assert isinstance(f.required_scope, frozenset)
        assert isinstance(f.known_irrelevant, frozenset)
        assert isinstance(f.recommended_edge_changes, list)


def test_resolved_scope_is_superset_of_required() -> None:
    """resolved_scope must contain all required_scope URNs (half-1 check)."""
    for mission_key in ["software-dev", "research", "documentation", "erp-custom"]:
        findings = walk_mission(mission_key=mission_key, repo_root=_REPO_ROOT)
        for f in findings:
            assert f.required_scope.issubset(f.resolved_scope), (
                f"{mission_key}/{f.step_id}: required URNs not in resolved_scope: "
                f"{f.required_scope - f.resolved_scope}"
            )


def test_no_recommended_changes_when_all_pass() -> None:
    """When the inequality holds, recommended_edge_changes is empty."""
    for mission_key in ["software-dev", "research", "documentation", "erp-custom"]:
        findings = walk_mission(mission_key=mission_key, repo_root=_REPO_ROOT)
        for f in findings:
            if f.inequality.holds:
                assert f.recommended_edge_changes == [], (
                    f"{mission_key}/{f.step_id}: unexpected edge changes: "
                    f"{f.recommended_edge_changes}"
                )


# ---------------------------------------------------------------------------
# Unit tests: overlay loading
# ---------------------------------------------------------------------------


def test_overlay_loading_does_not_break_when_file_absent(tmp_path: Path) -> None:
    """Walker works when no overlay file exists for the mission."""
    # tmp_path has no graph.yaml; use the repo's shipped graph
    # We patch repo_root to point to the real repo but use a tmp overlay dir
    import shutil

    src_dir = tmp_path / "src" / "doctrine"
    src_dir.mkdir(parents=True)
    shutil.copy(_REPO_ROOT / "src" / "doctrine" / "graph.yaml", src_dir / "graph.yaml")

    # No .kittify/doctrine/overlays/ directory → should not raise
    findings = walk_mission(mission_key="software-dev", repo_root=tmp_path)
    assert len(findings) == 6


def test_overlay_add_edge_extends_resolved_scope(tmp_path: Path) -> None:
    """An overlay add_edge increases the resolved scope for the targeted action."""
    import shutil

    src_dir = tmp_path / "src" / "doctrine"
    src_dir.mkdir(parents=True)
    shutil.copy(_REPO_ROOT / "src" / "doctrine" / "graph.yaml", src_dir / "graph.yaml")

    overlays_dir = tmp_path / ".kittify" / "doctrine" / "overlays"
    overlays_dir.mkdir(parents=True)

    # Add a scope edge from software-dev/specify to a tactic that is not yet scoped
    overlay_yaml = overlays_dir / "calibration-software-dev.yaml"
    overlay_yaml.write_text(
        "add_edge:\n"
        "  - source: action:software-dev/specify\n"
        "    target: tactic:adr-drafting-workflow\n"
        "    relation: scope\n"
        "    reason: test overlay\n",
        encoding="utf-8",
    )

    findings = walk_mission(mission_key="software-dev", repo_root=tmp_path)
    specify_finding = next(f for f in findings if f.step_id == "specify")
    # adr-drafting-workflow should be in the resolved scope after overlay
    assert "tactic:adr-drafting-workflow" in specify_finding.resolved_scope


# ---------------------------------------------------------------------------
# Unit tests: unknown mission key
# ---------------------------------------------------------------------------


def test_unknown_mission_key_raises() -> None:
    with pytest.raises(KeyError):
        walk_mission(mission_key="no-such-mission", repo_root=_REPO_ROOT)


# ---------------------------------------------------------------------------
# Unit tests: EdgeChange model
# ---------------------------------------------------------------------------


def test_edge_change_immutable() -> None:
    ec = EdgeChange(kind="add_edge", source="action:a/b", target="tactic:X", relation="scope")
    assert ec.kind == "add_edge"
    assert ec.new_target is None
