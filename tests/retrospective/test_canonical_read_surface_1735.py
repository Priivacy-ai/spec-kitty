"""Canonical status-read surface tests for the retrospective gate and CLI (FR-009 / #1735).

WP05 (coordination-merge-stabilization-01KTXRVR, contract §A-r2): the
retrospective completion gate (``retrospective/gate.py``) and the retrospect
command surface (``cli/commands/agent_retrospect.py``) must read status events
through the single canonical surface resolver
(:func:`specify_cli.coordination.surface_resolver.resolve_status_surface`),
never via a ``resolved.feature_dir``-anchored direct file read.

Divergence fixture: a coordination-topology mission whose authoritative
``status.events.jsonl`` exists ONLY in the coordination worktree. The primary
checkout's feature dir carries no event log at all. A reader still anchored on
the primary feature dir sees zero events (the #1735 split-brain); a reader
routed through ``resolve_status_surface`` sees the coord-worktree events.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.cli.commands.agent_retrospect import (
    _mission_artifacts_sufficient_for_empty_record,
)
from specify_cli.retrospective.gate import is_completion_allowed
from specify_cli.retrospective.schema import Mode, ModeSourceSignal

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_MISSION_SLUG = "coord-read-mission"
_MISSION_ID = "01KTXRVRTESTGATE0000000001"  # 26-char ULID (test fixture)
_MID8 = _MISSION_ID[:8]
_COORD_BRANCH = f"kitty/mission-{_MISSION_SLUG}-{_MID8}"


def _mode_autonomous() -> Mode:
    return Mode(
        value="autonomous",
        source_signal=ModeSourceSignal(kind="explicit_flag", evidence="autonomous"),
    )


def _write_meta(mission_dir: Path) -> None:
    mission_dir.mkdir(parents=True, exist_ok=True)
    (mission_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": _MISSION_ID,
                "mid8": _MID8,
                "mission_slug": _MISSION_SLUG,
                "mission_number": None,
                "mission_type": "software-dev",
                "coordination_branch": _COORD_BRANCH,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _build_coord_topology_repo(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Build a coord-topology mission with a divergent status surface.

    Returns ``(repo_root, primary_feature_dir, coord_feature_dir)``. The
    authoritative event log exists ONLY under the coordination worktree; the
    primary feature dir has no ``status.events.jsonl`` at all.
    """
    repo_root = tmp_path / "repo"
    primary_dir = repo_root / "kitty-specs" / _MISSION_SLUG
    _write_meta(primary_dir)

    coord_dir = (
        repo_root
        / ".worktrees"
        / f"{_MISSION_SLUG}-{_MID8}-coord"
        / "kitty-specs"
        / f"{_MISSION_SLUG}-{_MID8}"
    )
    _write_meta(coord_dir)

    return repo_root, primary_dir, coord_dir


def _retro_completed_envelope() -> dict[str, object]:
    # canonical-producer-exempt: #1735 -- legacy retrospective envelope fixture targets read-surface routing.
    return {
        "actor": {"id": "test-operator", "kind": "human", "profile_id": None},
        "at": "2026-06-12T10:00:00+00:00",
        "event_id": "01KTXRVRTESTGATE00000000E1",
        "event_name": "retrospective.completed",
        "mid8": _MID8,
        "mission_id": _MISSION_ID,
        "mission_slug": _MISSION_SLUG,
        "payload": {},
    }


def _status_event(wp_id: str, from_lane: str, to_lane: str, event_id: str, at: str) -> dict[str, object]:
    return {
        "actor": "test-fixture",
        "at": at,
        "event_id": event_id,
        "evidence": None,
        "execution_mode": "worktree",
        "force": True,
        "from_lane": from_lane,
        "mission_id": _MISSION_ID,
        "mission_slug": _MISSION_SLUG,
        "reason": "coord-surface divergence fixture",
        "review_ref": None,
        "to_lane": to_lane,
        "wp_id": wp_id,
    }


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# T024 — retrospective completion gate routes through resolve_status_surface
# ---------------------------------------------------------------------------


def test_gate_sees_coord_worktree_events_when_surfaces_diverge(tmp_path: Path) -> None:
    """FR-009 / #1735 (T024): the completion gate must read the coord surface.

    The ``retrospective.completed`` event is written ONLY to the coordination
    worktree's event log. A gate still reading
    ``feature_dir / "status.events.jsonl"`` directly sees no events and blocks
    with ``missing_completion_autonomous`` (the pre-fix behavior); the routed
    gate sees the coord event and allows completion.
    """
    repo_root, primary_dir, coord_dir = _build_coord_topology_repo(tmp_path)
    _write_jsonl(coord_dir / "status.events.jsonl", [_retro_completed_envelope()])

    # Divergence sanity: the primary feature dir has NO event log, so the only
    # way the gate can see the completed event is via the coord surface.
    assert not (primary_dir / "status.events.jsonl").exists()

    decision = is_completion_allowed(
        _MISSION_ID,
        feature_dir=primary_dir,
        repo_root=repo_root,
        mode_override=_mode_autonomous(),
    )

    assert decision.allow_completion is True, (
        "#1735 regression: the retrospective completion gate did not see the "
        "retrospective.completed event in the coordination worktree — it is "
        "still reading events through the primary checkout's feature_dir "
        f"instead of resolve_status_surface (reason: {decision.reason.code})."
    )
    assert decision.reason.code == "completed_present"


