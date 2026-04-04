"""Tests for merge gate evaluation engine."""

import json
import subprocess

import pytest

from specify_cli.policy.config import MergeGateConfig
from specify_cli.policy.merge_gates import (
    GateVerdict,
    MergeGateEvaluation,
    evaluate_merge_gates,
)


def _setup_feature(tmp_path, wp_ids, wp_lanes=None):
    """Create minimal feature directory with event log."""
    feature_dir = tmp_path / "kitty-specs" / "010-feat"
    feature_dir.mkdir(parents=True)
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir()

    # Create WP files with dependencies.
    for wp_id in wp_ids:
        (tasks_dir / f"{wp_id}-test.md").write_text(
            f"---\nwork_package_id: {wp_id}\ndependencies: []\n---\nBody\n"
        )

    # Create event log with lane transitions.
    if wp_lanes:
        events = []
        for wp_id, lane in wp_lanes.items():
            events.append({
                "event_id": f"evt-{wp_id}",
                "feature_slug": "010-feat",
                "wp_id": wp_id,
                "from_lane": "planned",
                "to_lane": lane,
                "at": "2026-04-03T12:00:00Z",
                "actor": "test",
                "force": False,
                "execution_mode": "worktree",
            })
        events_path = feature_dir / "status.events.jsonl"
        events_path.write_text(
            "\n".join(json.dumps(e, sort_keys=True) for e in events) + "\n"
        )

    return feature_dir


class TestEvidenceGate:
    def test_all_approved_passes(self, tmp_path):
        feature_dir = _setup_feature(
            tmp_path, ["WP01", "WP02"],
            wp_lanes={"WP01": "approved", "WP02": "done"},
        )
        result = evaluate_merge_gates(
            feature_dir, "010-feat", ["WP01", "WP02"],
            MergeGateConfig(mode="block"), tmp_path,
        )
        evidence_gate = next(g for g in result.gates if g.gate_name == "evidence")
        assert evidence_gate.verdict == GateVerdict.PASS

    def test_missing_approval_fails(self, tmp_path):
        feature_dir = _setup_feature(
            tmp_path, ["WP01", "WP02"],
            wp_lanes={"WP01": "approved", "WP02": "in_progress"},
        )
        result = evaluate_merge_gates(
            feature_dir, "010-feat", ["WP01", "WP02"],
            MergeGateConfig(mode="block"), tmp_path,
        )
        evidence_gate = next(g for g in result.gates if g.gate_name == "evidence")
        assert evidence_gate.verdict == GateVerdict.FAIL
        assert evidence_gate.blocking is True

    def test_missing_approval_warns_in_warn_mode(self, tmp_path):
        feature_dir = _setup_feature(
            tmp_path, ["WP01"],
            wp_lanes={"WP01": "in_progress"},
        )
        result = evaluate_merge_gates(
            feature_dir, "010-feat", ["WP01"],
            MergeGateConfig(mode="warn"), tmp_path,
        )
        evidence_gate = next(g for g in result.gates if g.gate_name == "evidence")
        assert evidence_gate.verdict == GateVerdict.FAIL
        assert evidence_gate.blocking is False


class TestOverallEvaluation:
    def test_disabled_gates_pass(self, tmp_path):
        feature_dir = _setup_feature(tmp_path, ["WP01"])
        result = evaluate_merge_gates(
            feature_dir, "010-feat", ["WP01"],
            MergeGateConfig(enabled=False), tmp_path,
        )
        assert result.overall_pass is True
        assert len(result.gates) == 0

    def test_off_mode_passes(self, tmp_path):
        feature_dir = _setup_feature(tmp_path, ["WP01"])
        result = evaluate_merge_gates(
            feature_dir, "010-feat", ["WP01"],
            MergeGateConfig(mode="off"), tmp_path,
        )
        assert result.overall_pass is True

    def test_blocking_failure_blocks_overall(self, tmp_path):
        feature_dir = _setup_feature(
            tmp_path, ["WP01"],
            wp_lanes={"WP01": "in_progress"},
        )
        result = evaluate_merge_gates(
            feature_dir, "010-feat", ["WP01"],
            MergeGateConfig(mode="block"), tmp_path,
        )
        assert result.overall_pass is False

    def test_to_dict(self, tmp_path):
        feature_dir = _setup_feature(
            tmp_path, ["WP01"],
            wp_lanes={"WP01": "approved"},
        )
        result = evaluate_merge_gates(
            feature_dir, "010-feat", ["WP01"],
            MergeGateConfig(mode="warn"), tmp_path,
        )
        d = result.to_dict()
        assert "overall_pass" in d
        assert "gates" in d
        assert "warnings" in d


class TestDependencyGateReadOnly:
    def test_evaluate_merge_gates_does_not_create_status_json(self, tmp_path):
        feature_dir = _setup_feature(
            tmp_path, ["WP01"], wp_lanes={"WP01": "approved"},
        )

        result = evaluate_merge_gates(
            feature_dir, "010-feat", ["WP01"],
            MergeGateConfig(mode="block"), tmp_path,
        )

        dependency_gate = next(g for g in result.gates if g.gate_name == "dependency")
        assert dependency_gate.verdict == GateVerdict.PASS
        assert not (feature_dir / "status.json").exists()

    def test_evaluate_merge_gates_does_not_dirty_tracked_status_json(self, tmp_path):
        feature_dir = _setup_feature(
            tmp_path, ["WP01"], wp_lanes={"WP01": "approved"},
        )
        repo_root = tmp_path

        subprocess.run(["git", "init", str(repo_root)], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(repo_root), "config", "user.email", "test@test.com"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(repo_root), "config", "user.name", "Test"],
            check=True,
            capture_output=True,
        )

        from specify_cli.status.reducer import materialize

        materialize(feature_dir)
        subprocess.run(["git", "-C", str(repo_root), "add", "-A"], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(repo_root), "commit", "-m", "init"],
            check=True,
            capture_output=True,
        )

        result = evaluate_merge_gates(
            feature_dir, "010-feat", ["WP01"],
            MergeGateConfig(mode="block"), tmp_path,
        )

        dependency_gate = next(g for g in result.gates if g.gate_name == "dependency")
        assert dependency_gate.verdict == GateVerdict.PASS

        git_status = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert git_status == ""
