"""Tests for context CLI commands -- mission-resolve and mission-show (T011)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.lane_test_utils import write_single_lane_manifest
from specify_cli.cli.commands.context import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_project(tmp_path: Path, *, mission_slug: str = "057-test-feature", wp_code: str = "WP01") -> Path:
    """Create a minimal spec-kitty project tree for CLI tests."""
    # .kittify/config.yaml
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir(parents=True)
    (kittify_dir / "config.yaml").write_text(
        "project:\n  uuid: test-uuid-1234\nvcs:\n  type: git\n",
        encoding="utf-8",
    )

    # kitty-specs/<slug>/meta.json
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)
    meta = {
        "mission_slug": mission_slug,
        "mission_id": mission_slug,
        "target_branch": "main",
    }
    (feature_dir / "meta.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8"
    )

    # kitty-specs/<slug>/tasks/<WP>.md
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    wp_content = (
        f"---\n"
        f"work_package_id: {wp_code}\n"
        f"title: Test WP\n"
        f"lane: planned\n"
        f"dependencies: []\n"
        f"---\n\n"
        f"# {wp_code} – Test\n"
    )
    (tasks_dir / f"{wp_code}-test-wp.md").write_text(wp_content, encoding="utf-8")
    write_single_lane_manifest(feature_dir, wp_ids=(wp_code,))

    return tmp_path


# ---------------------------------------------------------------------------
# Tests: mission-resolve
# ---------------------------------------------------------------------------


class TestMissionResolveCommand:
    """Tests for `spec-kitty context mission-resolve`."""

    def test_resolve_prints_token(self, tmp_path: Path) -> None:
        """Successful resolve prints a ctx- prefixed token on stdout."""
        repo_root = _make_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["mission-resolve", "--wp", "WP01", "--feature", "057-test-feature"],
            catch_exceptions=False,
            env={"SPECIFY_REPO_ROOT": str(repo_root)},
        )
        assert result.exit_code == 0, result.output
        token = result.output.strip()
        assert token.startswith("ctx-"), f"Expected ctx- prefix, got: {token}"

    def test_resolve_json_output(self, tmp_path: Path) -> None:
        """With --json flag, resolve outputs a valid JSON object."""
        repo_root = _make_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["mission-resolve", "--wp", "WP01", "--feature", "057-test-feature", "--json"],
            catch_exceptions=False,
            env={"SPECIFY_REPO_ROOT": str(repo_root)},
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["wp_code"] == "WP01"
        assert data["mission_slug"] == "057-test-feature"
        assert data["token"].startswith("ctx-")
        assert data["target_branch"] == "main"

    def test_resolve_creates_context_file(self, tmp_path: Path) -> None:
        """Resolve writes a JSON file to .kittify/runtime/contexts/."""
        repo_root = _make_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["mission-resolve", "--wp", "WP01", "--feature", "057-test-feature"],
            catch_exceptions=False,
            env={"SPECIFY_REPO_ROOT": str(repo_root)},
        )
        assert result.exit_code == 0, result.output
        token = result.output.strip()
        ctx_file = repo_root / ".kittify" / "runtime" / "contexts" / f"{token}.json"
        assert ctx_file.exists(), f"Context file not found: {ctx_file}"
        data = json.loads(ctx_file.read_text(encoding="utf-8"))
        assert data["token"] == token

    def test_resolve_missing_wp_fails(self, tmp_path: Path) -> None:
        """Resolve without --wp exits non-zero (typer enforces required option)."""
        repo_root = _make_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["mission-resolve", "--feature", "057-test-feature"],
            env={"SPECIFY_REPO_ROOT": str(repo_root)},
        )
        assert result.exit_code != 0

    def test_resolve_missing_feature_fails(self, tmp_path: Path) -> None:
        """Resolve without --feature exits non-zero (typer enforces required option)."""
        repo_root = _make_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["mission-resolve", "--wp", "WP01"],
            env={"SPECIFY_REPO_ROOT": str(repo_root)},
        )
        assert result.exit_code != 0

    def test_resolve_unknown_feature_fails(self, tmp_path: Path) -> None:
        """Resolve with a feature that doesn't exist exits non-zero."""
        repo_root = _make_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["mission-resolve", "--wp", "WP01", "--feature", "999-does-not-exist"],
            env={"SPECIFY_REPO_ROOT": str(repo_root)},
        )
        assert result.exit_code != 0
        assert "999-does-not-exist" in result.output


# ---------------------------------------------------------------------------
# Tests: mission-show
# ---------------------------------------------------------------------------