def test_gate_falls_back_to_feature_dir_for_unresolvable_mission(tmp_path: Path) -> None:
    """A mission with no resolvable meta.json keeps the historical behavior:
    the passed ``feature_dir`` is the surface (legacy/test missions)."""
    feature_dir = tmp_path / "feature"
    _write_jsonl(feature_dir / "status.events.jsonl", [_retro_completed_envelope()])

    decision = is_completion_allowed(
        _MISSION_ID,
        feature_dir=feature_dir,
        repo_root=tmp_path,
        mode_override=_mode_autonomous(),
    )

    assert decision.allow_completion is True
    assert decision.reason.code == "completed_present"


# ---------------------------------------------------------------------------
# T025 — agent retrospect synthesize artifact check routes status reads
# ---------------------------------------------------------------------------


def _write_primary_artifacts(primary_dir: Path) -> None:
    primary_dir.mkdir(parents=True, exist_ok=True)
    (primary_dir / "spec.md").write_text("# spec\n", encoding="utf-8")
    (primary_dir / "plan.md").write_text("# plan\n", encoding="utf-8")
    (primary_dir / "tasks.md").write_text("# tasks\n", encoding="utf-8")
    tasks_dir = primary_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / "WP01.md").write_text("# WP01\n", encoding="utf-8")


def test_artifact_sufficiency_reads_coord_worktree_events(tmp_path: Path) -> None:
    """FR-009 / #1735 (T025): the empty-record artifact check must read the
    coord surface.

    Mission artifacts (spec/plan/tasks) live in the primary checkout, but the
    WP status events that prove every WP is approved/done exist ONLY in the
    coordination worktree. A reader anchored on ``resolved.feature_dir`` sees
    zero events and reports the artifacts insufficient (pre-fix behavior); the
    routed reader sees the coord events and reports them sufficient.
    """
    repo_root, primary_dir, coord_dir = _build_coord_topology_repo(tmp_path)
    _write_primary_artifacts(primary_dir)
    _write_jsonl(
        coord_dir / "status.events.jsonl",
        [
            _status_event(
                "WP01", "planned", "done",
                event_id="01KTXRVRTESTGATE00000000S1",
                at="2026-06-12T09:00:00+00:00",
            ),
        ],
    )

    # Divergence sanity: no event log in the primary feature dir.
    assert not (primary_dir / "status.events.jsonl").exists()

    assert _mission_artifacts_sufficient_for_empty_record(
        primary_dir, repo_root=repo_root, mission_slug=_MISSION_SLUG
    ) is True, (
        "#1735 regression: the retrospect artifact-sufficiency check did not "
        "see the WP status events in the coordination worktree — it is still "
        "reading events through resolved.feature_dir instead of "
        "resolve_status_surface."
    )


def test_artifact_sufficiency_falls_back_to_feature_dir_for_unresolvable_mission(
    tmp_path: Path,
) -> None:
    """A mission with no resolvable meta.json keeps the historical behavior:
    events are read from the passed feature dir (legacy/test missions)."""
    feature_dir = tmp_path / "kitty-specs" / "legacy-mission"
    _write_primary_artifacts(feature_dir)
    _write_jsonl(
        feature_dir / "status.events.jsonl",
        [
            _status_event(
                "WP01", "planned", "done",
                event_id="01KTXRVRTESTGATE00000000S2",
                at="2026-06-12T09:00:00+00:00",
            ),
        ],
    )

    assert _mission_artifacts_sufficient_for_empty_record(
        feature_dir, repo_root=tmp_path, mission_slug="legacy-mission-unresolvable"
    ) is True


def test_artifact_sufficiency_false_when_no_events_anywhere(tmp_path: Path) -> None:
    """Negative control: with no events on ANY surface the check stays False."""
    repo_root, primary_dir, _coord_dir = _build_coord_topology_repo(tmp_path)
    _write_primary_artifacts(primary_dir)

    assert _mission_artifacts_sufficient_for_empty_record(
        primary_dir, repo_root=repo_root, mission_slug=_MISSION_SLUG
    ) is False
