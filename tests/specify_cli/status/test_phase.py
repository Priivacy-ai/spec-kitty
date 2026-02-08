"""Tests for specify_cli.status.phase - phase configuration with 3-tier precedence."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.status.phase import (
    DEFAULT_PHASE,
    DEFAULT_PHASE_SOURCE,
    MAX_PHASE_01X,
    VALID_PHASES,
    _read_config_phase,
    _read_meta_phase,
    is_01x_branch,
    resolve_phase,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_meta_json(repo_root: Path, feature_slug: str, data: dict) -> Path:
    """Write a meta.json for the given feature slug."""
    feature_dir = repo_root / "kitty-specs" / feature_slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    meta_path = feature_dir / "meta.json"
    meta_path.write_text(json.dumps(data), encoding="utf-8")
    return meta_path


def _write_config_yaml(repo_root: Path, content: str) -> Path:
    """Write .kittify/config.yaml with the given YAML content."""
    config_dir = repo_root / ".kittify"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.yaml"
    config_path.write_text(content, encoding="utf-8")
    return config_path


def _mock_branch(branch_name: str) -> MagicMock:
    """Return a mock subprocess.run result simulating a git branch name."""
    result = MagicMock()
    result.returncode = 0
    result.stdout = f"{branch_name}\n"
    return result


# ---------------------------------------------------------------------------
# resolve_phase tests
# ---------------------------------------------------------------------------


@patch("specify_cli.status.phase.is_01x_branch", return_value=False)
class TestResolvePhase:
    """Tests for resolve_phase with is_01x_branch mocked to False (2.x branch)."""

    def test_default_phase_when_no_config(self, _mock_branch, tmp_path: Path):
        """No meta.json, no config.yaml -> returns built-in default (Phase 1)."""
        phase, source = resolve_phase(tmp_path, "some-feature")
        assert phase == DEFAULT_PHASE
        assert phase == 1
        assert source == DEFAULT_PHASE_SOURCE

    def test_config_yaml_overrides_default(self, _mock_branch, tmp_path: Path):
        """config.yaml has phase 0 -> overrides built-in default."""
        _write_config_yaml(tmp_path, "status:\n  phase: 0\n")
        phase, source = resolve_phase(tmp_path, "some-feature")
        assert phase == 0
        assert "config.yaml" in source

    def test_meta_json_overrides_config_yaml(self, _mock_branch, tmp_path: Path):
        """meta.json phase 2 overrides config.yaml phase 1."""
        _write_config_yaml(tmp_path, "status:\n  phase: 1\n")
        _write_meta_json(tmp_path, "my-feature", {"status_phase": 2})
        phase, source = resolve_phase(tmp_path, "my-feature")
        assert phase == 2
        assert "meta.json" in source
        assert "my-feature" in source

    def test_meta_json_overrides_default(self, _mock_branch, tmp_path: Path):
        """meta.json phase 0, no config.yaml -> meta.json wins."""
        _write_meta_json(tmp_path, "my-feature", {"status_phase": 0})
        phase, source = resolve_phase(tmp_path, "my-feature")
        assert phase == 0
        assert "meta.json" in source

    def test_invalid_meta_json_phase_ignored(self, _mock_branch, tmp_path: Path):
        """meta.json has phase 99 (invalid) -> falls through to config/default."""
        _write_meta_json(tmp_path, "my-feature", {"status_phase": 99})
        _write_config_yaml(tmp_path, "status:\n  phase: 0\n")
        phase, source = resolve_phase(tmp_path, "my-feature")
        assert phase == 0
        assert "config.yaml" in source

    def test_invalid_config_phase_ignored(self, _mock_branch, tmp_path: Path):
        """config.yaml has phase -1 (invalid) -> falls through to default."""
        _write_config_yaml(tmp_path, "status:\n  phase: -1\n")
        phase, source = resolve_phase(tmp_path, "my-feature")
        assert phase == DEFAULT_PHASE
        assert source == DEFAULT_PHASE_SOURCE

    def test_non_integer_phase_ignored(self, _mock_branch, tmp_path: Path):
        """meta.json has non-integer phase ("two") -> falls through."""
        _write_meta_json(tmp_path, "my-feature", {"status_phase": "two"})
        phase, source = resolve_phase(tmp_path, "my-feature")
        assert phase == DEFAULT_PHASE
        assert source == DEFAULT_PHASE_SOURCE

    def test_missing_meta_json_file(self, _mock_branch, tmp_path: Path):
        """No meta.json file at all -> gracefully returns None, falls to default."""
        phase, source = resolve_phase(tmp_path, "nonexistent-feature")
        assert phase == DEFAULT_PHASE
        assert source == DEFAULT_PHASE_SOURCE

    def test_missing_config_yaml_file(self, _mock_branch, tmp_path: Path):
        """No config.yaml -> gracefully skips, falls to default."""
        phase, source = resolve_phase(tmp_path, "some-feature")
        assert phase == DEFAULT_PHASE
        assert source == DEFAULT_PHASE_SOURCE

    def test_config_yaml_no_status_section(self, _mock_branch, tmp_path: Path):
        """config.yaml exists but has no 'status' key -> returns default."""
        _write_config_yaml(tmp_path, "agents:\n  available:\n    - claude\n")
        phase, source = resolve_phase(tmp_path, "some-feature")
        assert phase == DEFAULT_PHASE
        assert source == DEFAULT_PHASE_SOURCE

    def test_config_yaml_status_not_dict(self, _mock_branch, tmp_path: Path):
        """config.yaml has status: 'some string' (not a dict) -> treated as not set."""
        _write_config_yaml(tmp_path, "status: active\n")
        phase, source = resolve_phase(tmp_path, "some-feature")
        assert phase == DEFAULT_PHASE
        assert source == DEFAULT_PHASE_SOURCE


# ---------------------------------------------------------------------------
# 0.1x branch capping tests
# ---------------------------------------------------------------------------


@patch("specify_cli.status.phase.is_01x_branch", return_value=True)
class TestResolvePhaseOn01x:
    """Tests for resolve_phase when on a 0.1x branch (capping applies)."""

    def test_01x_cap_not_applied_when_within_limit(self, _mock_branch, tmp_path: Path):
        """Phase <= MAX_PHASE_01X is not capped on 0.1x branch."""
        _write_meta_json(tmp_path, "feat", {"status_phase": 2})
        phase, source = resolve_phase(tmp_path, "feat")
        assert phase == 2
        # No "(capped" text since 2 == MAX_PHASE_01X
        assert "capped" not in source


@patch("specify_cli.status.phase.is_01x_branch", return_value=False)
class TestResolvePhaseOn2x:
    """Tests for resolve_phase when on a 2.x branch (no capping)."""

    def test_01x_cap_not_applied_on_2x(self, _mock_branch, tmp_path: Path):
        """On 2.x branch, no capping is applied regardless of phase value."""
        _write_meta_json(tmp_path, "feat", {"status_phase": 2})
        phase, source = resolve_phase(tmp_path, "feat")
        assert phase == 2
        assert "capped" not in source


# ---------------------------------------------------------------------------
# is_01x_branch tests
# ---------------------------------------------------------------------------


class TestIs01xBranch:
    """Tests for is_01x_branch using mocked subprocess.run."""

    @patch("specify_cli.status.phase.subprocess.run")
    def test_is_01x_branch_main(self, mock_run, tmp_path: Path):
        """'main' branch is considered 0.1x -> True."""
        mock_run.return_value = _mock_branch("main")
        assert is_01x_branch(tmp_path) is True

    @patch("specify_cli.status.phase.subprocess.run")
    def test_is_01x_branch_2x(self, mock_run, tmp_path: Path):
        """'2.x' branch is NOT 0.1x -> False."""
        mock_run.return_value = _mock_branch("2.x")
        assert is_01x_branch(tmp_path) is False

    @patch("specify_cli.status.phase.subprocess.run")
    def test_is_01x_branch_feature(self, mock_run, tmp_path: Path):
        """'034-feature-name' branch is NOT 0.1x -> False."""
        mock_run.return_value = _mock_branch("034-feature-name")
        assert is_01x_branch(tmp_path) is False

    @patch("specify_cli.status.phase.subprocess.run")
    def test_is_01x_branch_2_dot_version(self, mock_run, tmp_path: Path):
        """'2.1' branch is NOT 0.1x -> False."""
        mock_run.return_value = _mock_branch("2.1")
        assert is_01x_branch(tmp_path) is False

    @patch("specify_cli.status.phase.subprocess.run")
    def test_is_01x_branch_release(self, mock_run, tmp_path: Path):
        """'release/0.15.0' branch is 0.1x -> True."""
        mock_run.return_value = _mock_branch("release/0.15.0")
        assert is_01x_branch(tmp_path) is True

    @patch("specify_cli.status.phase.subprocess.run")
    def test_is_01x_branch_git_error(self, mock_run, tmp_path: Path):
        """Git command failure -> returns False."""
        result = MagicMock()
        result.returncode = 128
        result.stdout = ""
        mock_run.return_value = result
        assert is_01x_branch(tmp_path) is False

    @patch("specify_cli.status.phase.subprocess.run")
    def test_is_01x_branch_timeout(self, mock_run, tmp_path: Path):
        """Subprocess timeout -> returns False."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=5)
        assert is_01x_branch(tmp_path) is False


