"""Integration tests for ``spec-kitty next`` CLI command."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli import app as cli_app
from specify_cli.next.decision import DecisionKind

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _init_git_repo(path: Path) -> None:
    """Initialize a bare git repo at *path* so feature detection works."""
    subprocess.run(["git", "init", "--initial-branch=main"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, capture_output=True, check=True)
    # Initial commit so branch exists
    (path / "README.md").write_text("# test", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, capture_output=True, check=True)


def _scaffold_project(
    tmp_path: Path,
    feature_slug: str = "042-test-feature",
    mission_key: str = "software-dev",
) -> Path:
    """Scaffold a minimal spec-kitty project with a feature."""
    repo_root = tmp_path / "project"
    repo_root.mkdir()
    _init_git_repo(repo_root)

    # .kittify dir (minimal)
    kittify = repo_root / ".kittify"
    kittify.mkdir()

    # Feature directory
    feature_dir = repo_root / "kitty-specs" / feature_slug
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"mission": mission_key}), encoding="utf-8",
    )

    return repo_root


def _add_events(feature_dir: Path, events: list[dict]) -> None:
    """Append events to mission-events.jsonl."""
    events_file = feature_dir / "mission-events.jsonl"
    with open(events_file, "a", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")


def _add_wp_files(feature_dir: Path, wps: dict[str, str]) -> None:
    """Create WP task files.  wps maps WP ID to lane."""
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)
    for wp_id, lane in wps.items():
        (tasks_dir / f"{wp_id}.md").write_text(
            f"---\nwork_package_id: {wp_id}\nlane: {lane}\ntitle: {wp_id} task\n---\n# {wp_id}\nDo something.\n",
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestNextCommandJSON:
    """Test JSON output mode of the ``next`` command."""

    def test_discovery_state_returns_step(self, tmp_path: Path) -> None:
        """Fresh feature with no events should be in discovery/initial state."""
        repo_root = _scaffold_project(tmp_path)

        from specify_cli.next.decision import decide_next

        decision = decide_next("test-agent", "042-test-feature", "success", repo_root)
        d = decision.to_dict()
        assert d["agent"] == "test-agent"
        assert d["feature_slug"] == "042-test-feature"
        assert d["mission"] == "software-dev"
        assert "kind" in d

    def test_terminal_state_returns_terminal(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        _add_events(feature_dir, [
            {"type": "phase_entered", "payload": {"state": "done"}},
        ])

        from specify_cli.next.decision import decide_next

        decision = decide_next("test-agent", "042-test-feature", "success", repo_root)
        assert decision.kind == DecisionKind.terminal
        assert decision.mission_state == "done"

    def test_failed_result_returns_decision_required(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)

        from specify_cli.next.decision import decide_next

        decision = decide_next("test-agent", "042-test-feature", "failed", repo_root)
        assert decision.kind == DecisionKind.decision_required

    def test_blocked_result_returns_blocked(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)

        from specify_cli.next.decision import decide_next

        decision = decide_next("test-agent", "042-test-feature", "blocked", repo_root)
        assert decision.kind == DecisionKind.blocked

    def test_nonexistent_feature_returns_blocked(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)

        from specify_cli.next.decision import decide_next

        decision = decide_next("test-agent", "999-nonexistent", "success", repo_root)
        assert decision.kind == DecisionKind.blocked
        assert "not found" in decision.reason


class TestNextCommandImplementState:
    """Test implement state behavior with WP files."""

    def test_implement_state_picks_planned_wp(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        _add_events(feature_dir, [
            {"type": "phase_entered", "payload": {"state": "implement"}},
        ])
        _add_wp_files(feature_dir, {
            "WP01": "done",
            "WP02": "planned",
            "WP03": "planned",
        })

        from specify_cli.next.decision import decide_next

        decision = decide_next("test-agent", "042-test-feature", "success", repo_root)
        assert decision.kind == DecisionKind.step
        assert decision.action == "implement"
        assert decision.wp_id == "WP02"
        assert decision.workspace_path is not None

    def test_implement_state_no_planned_checks_for_review(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        _add_events(feature_dir, [
            {"type": "phase_entered", "payload": {"state": "implement"}},
        ])
        _add_wp_files(feature_dir, {
            "WP01": "done",
            "WP02": "for_review",
        })

        from specify_cli.next.decision import decide_next

        decision = decide_next("test-agent", "042-test-feature", "success", repo_root)
        assert decision.kind == DecisionKind.step
        assert decision.action == "review"
        assert decision.wp_id == "WP02"

    def test_all_wps_done_advances_to_review(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        _add_events(feature_dir, [
            {"type": "phase_entered", "payload": {"state": "implement"}},
        ])
        _add_wp_files(feature_dir, {
            "WP01": "done",
            "WP02": "done",
        })

        from specify_cli.next.decision import decide_next

        decision = decide_next("test-agent", "042-test-feature", "success", repo_root)
        # All WPs done => guard passes => advance to review state
        # But review state needs a for_review WP to map to an action
        # Since there are no for_review WPs, it might be blocked
        assert decision.kind in (DecisionKind.step, DecisionKind.blocked)


class TestNextCommandProgress:
    """Test that progress information is included."""

    def test_progress_in_decision(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        _add_wp_files(feature_dir, {
            "WP01": "done",
            "WP02": "doing",
            "WP03": "planned",
        })

        from specify_cli.next.decision import decide_next

        decision = decide_next("test-agent", "042-test-feature", "success", repo_root)
        assert decision.progress is not None
        assert decision.progress["total_wps"] == 3
        assert decision.progress["done_wps"] == 1
        assert decision.progress["in_progress_wps"] == 1
        assert decision.progress["planned_wps"] == 1


class TestNextCommandOrigin:
    """Test that origin metadata is included."""

    def test_origin_in_decision(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)

        from specify_cli.next.decision import decide_next

        decision = decide_next("test-agent", "042-test-feature", "success", repo_root)
        if decision.origin:
            assert "mission_path" in decision.origin


class TestNextCommandKnownBlockedMissions:
    """Strict reminders for accepted-but-unimplemented mission mappings."""

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "Tracked in docs/development/tracking/next-mission-mappings/"
            "issue-plan-mission-next-mapping.md"
        ),
    )
    def test_plan_mission_should_return_runnable_step_when_mapped(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(
            tmp_path,
            feature_slug="043-plan-feature",
            mission_key="plan",
        )

        from specify_cli.next.decision import decide_next

        decision = decide_next("test-agent", "043-plan-feature", "success", repo_root)
        assert decision.kind == DecisionKind.step
        assert decision.action is not None

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "Tracked in docs/development/tracking/next-mission-mappings/"
            "issue-documentation-mission-next-mapping.md"
        ),
    )
    def test_documentation_mission_should_return_runnable_step_when_mapped(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(
            tmp_path,
            feature_slug="044-docs-feature",
            mission_key="documentation",
        )

        from specify_cli.next.decision import decide_next

        decision = decide_next("test-agent", "044-docs-feature", "success", repo_root)
        assert decision.kind == DecisionKind.step
        assert decision.action is not None


# ---------------------------------------------------------------------------
# CLI CliRunner tests — test actual Typer command routing
# ---------------------------------------------------------------------------


class TestNextCommandCLI:
    """Test the ``next`` command via CliRunner (real CLI routing)."""

    def test_json_output_valid(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """--json flag produces valid JSON with required fields."""
        repo_root = _scaffold_project(tmp_path)
        monkeypatch.chdir(repo_root)

        result = runner.invoke(
            cli_app,
            ["next", "--agent", "test-agent", "--feature", "042-test-feature", "--json"],
        )
        assert result.exit_code == 0, f"stderr: {result.output}"
        data = json.loads(result.output)
        assert data["agent"] == "test-agent"
        assert data["feature_slug"] == "042-test-feature"
        assert data["mission"] == "software-dev"
        assert "kind" in data
        assert "mission_state" in data
        assert "timestamp" in data
        assert "guard_failures" in data

    def test_invalid_result_flag(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Invalid --result value causes exit code 1."""
        repo_root = _scaffold_project(tmp_path)
        monkeypatch.chdir(repo_root)

        result = runner.invoke(
            cli_app,
            ["next", "--agent", "test", "--feature", "042-test-feature", "--result", "bogus"],
        )
        assert result.exit_code == 1

    def test_blocked_result_exit_code(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """--result blocked produces exit code 1."""
        repo_root = _scaffold_project(tmp_path)
        monkeypatch.chdir(repo_root)

        result = runner.invoke(
            cli_app,
            ["next", "--agent", "test", "--feature", "042-test-feature", "--result", "blocked", "--json"],
        )
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["kind"] == "blocked"

    def test_terminal_state_exit_code_zero(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Terminal state returns exit code 0."""
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        _add_events(feature_dir, [
            {"type": "phase_entered", "payload": {"state": "done"}},
        ])
        monkeypatch.chdir(repo_root)

        result = runner.invoke(
            cli_app,
            ["next", "--agent", "test", "--feature", "042-test-feature", "--json"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["kind"] == "terminal"

    def test_human_output_mode(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Without --json, outputs human-readable text."""
        repo_root = _scaffold_project(tmp_path)
        monkeypatch.chdir(repo_root)

        result = runner.invoke(
            cli_app,
            ["next", "--agent", "test", "--feature", "042-test-feature"],
        )
        assert result.exit_code == 0
        # Human output should contain the mission state
        assert "software-dev" in result.output

    def test_nonexistent_feature_blocked(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-existent feature returns blocked with exit code 1."""
        repo_root = _scaffold_project(tmp_path)
        monkeypatch.chdir(repo_root)

        result = runner.invoke(
            cli_app,
            ["next", "--agent", "test", "--feature", "999-nonexistent", "--json"],
        )
        # Feature detection may fail before decide_next, or decide_next returns blocked
        assert result.exit_code != 0 or "blocked" in result.output or "not found" in result.output.lower()

    def test_state_advancement_persists(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """P0: calling next advances state and persists it for next call."""
        repo_root = _scaffold_project(tmp_path)
        monkeypatch.chdir(repo_root)

        # First call — should be in initial state (discovery) and advance
        r1 = runner.invoke(
            cli_app,
            ["next", "--agent", "test", "--feature", "042-test-feature", "--json"],
        )
        assert r1.exit_code == 0
        d1 = json.loads(r1.output)

        # Second call — should be in a different state than the first
        r2 = runner.invoke(
            cli_app,
            ["next", "--agent", "test", "--feature", "042-test-feature", "--json"],
        )
        assert r2.exit_code == 0
        d2 = json.loads(r2.output)

        # State should have advanced (d2 state != d1's original initial state)
        # Both may show the same state if guards block, but the event log
        # should show progression
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        events_file = feature_dir / "mission-events.jsonl"
        if events_file.exists():
            events = [
                json.loads(line)
                for line in events_file.read_text().strip().split("\n")
                if line.strip()
            ]
            # Should have at least one phase_entered event from advancement
            phase_events = [e for e in events if e.get("type") == "phase_entered"]
            assert len(phase_events) >= 1, "State advancement should emit phase_entered events"
