"""Integration tests for ``spec-kitty next`` CLI command."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from specify_cli import app as cli_app
from specify_cli.next.decision import DecisionKind

import pytest

from tests.lane_test_utils import write_single_lane_manifest

pytestmark = pytest.mark.git_repo

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
    mission_slug: str = "042-test-feature",
    mission_type: str = "software-dev",
) -> Path:
    """Scaffold a minimal spec-kitty project with a feature."""
    repo_root = tmp_path / "project"
    repo_root.mkdir()
    _init_git_repo(repo_root)

    # .kittify dir (minimal)
    kittify = repo_root / ".kittify"
    kittify.mkdir()

    # Feature directory
    feature_dir = repo_root / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"mission_type": mission_type}),
        encoding="utf-8",
    )

    return repo_root


def _write_runtime_input_mission(repo_root: Path, mission_type: str) -> None:
    """Create a runtime-only mission that deterministically requests input."""
    mission_dir = repo_root / ".kittify" / "overrides" / "missions" / mission_type
    mission_dir.mkdir(parents=True, exist_ok=True)
    (mission_dir / "mission-runtime.yaml").write_text(
        (
            "mission:\n"
            f"  key: {mission_type}\n"
            f"  name: {mission_type}\n"
            "  version: '1.0.0'\n"
            "steps:\n"
            "  - id: collect_input\n"
            "    title: Collect Input\n"
            "    description: Gather required answer\n"
            "    requires_inputs: [approval]\n"
            "  - id: execute\n"
            "    title: Execute\n"
            "    depends_on: [collect_input]\n"
            "    description: Proceed with mission\n"
        ),
        encoding="utf-8",
    )


def _write_invalid_runtime_mission(repo_root: Path, mission_type: str) -> None:
    """Create a mission whose first step is unschedulable on a fresh run."""
    mission_dir = repo_root / ".kittify" / "overrides" / "missions" / mission_type
    mission_dir.mkdir(parents=True, exist_ok=True)
    (mission_dir / "mission-runtime.yaml").write_text(
        (
            "mission:\n"
            f"  key: {mission_type}\n"
            f"  name: {mission_type}\n"
            "  version: '1.0.0'\n"
            "steps:\n"
            "  - id: impossible\n"
            "    title: Impossible\n"
            "    description: Never issuable first step\n"
            "    depends_on: [missing-prereq]\n"
        ),
        encoding="utf-8",
    )


def _seed_wp_lane(feature_dir: Path, wp_id: str, lane: str) -> None:
    """Seed a WP into a specific lane in the event log."""
    from specify_cli.status.store import append_event
    from specify_cli.status.models import StatusEvent, Lane

    # Map legacy aliases to canonical lane names
    _lane_alias = {"doing": "in_progress"}
    canonical_lane = _lane_alias.get(lane, lane)

    event = StatusEvent(
        event_id=f"test-{wp_id}-{canonical_lane}",
        mission_slug=feature_dir.name,
        wp_id=wp_id,
        from_lane=Lane.PLANNED,
        to_lane=Lane(canonical_lane),
        at="2026-01-01T00:00:00+00:00",
        actor="test",
        force=True,
        execution_mode="worktree",
    )
    append_event(feature_dir, event)


def _add_wp_files(feature_dir: Path, wps: dict[str, str]) -> None:
    """Create WP task files.  wps maps WP ID to lane."""
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)
    for wp_id, lane in wps.items():
        (tasks_dir / f"{wp_id}.md").write_text(
            f"---\nwork_package_id: {wp_id}\nlane: {lane}\ntitle: {wp_id} task\n---\n# {wp_id}\nDo something.\n",
            encoding="utf-8",
        )
        # Seed event log for non-planned lanes
        if lane != "planned":
            _seed_wp_lane(feature_dir, wp_id, lane)
    write_single_lane_manifest(feature_dir, wp_ids=tuple(wps.keys()))


def _advance_runtime_to_step(
    repo_root: Path,
    mission_slug: str,
    target_step_id: str,
    agent: str = "test-agent",
) -> None:
    """Advance the runtime run past steps until target_step_id is issued."""
    from specify_cli.next.runtime_bridge import get_or_start_run
    from specify_cli.mission import get_mission_type
    from spec_kitty_runtime import next_step as runtime_next_step, NullEmitter
    from spec_kitty_runtime.engine import _read_snapshot

    feature_dir = repo_root / "kitty-specs" / mission_slug
    mission_type = get_mission_type(feature_dir)
    run_ref = get_or_start_run(mission_slug, repo_root, mission_type)

    step_order = [
        "discovery",
        "specify",
        "plan",
        "tasks_outline",
        "tasks_packages",
        "tasks_finalize",
        "implement",
        "review",
        "accept",
    ]
    target_idx = step_order.index(target_step_id) if target_step_id in step_order else -1

    for _ in range(target_idx + 2):
        snapshot = _read_snapshot(Path(run_ref.run_dir))
        if snapshot.issued_step_id == target_step_id:
            return
        runtime_next_step(run_ref, agent_id=agent, result="success", emitter=NullEmitter())
        snapshot = _read_snapshot(Path(run_ref.run_dir))
        if snapshot.issued_step_id == target_step_id:
            return


def _complete_all_steps(
    repo_root: Path,
    mission_slug: str,
    agent: str = "test-agent",
) -> None:
    """Complete all runtime steps to reach terminal state."""
    from specify_cli.next.runtime_bridge import get_or_start_run
    from specify_cli.mission import get_mission_type
    from spec_kitty_runtime import next_step as runtime_next_step, NullEmitter

    feature_dir = repo_root / "kitty-specs" / mission_slug
    mission_type = get_mission_type(feature_dir)
    run_ref = get_or_start_run(mission_slug, repo_root, mission_type)

    for _ in range(20):
        decision = runtime_next_step(run_ref, agent_id=agent, result="success", emitter=NullEmitter())
        if decision.kind == "terminal":
            return


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
        assert d["mission_slug"] == "042-test-feature"
        assert d["mission"] == "software-dev"
        assert "kind" in d

    def test_terminal_state_returns_terminal(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        # Complete all steps via runtime to reach terminal
        _complete_all_steps(repo_root, "042-test-feature")

        from specify_cli.next.decision import decide_next

        decision = decide_next("test-agent", "042-test-feature", "success", repo_root)
        assert decision.kind == DecisionKind.terminal

    def test_failed_result_flows_through_runtime_as_blocked(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)

        from specify_cli.next.decision import decide_next

        # Issue first step so runtime has an issued step to complete as failed.
        first = decide_next("test-agent", "042-test-feature", "success", repo_root)
        assert first.step_id is not None

        decision = decide_next("test-agent", "042-test-feature", "failed", repo_root)
        assert decision.kind == DecisionKind.blocked
        assert "failed" in (decision.reason or "").lower()
        assert decision.run_id is not None

    def test_blocked_result_returns_blocked(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)

        from specify_cli.next.decision import decide_next

        first = decide_next("test-agent", "042-test-feature", "success", repo_root)
        assert first.step_id is not None

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
        _add_wp_files(
            feature_dir,
            {
                "WP01": "done",
                "WP02": "planned",
                "WP03": "planned",
            },
        )
        # Advance runtime to implement step
        _advance_runtime_to_step(repo_root, "042-test-feature", "implement")

        from specify_cli.next.decision import decide_next

        decision = decide_next("test-agent", "042-test-feature", "success", repo_root)
        assert decision.kind == DecisionKind.step
        assert decision.action == "implement"
        assert decision.wp_id == "WP02"
        assert decision.workspace_path is not None

    def test_implement_state_no_planned_checks_for_review(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        _add_wp_files(
            feature_dir,
            {
                "WP01": "done",
                "WP02": "for_review",
            },
        )
        # Advance runtime to implement step
        _advance_runtime_to_step(repo_root, "042-test-feature", "implement")

        from specify_cli.next.decision import decide_next

        decision = decide_next("test-agent", "042-test-feature", "success", repo_root)
        assert decision.kind == DecisionKind.step
        assert decision.action == "review"
        assert decision.wp_id == "WP02"

    def test_all_wps_done_advances_to_review(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        _add_wp_files(
            feature_dir,
            {
                "WP01": "done",
                "WP02": "done",
            },
        )
        # Advance runtime to implement step
        _advance_runtime_to_step(repo_root, "042-test-feature", "implement")

        from specify_cli.next.decision import decide_next

        decision = decide_next("test-agent", "042-test-feature", "success", repo_root)
        # All WPs done => should advance past implement
        assert decision.kind in (DecisionKind.step, DecisionKind.blocked)


class TestNextCommandProgress:
    """Test that progress information is included."""

    def test_progress_in_decision(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"
        _add_wp_files(
            feature_dir,
            {
                "WP01": "done",
                "WP02": "doing",
                "WP03": "planned",
            },
        )

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


class TestNextCommandRuntimeFields:
    """Test that runtime fields are included in decisions."""

    def test_run_id_in_decision(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)

        from specify_cli.next.decision import decide_next

        decision = decide_next("test-agent", "042-test-feature", "success", repo_root)
        assert decision.run_id is not None
        assert len(decision.run_id) > 0

    def test_step_id_in_decision(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)

        from specify_cli.next.decision import decide_next

        decision = decide_next("test-agent", "042-test-feature", "success", repo_root)
        assert decision.step_id is not None

    def test_json_output_has_runtime_fields(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)

        from specify_cli.next.decision import decide_next

        decision = decide_next("test-agent", "042-test-feature", "success", repo_root)
        d = decision.to_dict()
        assert "run_id" in d
        assert "step_id" in d
        assert "decision_id" in d
        assert "input_key" in d


class TestNextCommandKnownBlockedMissions:
    """Strict reminders for accepted-but-unimplemented mission mappings."""

    @pytest.mark.xfail(
        strict=True,
        reason=("Tracked in docs/development/tracking/next-mission-mappings/issue-plan-mission-next-mapping.md"),
    )
    def test_plan_mission_should_return_runnable_step_when_mapped(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(
            tmp_path,
            mission_slug="043-plan-feature",
            mission_type="plan",
        )

        from specify_cli.next.decision import decide_next

        decision = decide_next("test-agent", "043-plan-feature", "success", repo_root)
        assert decision.kind == DecisionKind.step
        assert decision.action is not None

    @pytest.mark.xfail(
        strict=True,
        reason=("Tracked in docs/development/tracking/next-mission-mappings/issue-documentation-mission-next-mapping.md"),
    )
    def test_documentation_mission_should_return_runnable_step_when_mapped(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(
            tmp_path,
            mission_slug="044-docs-feature",
            mission_type="documentation",
        )

        from specify_cli.next.decision import decide_next

        decision = decide_next("test-agent", "044-docs-feature", "success", repo_root)
        assert decision.kind == DecisionKind.step
        assert decision.action is not None

    def test_missing_canonical_status_during_wp_iteration_returns_structured_decision(self, tmp_path: Path) -> None:
        repo_root = _scaffold_project(tmp_path)

        from specify_cli.next.runtime_bridge import decide_next_via_runtime
        from specify_cli.status.lane_reader import CanonicalStatusNotFoundError

        class RunRef:
            run_id = "run-123"
            run_dir = str(tmp_path / "run")

        class Snapshot:
            issued_step_id = "implement"

        with (
            patch("specify_cli.next.runtime_bridge.get_or_start_run", return_value=RunRef()),
            patch("specify_cli.next.runtime_bridge._compute_wp_progress", return_value=None),
            patch("spec_kitty_runtime.engine._read_snapshot", return_value=Snapshot()),
            patch(
                "specify_cli.next.runtime_bridge._should_advance_wp_step",
                side_effect=CanonicalStatusNotFoundError(
                    "Canonical status not found for feature '042-test-feature'. Run 'spec-kitty agent mission finalize-tasks --mission 042-test-feature' to bootstrap the event log."
                ),
            ),
        ):
            decision = decide_next_via_runtime("test-agent", "042-test-feature", "success", repo_root)

        assert decision.kind in {DecisionKind.step, DecisionKind.blocked}
        assert any("finalize-tasks" in failure for failure in decision.guard_failures)


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
            ["next", "--feature", "042-test-feature", "--json"],
        )
        assert result.exit_code == 0, f"stderr: {result.output}"
        data = json.loads(result.output)
        assert data["agent"] is None
        assert data["mission_slug"] == "042-test-feature"
        assert data["mission"] == "software-dev"
        assert "kind" in data
        assert "mission_state" in data
        assert "timestamp" in data
        assert "guard_failures" in data
        assert data["mission_state"] == "not_started"
        assert data["preview_step"] is not None
        assert "run_id" in data
        assert data["step_id"] is None

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

        # First issue a step so runtime can complete it as blocked.
        first = runner.invoke(
            cli_app,
            ["next", "--agent", "test", "--feature", "042-test-feature", "--result", "success", "--json"],
        )
        assert first.exit_code == 0

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
        # Complete all steps via runtime
        _complete_all_steps(repo_root, "042-test-feature")
        monkeypatch.chdir(repo_root)

        result = runner.invoke(
            cli_app,
            ["next", "--agent", "test", "--feature", "042-test-feature", "--result", "success", "--json"],
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
            ["next", "--feature", "042-test-feature"],
        )
        assert result.exit_code == 0
        assert "software-dev @ not_started" in result.output
        assert "Next step:" in result.output

    def test_nonexistent_feature_blocked(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-existent feature returns blocked with exit code 1."""
        repo_root = _scaffold_project(tmp_path)
        monkeypatch.chdir(repo_root)

        result = runner.invoke(
            cli_app,
            ["next", "--agent", "test", "--feature", "999-nonexistent", "--result", "success", "--json"],
        )
        # Feature detection may fail before decide_next, or decide_next returns blocked
        assert result.exit_code != 0 or "blocked" in result.output or "not found" in result.output.lower()

    def test_query_mode_does_not_advance_state(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Bare query calls are read-only and keep the run snapshot unchanged."""
        repo_root = _scaffold_project(tmp_path)
        monkeypatch.chdir(repo_root)

        from specify_cli.mission import get_mission_type
        from specify_cli.next.runtime_bridge import get_or_start_run
        from spec_kitty_runtime.engine import _read_snapshot

        mission_type = get_mission_type(repo_root / "kitty-specs" / "042-test-feature")
        run_ref = get_or_start_run("042-test-feature", repo_root, mission_type)
        before = _read_snapshot(Path(run_ref.run_dir))

        r1 = runner.invoke(
            cli_app,
            ["next", "--feature", "042-test-feature", "--json"],
        )
        assert r1.exit_code == 0
        d1 = json.loads(r1.output)

        r2 = runner.invoke(
            cli_app,
            ["next", "--agent", "compat-agent", "--feature", "042-test-feature", "--json"],
        )
        assert r2.exit_code == 0
        d2 = json.loads(r2.output)

        after = _read_snapshot(Path(run_ref.run_dir))

        assert d1["mission_state"] == "not_started"
        assert d1["preview_step"] == d2["preview_step"]
        assert d2["agent"] == "compat-agent"
        assert before.model_dump(mode="json") == after.model_dump(mode="json")

    def test_query_mode_does_not_create_runtime_index_on_first_use(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        repo_root = _scaffold_project(tmp_path)
        monkeypatch.chdir(repo_root)

        runtime_index = repo_root / ".kittify" / "runtime" / "feature-runs.json"
        assert not runtime_index.exists()

        result = runner.invoke(
            cli_app,
            ["next", "--feature", "042-test-feature", "--json"],
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["mission_state"] == "not_started"
        assert data["preview_step"] is not None
        assert not runtime_index.exists()

    def test_json_output_includes_runtime_fields(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """JSON output includes new runtime fields."""
        repo_root = _scaffold_project(tmp_path)
        monkeypatch.chdir(repo_root)

        result = runner.invoke(
            cli_app,
            ["next", "--feature", "042-test-feature", "--json"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "run_id" in data
        assert data["run_id"] is not None
        assert "step_id" in data
        assert "preview_step" in data

    def test_query_mode_invalid_first_step_fails_clearly(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        repo_root = _scaffold_project(tmp_path, mission_type="invalid-query-mission")
        _write_invalid_runtime_mission(repo_root, mission_type="invalid-query-mission")
        monkeypatch.chdir(repo_root)

        result = runner.invoke(
            cli_app,
            ["next", "--feature", "042-test-feature", "--json"],
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert "has no issuable first step" in data["error"]

    def test_advancing_mode_still_requires_agent_and_result(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        repo_root = _scaffold_project(tmp_path)
        monkeypatch.chdir(repo_root)

        result = runner.invoke(
            cli_app,
            ["next", "--feature", "042-test-feature", "--result", "success", "--json"],
        )

        assert result.exit_code == 1
        assert "--agent is required when --result is provided" in result.output

    def test_advancing_mode_with_result_still_advances_normally(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        repo_root = _scaffold_project(tmp_path)
        monkeypatch.chdir(repo_root)

        result = runner.invoke(
            cli_app,
            ["next", "--agent", "test", "--feature", "042-test-feature", "--result", "success", "--json"],
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["step_id"] is not None
        assert data["preview_step"] is None


# ---------------------------------------------------------------------------
# --answer --json single-document output tests
# ---------------------------------------------------------------------------


class TestNextCommandAnswerJSON:
    def test_answer_json_single_document(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Successful answer flow emits one JSON document with merged answer fields."""
        repo_root = _scaffold_project(tmp_path, mission_type="input-mission")
        _write_runtime_input_mission(repo_root, mission_type="input-mission")
        monkeypatch.chdir(repo_root)

        # First call creates a real pending decision.
        first = runner.invoke(
            cli_app,
            ["next", "--agent", "test", "--feature", "042-test-feature", "--result", "success", "--json"],
        )
        assert first.exit_code == 0, first.output
        first_data = json.loads(first.output)
        assert first_data["kind"] == "decision_required"
        assert first_data["decision_id"] == "input:approval"

        # Answer without --decision-id: command must auto-resolve the single pending decision.
        r = runner.invoke(
            cli_app,
            [
                "next",
                "--agent",
                "test",
                "--feature",
                "042-test-feature",
                "--result",
                "success",
                "--answer",
                "yes",
                "--json",
            ],
        )
        assert r.exit_code == 0, r.output
        data = json.loads(r.output.strip())
        assert isinstance(data, dict)
        assert data["answered"] == "input:approval"
        assert data["answer"] == "yes"
        assert data["kind"] in {"step", "terminal", "blocked", "decision_required"}

    def test_answer_json_never_emits_two_objects(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Regression: stdout must be exactly one JSON document, no trailing object."""
        repo_root = _scaffold_project(tmp_path, mission_type="input-mission")
        _write_runtime_input_mission(repo_root, mission_type="input-mission")
        monkeypatch.chdir(repo_root)

        # First, advance once so a pending decision exists to answer.
        first = runner.invoke(
            cli_app,
            [
                "next",
                "--agent",
                "test",
                "--feature",
                "042-test-feature",
                "--result",
                "success",
                "--json",
            ],
        )
        assert first.exit_code == 0, first.output

        r = runner.invoke(
            cli_app,
            [
                "next",
                "--agent",
                "test",
                "--feature",
                "042-test-feature",
                "--answer",
                "yes",
                "--json",
            ],
        )
        assert r.exit_code == 0, r.output

        # Ensure a single top-level JSON value with no trailing payload.
        decoder = json.JSONDecoder()
        text = r.output.strip()
        obj, idx = decoder.raw_decode(text)
        assert isinstance(obj, dict)
        assert text[idx:].strip() == "", f"Unexpected trailing output: {text[idx:]!r}"


# ---------------------------------------------------------------------------
# Decision-required metadata tests
# ---------------------------------------------------------------------------


class TestNextCommandDecisionRequired:
    def test_decision_required_has_question_field_in_json(self, tmp_path: Path) -> None:
        """JSON output includes question/options for real runtime decision_required."""
        repo_root = _scaffold_project(tmp_path, mission_type="input-mission")
        _write_runtime_input_mission(repo_root, mission_type="input-mission")

        from specify_cli.next.decision import decide_next

        decision = decide_next("test-agent", "042-test-feature", "success", repo_root)
        d = decision.to_dict()
        assert d["kind"] == "decision_required"
        assert "question" in d
        assert "options" in d
        assert d["question"] is not None

    def test_decision_required_has_decision_id_field(self, tmp_path: Path) -> None:
        """Decision-required responses include canonical decision_id/input_key fields."""
        repo_root = _scaffold_project(tmp_path, mission_type="input-mission")
        _write_runtime_input_mission(repo_root, mission_type="input-mission")

        from specify_cli.next.decision import decide_next

        decision = decide_next("test-agent", "042-test-feature", "success", repo_root)
        d = decision.to_dict()
        assert d["decision_id"] == "input:approval"
        assert d["input_key"] == "approval"


# ---------------------------------------------------------------------------
# Atomic task transition tests
# ---------------------------------------------------------------------------


class TestAtomicTaskTransitions:
    def test_plan_to_tasks_outline_to_packages_to_finalize(self, tmp_path: Path) -> None:
        """Advance through all 3 atomic task steps in the correct order."""
        repo_root = _scaffold_project(tmp_path)
        feature_dir = repo_root / "kitty-specs" / "042-test-feature"

        # Create artifacts for earlier steps
        (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
        (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
        (feature_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")

        # Create WP files with dependencies for tasks_finalize guard
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)
        (tasks_dir / "WP01.md").write_text(
            "---\nwork_package_id: WP01\nlane: done\ndependencies: []\ntitle: WP01\n---\n# WP01\n",
            encoding="utf-8",
        )
        # Seed event log so runtime bridge reads WP01 as done
        _seed_wp_lane(feature_dir, "WP01", "done")

        from specify_cli.next.decision import decide_next

        seen_steps = []
        for _i in range(40):
            decision = decide_next("test-agent", "042-test-feature", "success", repo_root)
            if decision.kind == "terminal":
                break
            if decision.step_id and decision.step_id not in seen_steps:
                seen_steps.append(decision.step_id)

        # All 3 atomic task steps must be visited
        assert "tasks_outline" in seen_steps, f"tasks_outline not visited; saw: {seen_steps}"
        assert "tasks_packages" in seen_steps, f"tasks_packages not visited; saw: {seen_steps}"
        assert "tasks_finalize" in seen_steps, f"tasks_finalize not visited; saw: {seen_steps}"

        # Verify correct ordering: outline before packages before finalize
        outline_idx = seen_steps.index("tasks_outline")
        packages_idx = seen_steps.index("tasks_packages")
        finalize_idx = seen_steps.index("tasks_finalize")
        assert outline_idx < packages_idx < finalize_idx, f"Steps out of order: outline@{outline_idx}, packages@{packages_idx}, finalize@{finalize_idx}"