# ---------------------------------------------------------------------------
# _read_meta_phase edge cases
# ---------------------------------------------------------------------------


class TestReadMetaPhase:
    """Direct tests for _read_meta_phase."""

    def test_malformed_json(self, tmp_path: Path):
        """Malformed JSON -> returns None (logs warning)."""
        feature_dir = tmp_path / "kitty-specs" / "bad-json"
        feature_dir.mkdir(parents=True)
        (feature_dir / "meta.json").write_text("{not valid json", encoding="utf-8")
        assert _read_meta_phase(tmp_path, "bad-json") is None

    def test_status_phase_missing_key(self, tmp_path: Path):
        """meta.json exists but has no status_phase key -> returns None."""
        _write_meta_json(tmp_path, "feat", {"name": "something"})
        assert _read_meta_phase(tmp_path, "feat") is None

    def test_all_valid_phases(self, tmp_path: Path):
        """All VALID_PHASES (0, 1, 2) are accepted."""
        for p in VALID_PHASES:
            _write_meta_json(tmp_path, "feat", {"status_phase": p})
            assert _read_meta_phase(tmp_path, "feat") == p


# ---------------------------------------------------------------------------
# _read_config_phase edge cases
# ---------------------------------------------------------------------------


class TestReadConfigPhase:
    """Direct tests for _read_config_phase."""

    def test_empty_config_file(self, tmp_path: Path):
        """Empty config file -> returns None."""
        _write_config_yaml(tmp_path, "")
        assert _read_config_phase(tmp_path) is None

    def test_config_with_only_status_phase(self, tmp_path: Path):
        """Minimal config with only status.phase."""
        _write_config_yaml(tmp_path, "status:\n  phase: 2\n")
        assert _read_config_phase(tmp_path) == 2

    def test_config_phase_as_string_number(self, tmp_path: Path):
        """Phase provided as string '1' -> int conversion works."""
        _write_config_yaml(tmp_path, 'status:\n  phase: "1"\n')
        assert _read_config_phase(tmp_path) == 1
