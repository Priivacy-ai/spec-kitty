"""End-to-end mission loading and execution tests (v1 + v0)."""

from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from specify_cli.mission_v1 import PhaseMission, StateMachineMission, load_mission


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")


def test_v1_mission_e2e(tmp_path: Path):
    """Full v1 mission flow with guard blocking until artifact exists."""
    mission_dir = tmp_path / "test-mission"
    _write_yaml(
        mission_dir / "mission.yaml",
        {
            "mission": {
                "name": "test",
                "version": "1.0.0",
                "description": "E2E test",
            },
            "initial": "alpha",
            "states": [
                {"name": "alpha"},
                {"name": "beta"},
                {"name": "done"},
            ],
            "transitions": [
                {
                    "trigger": "advance",
                    "source": "alpha",
                    "dest": "beta",
                    "conditions": ['artifact_exists("required.txt")'],
                },
                {"trigger": "advance", "source": "beta", "dest": "done"},
                {"trigger": "rollback", "source": "beta", "dest": "alpha"},
            ],
        },
    )

    feature_dir = tmp_path / "feature"
    feature_dir.mkdir()

    mission = load_mission(mission_dir, feature_dir=feature_dir)
    assert isinstance(mission, StateMachineMission)
    assert mission.state == "alpha"

    # Guard should block when artifact is missing
    assert mission.trigger("advance") is False
    assert mission.state == "alpha"

    # Satisfy guard
    (feature_dir / "required.txt").write_text("exists", encoding="utf-8")

    mission.trigger("advance")
    assert mission.state == "beta"

    # Rollback path should work without guards
    mission.trigger("rollback")
    assert mission.state == "alpha"


def test_v0_mission_e2e(tmp_path: Path):
    """v0 mission loads via PhaseMission and progresses linearly."""
    mission_dir = tmp_path / "legacy-mission"
    _write_yaml(
        mission_dir / "mission.yaml",
        {
            "name": "Legacy Test",
            "description": "v0 format",
            "version": "1.0.0",
            "domain": "software",
            "workflow": {
                "phases": [
                    {"name": "alpha", "description": "First phase"},
                    {"name": "beta", "description": "Second phase"},
                    {"name": "gamma", "description": "Third phase"},
                ]
            },
            "artifacts": {"required": [], "optional": []},
        },
    )

    mission = load_mission(mission_dir)
    assert isinstance(mission, PhaseMission)
    assert mission.state == "alpha"

    mission.trigger("advance")
    assert mission.state == "beta"

    mission.trigger("advance")
    assert mission.state == "gamma"

    mission.trigger("advance")
    assert mission.state == "done"


def test_all_missions_coexist(tmp_path: Path):
    """Ensure bundled missions (3 v1 + 1 v0) load together."""
    missions_src = Path("src/specify_cli/missions")
    mission_names = ["software-dev", "research", "plan", "documentation"]

    loaded = []
    for name in mission_names:
        src = missions_src / name
        dst = tmp_path / name
        shutil.copytree(src, dst)
        mission = load_mission(dst)
        loaded.append(mission)

        # basic sanity
        assert mission.name != ""
        assert mission.state is not None
        assert len(mission.get_states()) > 0

    # Verify we have both v1 and v0 types represented
    assert any(isinstance(m, StateMachineMission) for m in loaded)
    assert any(isinstance(m, PhaseMission) for m in loaded)

