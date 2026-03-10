"""Integration-level guard evaluation tests with real feature directories."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace


from specify_cli.mission_v1.guards import GUARD_REGISTRY
from specify_cli.mission_v1.runner import MissionModel


def _event_data(model: MissionModel):
    """Minimal EventData stand-in with the required ``model`` attribute."""
    return SimpleNamespace(model=model)


class TestArtifactExistsGuard:
    def test_file_present_returns_true(self, tmp_path: Path):
        feature_dir = tmp_path / "feature"
        feature_dir.mkdir()
        (feature_dir / "spec.md").write_text("# Spec", encoding="utf-8")

        guard = GUARD_REGISTRY["artifact_exists"](["spec.md"])
        assert guard(_event_data(MissionModel(feature_dir=feature_dir))) is True

    def test_file_missing_returns_false(self, tmp_path: Path):
        feature_dir = tmp_path / "feature"
        feature_dir.mkdir()
        guard = GUARD_REGISTRY["artifact_exists"](["spec.md"])
        assert guard(_event_data(MissionModel(feature_dir=feature_dir))) is False

    def test_missing_feature_dir_returns_false(self, tmp_path: Path):
        guard = GUARD_REGISTRY["artifact_exists"](["spec.md"])
        assert guard(_event_data(MissionModel(feature_dir=None))) is False


class TestGatePassedGuard:
    def test_gate_event_present_returns_true(self, tmp_path: Path):
        feature_dir = tmp_path / "feature"
        feature_dir.mkdir()
        log = feature_dir / "mission-events.jsonl"
        log.write_text(
            json.dumps({"type": "gate_passed", "name": "G1"}) + "\n",
            encoding="utf-8",
        )
        guard = GUARD_REGISTRY["gate_passed"](["G1"])
        assert guard(_event_data(MissionModel(feature_dir=feature_dir))) is True

    def test_missing_gate_returns_false(self, tmp_path: Path):
        feature_dir = tmp_path / "feature"
        feature_dir.mkdir()
        log = feature_dir / "mission-events.jsonl"
        log.write_text(json.dumps({"type": "other", "name": "X"}) + "\n", encoding="utf-8")
        guard = GUARD_REGISTRY["gate_passed"](["G1"])
        assert guard(_event_data(MissionModel(feature_dir=feature_dir))) is False

    def test_missing_log_returns_false(self, tmp_path: Path):
        feature_dir = tmp_path / "feature"
        feature_dir.mkdir()
        guard = GUARD_REGISTRY["gate_passed"](["G1"])
        assert guard(_event_data(MissionModel(feature_dir=feature_dir))) is False


class TestAllWpStatusGuard:
    def test_all_done_returns_true(self, tmp_path: Path):
        feature_dir = tmp_path / "feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        for wp in ("WP01", "WP02", "WP03"):
            (tasks_dir / f"{wp}.md").write_text("---\nlane: done\n---\n", encoding="utf-8")

        guard = GUARD_REGISTRY["all_wp_status"](["done"])
        assert guard(_event_data(MissionModel(feature_dir=feature_dir))) is True

    def test_any_not_done_returns_false(self, tmp_path: Path):
        feature_dir = tmp_path / "feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "WP01.md").write_text("---\nlane: done\n---\n", encoding="utf-8")
        (tasks_dir / "WP02.md").write_text("---\nlane: doing\n---\n", encoding="utf-8")

        guard = GUARD_REGISTRY["all_wp_status"](["done"])
        assert guard(_event_data(MissionModel(feature_dir=feature_dir))) is False

    def test_missing_tasks_dir_returns_false(self, tmp_path: Path):
        feature_dir = tmp_path / "feature"
        guard = GUARD_REGISTRY["all_wp_status"](["done"])
        assert guard(_event_data(MissionModel(feature_dir=feature_dir))) is False


class TestAnyWpStatusGuard:
    def test_any_done_returns_true(self, tmp_path: Path):
        feature_dir = tmp_path / "feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "WP01.md").write_text("---\nlane: planned\n---\n", encoding="utf-8")
        (tasks_dir / "WP02.md").write_text("---\nlane: done\n---\n", encoding="utf-8")

        guard = GUARD_REGISTRY["any_wp_status"](["done"])
        assert guard(_event_data(MissionModel(feature_dir=feature_dir))) is True

    def test_none_match_returns_false(self, tmp_path: Path):
        feature_dir = tmp_path / "feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "WP01.md").write_text("---\nlane: planned\n---\n", encoding="utf-8")
        (tasks_dir / "WP02.md").write_text("---\nlane: doing\n---\n", encoding="utf-8")

        guard = GUARD_REGISTRY["any_wp_status"](["done"])
        assert guard(_event_data(MissionModel(feature_dir=feature_dir))) is False

    def test_missing_tasks_dir_returns_false(self, tmp_path: Path):
        feature_dir = tmp_path / "feature"
        guard = GUARD_REGISTRY["any_wp_status"](["done"])
        assert guard(_event_data(MissionModel(feature_dir=feature_dir))) is False


class TestInputProvidedGuard:
    def test_input_present_returns_true(self, tmp_path: Path):
        model = MissionModel(feature_dir=tmp_path, inputs={"foo": "bar"})
        guard = GUARD_REGISTRY["input_provided"](["foo"])
        assert guard(_event_data(model)) is True

    def test_input_missing_returns_false(self, tmp_path: Path):
        model = MissionModel(feature_dir=tmp_path, inputs={})
        guard = GUARD_REGISTRY["input_provided"](["foo"])
        assert guard(_event_data(model)) is False


class TestEventCountGuard:
    def test_minimum_met_returns_true(self, tmp_path: Path):
        feature_dir = tmp_path / "feature"
        feature_dir.mkdir()
        log = feature_dir / "mission-events.jsonl"
        log.write_text(
            "\n".join(json.dumps({"type": "checkpoint"}) for _ in range(3)) + "\n",
            encoding="utf-8",
        )
        guard = GUARD_REGISTRY["event_count"](["checkpoint", 3])
        assert guard(_event_data(MissionModel(feature_dir=feature_dir))) is True

    def test_below_minimum_returns_false(self, tmp_path: Path):
        feature_dir = tmp_path / "feature"
        feature_dir.mkdir()
        log = feature_dir / "mission-events.jsonl"
        log.write_text(
            "\n".join(json.dumps({"type": "checkpoint"}) for _ in range(2)) + "\n",
            encoding="utf-8",
        )
        guard = GUARD_REGISTRY["event_count"](["checkpoint", 3])
        assert guard(_event_data(MissionModel(feature_dir=feature_dir))) is False

    def test_missing_log_returns_false(self, tmp_path: Path):
        feature_dir = tmp_path / "feature"
        feature_dir.mkdir()
        guard = GUARD_REGISTRY["event_count"](["checkpoint", 1])
        assert guard(_event_data(MissionModel(feature_dir=feature_dir))) is False