class TestMissionShowCommand:
    """Tests for `spec-kitty context mission-show`."""

    def _resolve_token(self, repo_root: Path) -> str:
        """Helper: resolve a context and return the token."""
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["mission-resolve", "--wp", "WP01", "--feature", "057-test-feature"],
            catch_exceptions=False,
            env={"SPECIFY_REPO_ROOT": str(repo_root)},
        )
        assert result.exit_code == 0
        return result.output.strip()

    def test_show_displays_fields(self, tmp_path: Path) -> None:
        """show prints key MissionContext fields in human-readable format."""
        repo_root = _make_project(tmp_path)
        token = self._resolve_token(repo_root)
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["mission-show", "--context", token],
            catch_exceptions=False,
            env={"SPECIFY_REPO_ROOT": str(repo_root)},
        )
        assert result.exit_code == 0, result.output
        assert "WP01" in result.output
        assert "057-test-feature" in result.output

    def test_show_json_output(self, tmp_path: Path) -> None:
        """With --json flag, show outputs valid JSON with all fields."""
        repo_root = _make_project(tmp_path)
        token = self._resolve_token(repo_root)
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["mission-show", "--context", token, "--json"],
            catch_exceptions=False,
            env={"SPECIFY_REPO_ROOT": str(repo_root)},
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["token"] == token
        assert data["wp_code"] == "WP01"
        assert data["mission_slug"] == "057-test-feature"

    def test_show_invalid_token_fails(self, tmp_path: Path) -> None:
        """show with an invalid token exits non-zero with an error."""
        repo_root = _make_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["mission-show", "--context", "ctx-invalid-token-does-not-exist"],
            env={"SPECIFY_REPO_ROOT": str(repo_root)},
        )
        assert result.exit_code != 0
        assert "ctx-invalid-token-does-not-exist" in result.output or "Error" in result.output

    def test_show_missing_context_flag_fails(self, tmp_path: Path) -> None:
        """show without --context exits non-zero (typer enforces required option)."""
        repo_root = _make_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["mission-show"],
            env={"SPECIFY_REPO_ROOT": str(repo_root)},
        )
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Tests: require_explicit_feature helper
# ---------------------------------------------------------------------------


class TestRequireExplicitFeature:
    """Tests for core/paths.py require_explicit_feature."""

    def test_returns_slug_when_provided(self) -> None:
        from specify_cli.core.paths import require_explicit_feature
        assert require_explicit_feature("057-my-feature") == "057-my-feature"

    def test_strips_whitespace(self) -> None:
        from specify_cli.core.paths import require_explicit_feature
        assert require_explicit_feature("  057-my-feature  ") == "057-my-feature"

    def test_raises_when_none(self) -> None:
        from specify_cli.core.paths import require_explicit_feature
        with pytest.raises(ValueError, match="--feature"):
            require_explicit_feature(None)

    def test_raises_when_empty_string(self) -> None:
        from specify_cli.core.paths import require_explicit_feature
        with pytest.raises(ValueError, match="--feature"):
            require_explicit_feature("")

    def test_raises_when_whitespace_only(self) -> None:
        from specify_cli.core.paths import require_explicit_feature
        with pytest.raises(ValueError, match="--feature"):
            require_explicit_feature("   ")

    def test_custom_command_hint(self) -> None:
        from specify_cli.core.paths import require_explicit_feature
        with pytest.raises(ValueError, match="--wp <WP_CODE>"):
            require_explicit_feature(None, command_hint="--wp <WP_CODE>")


# ---------------------------------------------------------------------------
# Tests: get_feature_target_branch helper
# ---------------------------------------------------------------------------


class TestGetFeatureTargetBranch:
    """Tests for core/paths.py get_feature_target_branch."""

    def test_reads_from_meta_json(self, tmp_path: Path) -> None:
        from specify_cli.core.paths import get_feature_target_branch
        feature_dir = tmp_path / "kitty-specs" / "057-test"
        feature_dir.mkdir(parents=True)
        (feature_dir / "meta.json").write_text(
            json.dumps({"target_branch": "2.x"}) + "\n", encoding="utf-8"
        )
        # Need a fake .git directory so resolve_primary_branch can run
        (tmp_path / ".git").mkdir()
        branch = get_feature_target_branch(tmp_path, "057-test")
        assert branch == "2.x"

    def test_falls_back_when_no_meta(self, tmp_path: Path) -> None:
        from specify_cli.core.paths import get_feature_target_branch
        (tmp_path / ".git").mkdir()
        # No kitty-specs directory at all -- should return primary branch fallback
        branch = get_feature_target_branch(tmp_path, "099-nonexistent")
        # Just verify it returns a non-empty string (main or master)
        assert isinstance(branch, str)
        assert len(branch) > 0

    def test_falls_back_on_malformed_meta(self, tmp_path: Path) -> None:
        from specify_cli.core.paths import get_feature_target_branch
        feature_dir = tmp_path / "kitty-specs" / "057-test"
        feature_dir.mkdir(parents=True)
        (feature_dir / "meta.json").write_text("INVALID JSON {{", encoding="utf-8")
        (tmp_path / ".git").mkdir()
        branch = get_feature_target_branch(tmp_path, "057-test")
        assert isinstance(branch, str)
        assert len(branch) > 0
