"""Integration tests for orchestrator-api commands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from specify_cli.frontmatter import read_frontmatter
from specify_cli.orchestrator_api.commands import app
from specify_cli.orchestrator_api.envelope import CONTRACT_VERSION, MIN_PROVIDER_VERSION

runner = CliRunner()


def _valid_policy_json() -> str:
    return json.dumps(
        {
            "orchestrator_id": "spec-kitty-orchestrator",
            "orchestrator_version": "0.1.0",
            "agent_family": "claude",
            "approval_mode": "supervised",
            "sandbox_mode": "sandbox",
            "network_mode": "restricted",
            "dangerous_flags": [],
        }
    )


def _deps_yaml(dependencies: list[str]) -> str:
    if not dependencies:
        return "dependencies: []"
    lines = ["dependencies:"]
    lines.extend(f"  - {dep}" for dep in dependencies)
    return "\n".join(lines)


def _write_wp(
    tasks_dir: Path,
    wp_id: str,
    lane: str = "planned",
    dependencies: list[str] | None = None,
    filename: str | None = None,
    agent: str | None = None,
) -> Path:
    deps = dependencies or []
    wp_file = tasks_dir / (filename or f"{wp_id}.md")
    agent_line = f"agent: {agent}\n" if agent else ""
    wp_file.write_text(
        "---\n"
        f"work_package_id: {wp_id}\n"
        f"title: {wp_id} test\n"
        f"lane: {lane}\n"
        f"{agent_line}"
        f"{_deps_yaml(deps)}\n"
        "---\n\n"
        f"# {wp_id}\n\n"
        "## Activity Log\n\n",
        encoding="utf-8",
    )
    return wp_file


def _make_feature(tmp_path: Path, feature_slug: str = "099-test-feature") -> tuple[Path, Path]:
    repo_root = tmp_path / "repo"
    feature_dir = repo_root / "kitty-specs" / feature_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    _write_wp(tasks_dir, "WP01")
    _write_wp(tasks_dir, "WP02")

    (feature_dir / "meta.json").write_text(json.dumps({"status_phase": 1}), encoding="utf-8")
    return repo_root, feature_dir


def _lane_of(path: Path) -> str:
    frontmatter, _ = read_frontmatter(path)
    return str(frontmatter.get("lane", "planned"))


class TestContractVersion:
    def test_contract_version_envelope(self) -> None:
        result = runner.invoke(app, ["contract-version"])
        assert result.exit_code == 0, result.output

        payload = json.loads(result.output)
        assert payload["success"] is True
        assert payload["data"]["api_version"] == CONTRACT_VERSION
        assert payload["command"] == "orchestrator-api.contract-version"

    def test_contract_version_mismatch(self) -> None:
        result = runner.invoke(app, ["contract-version", "--provider-version", "0.0.1"])
        assert result.exit_code == 1

        payload = json.loads(result.output)
        assert payload["error_code"] == "CONTRACT_VERSION_MISMATCH"

    def test_contract_version_accepts_min_provider(self) -> None:
        result = runner.invoke(
            app,
            ["contract-version", "--provider-version", MIN_PROVIDER_VERSION],
        )
        assert result.exit_code == 0, result.output


class TestFeatureState:
    def test_reports_in_progress_mapping_and_last_actor(self, tmp_path: Path) -> None:
        repo_root, feature_dir = _make_feature(tmp_path)
        wp01 = feature_dir / "tasks" / "WP01.md"
        _write_wp(feature_dir / "tasks", "WP01", lane="doing", agent="claude")

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(app, ["feature-state", "--feature", "099-test-feature"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        wps = {wp["wp_id"]: wp for wp in payload["data"]["work_packages"]}
        assert wps["WP01"]["lane"] == "in_progress"
        assert wps["WP01"]["last_actor"] == "claude"
        assert _lane_of(wp01) == "doing"

    def test_reports_feature_not_found(self, tmp_path: Path) -> None:
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(app, ["feature-state", "--feature", "missing-feature"])

        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["error_code"] == "FEATURE_NOT_FOUND"


class TestListReady:
    def test_only_planned_with_done_dependencies_are_ready(self, tmp_path: Path) -> None:
        repo_root = tmp_path / "repo"
        feature_dir = repo_root / "kitty-specs" / "099-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        _write_wp(tasks_dir, "WP01", lane="done")
        _write_wp(tasks_dir, "WP02", lane="planned", dependencies=["WP01"])
        _write_wp(tasks_dir, "WP03", lane="planned", dependencies=["WP02"])

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(app, ["list-ready", "--feature", "099-test-feature"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        ready = {item["wp_id"] for item in payload["data"]["ready_work_packages"]}
        assert "WP02" in ready
        assert "WP03" not in ready


class TestStartImplementation:
    def test_requires_policy(self, tmp_path: Path) -> None:
        repo_root, _ = _make_feature(tmp_path)
        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "start-implementation",
                    "--feature",
                    "099-test-feature",
                    "--wp",
                    "WP01",
                    "--actor",
                    "claude",
                ],
            )

        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["error_code"] == "POLICY_METADATA_REQUIRED"

    def test_transitions_planned_to_in_progress(self, tmp_path: Path) -> None:
        repo_root, feature_dir = _make_feature(tmp_path)
        wp_path = feature_dir / "tasks" / "WP01.md"

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "start-implementation",
                    "--feature",
                    "099-test-feature",
                    "--wp",
                    "WP01",
                    "--actor",
                    "claude",
                    "--policy",
                    _valid_policy_json(),
                ],
            )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["data"]["from_lane"] == "planned"
        assert payload["data"]["to_lane"] == "in_progress"
        assert payload["data"]["workspace_path"].endswith(".worktrees/099-test-feature-WP01")
        assert payload["data"]["prompt_path"].endswith("WP01.md")
        assert _lane_of(wp_path) == "doing"

    def test_rejects_when_in_progress_claimed_by_other_actor(self, tmp_path: Path) -> None:
        repo_root = tmp_path / "repo"
        feature_dir = repo_root / "kitty-specs" / "099-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", lane="doing", agent="other-agent")

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "start-implementation",
                    "--feature",
                    "099-test-feature",
                    "--wp",
                    "WP01",
                    "--actor",
                    "claude",
                    "--policy",
                    _valid_policy_json(),
                ],
            )

        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["error_code"] == "WP_ALREADY_CLAIMED"


class TestStartReviewAndTransition:
    def test_start_review_requires_review_ref(self, tmp_path: Path) -> None:
        repo_root = tmp_path / "repo"
        feature_dir = repo_root / "kitty-specs" / "099-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", lane="for_review", agent="claude")

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "start-review",
                    "--feature",
                    "099-test-feature",
                    "--wp",
                    "WP01",
                    "--actor",
                    "reviewer",
                    "--policy",
                    _valid_policy_json(),
                ],
            )

        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["error_code"] == "TRANSITION_REJECTED"

    def test_start_review_moves_for_review_to_in_progress(self, tmp_path: Path) -> None:
        repo_root = tmp_path / "repo"
        feature_dir = repo_root / "kitty-specs" / "099-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        wp_path = _write_wp(tasks_dir, "WP01", lane="for_review", agent="claude")

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "start-review",
                    "--feature",
                    "099-test-feature",
                    "--wp",
                    "WP01",
                    "--actor",
                    "reviewer",
                    "--policy",
                    _valid_policy_json(),
                    "--review-ref",
                    "feedback-001",
                ],
            )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["data"]["to_lane"] == "in_progress"
        assert _lane_of(wp_path) == "doing"

    def test_transition_rejects_invalid_planned_to_done(self, tmp_path: Path) -> None:
        repo_root, _ = _make_feature(tmp_path)

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "transition",
                    "--feature",
                    "099-test-feature",
                    "--wp",
                    "WP01",
                    "--to",
                    "done",
                    "--actor",
                    "reviewer",
                ],
            )

        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["error_code"] == "TRANSITION_REJECTED"

    def test_transition_requires_policy_for_in_progress(self, tmp_path: Path) -> None:
        repo_root, _ = _make_feature(tmp_path)

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "transition",
                    "--feature",
                    "099-test-feature",
                    "--wp",
                    "WP01",
                    "--to",
                    "in_progress",
                    "--actor",
                    "claude",
                ],
            )

        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["error_code"] == "POLICY_METADATA_REQUIRED"

    def test_transition_rejects_for_review_to_planned_without_review_ref(
        self, tmp_path: Path
    ) -> None:
        """for_review -> planned (reject) must require --review-ref."""
        repo_root = tmp_path / "repo"
        feature_dir = repo_root / "kitty-specs" / "099-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", lane="for_review", agent="claude")
        (feature_dir / "meta.json").write_text(
            json.dumps({"status_phase": 1}), encoding="utf-8"
        )

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "transition",
                    "--feature",
                    "099-test-feature",
                    "--wp",
                    "WP01",
                    "--to",
                    "planned",
                    "--actor",
                    "reviewer",
                ],
            )

        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["error_code"] == "TRANSITION_REJECTED"
        assert "review-ref" in payload["data"]["message"]

    def test_transition_for_review_to_planned_with_review_ref_succeeds(
        self, tmp_path: Path
    ) -> None:
        """for_review -> planned with --review-ref is the valid review-reject path."""
        repo_root = tmp_path / "repo"
        feature_dir = repo_root / "kitty-specs" / "099-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        wp_path = _write_wp(tasks_dir, "WP01", lane="for_review", agent="claude")
        (feature_dir / "meta.json").write_text(
            json.dumps({"status_phase": 1}), encoding="utf-8"
        )

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "transition",
                    "--feature",
                    "099-test-feature",
                    "--wp",
                    "WP01",
                    "--to",
                    "planned",
                    "--actor",
                    "reviewer",
                    "--review-ref",
                    "feedback-reject-001",
                ],
            )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["data"]["from_lane"] == "for_review"
        assert payload["data"]["to_lane"] == "planned"
        assert _lane_of(wp_path) == "planned"


class TestAppendAcceptMerge:
    def test_append_history_returns_history_id(self, tmp_path: Path) -> None:
        repo_root, feature_dir = _make_feature(tmp_path)
        wp_path = feature_dir / "tasks" / "WP01.md"

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "append-history",
                    "--feature",
                    "099-test-feature",
                    "--wp",
                    "WP01",
                    "--actor",
                    "claude",
                    "--note",
                    "Started work",
                ],
            )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["data"]["history_entry_id"].startswith("hist-")
        assert "Started work" in wp_path.read_text(encoding="utf-8")

    def test_accept_feature_requires_all_done(self, tmp_path: Path) -> None:
        repo_root, _ = _make_feature(tmp_path)

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                ["accept-feature", "--feature", "099-test-feature", "--actor", "claude"],
            )

        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["error_code"] == "FEATURE_NOT_READY"

    def test_accept_feature_succeeds_when_done(self, tmp_path: Path) -> None:
        repo_root = tmp_path / "repo"
        feature_dir = repo_root / "kitty-specs" / "099-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", lane="done")
        _write_wp(tasks_dir, "WP02", lane="done")
        (feature_dir / "meta.json").write_text("{}", encoding="utf-8")

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                ["accept-feature", "--feature", "099-test-feature", "--actor", "claude"],
            )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["data"]["accepted"] is True
        meta = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
        assert meta["accepted_by"] == "claude"

    def test_merge_feature_preflight_failure(self, tmp_path: Path) -> None:
        repo_root, _ = _make_feature(tmp_path)
        preflight = MagicMock()
        preflight.passed = False
        preflight.errors = ["preflight failed"]

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ), patch(
            "specify_cli.orchestrator_api.commands.run_preflight",
            return_value=preflight,
        ):
            result = runner.invoke(
                app,
                ["merge-feature", "--feature", "099-test-feature"],
            )

        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["error_code"] == "PREFLIGHT_FAILED"

    def test_merge_feature_rejects_unsupported_strategy(self, tmp_path: Path) -> None:
        repo_root, _ = _make_feature(tmp_path)

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                ["merge-feature", "--feature", "099-test-feature", "--strategy", "rebase"],
            )

        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["error_code"] == "UNSUPPORTED_STRATEGY"


class TestSuffixedWpFilenames:
    def test_start_implementation_finds_suffixed_wp_filename(self, tmp_path: Path) -> None:
        repo_root = tmp_path / "repo"
        feature_dir = repo_root / "kitty-specs" / "040-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        _write_wp(tasks_dir, "WP07", filename="WP07-adapter-implementations.md")

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "start-implementation",
                    "--feature",
                    "040-test-feature",
                    "--wp",
                    "WP07",
                    "--actor",
                    "claude",
                    "--policy",
                    _valid_policy_json(),
                ],
            )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["data"]["wp_id"] == "WP07"
        assert "WP07-adapter-implementations.md" in payload["data"]["prompt_path"]

    def test_feature_state_uses_canonical_wp_id_for_suffixed_file(self, tmp_path: Path) -> None:
        repo_root = tmp_path / "repo"
        feature_dir = repo_root / "kitty-specs" / "040-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        _write_wp(tasks_dir, "WP07", filename="WP07-adapter-implementations.md")

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(app, ["feature-state", "--feature", "040-test-feature"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        wp_ids = {item["wp_id"] for item in payload["data"]["work_packages"]}
        assert "WP07" in wp_ids
        assert "WP07-adapter-implementations" not in wp_ids
