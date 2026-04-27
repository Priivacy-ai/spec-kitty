"""Tests for specify_cli.compat.config (T010 — UpgradeConfig).

Uses ``monkeypatch`` for env vars and ``tmp_path`` for config files.
No real user config file is read.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.compat.config import (
    _DEFAULT_THROTTLE_SECONDS,
    _MAX_THROTTLE_SECONDS,
    _MIN_THROTTLE_SECONDS,
    UpgradeConfig,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_yaml(path: Path, content: str) -> None:
    """Write content to path, creating parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _patch_config_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Redirect config resolution to tmp_path/config and return the yaml path."""
    config_dir = tmp_path / "spec-kitty"
    config_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = config_dir / "upgrade.yaml"

    # Patch _resolve_config_dir to return our tmp dir.
    monkeypatch.setattr(
        "specify_cli.compat.config._resolve_config_dir",
        lambda: str(config_dir),
    )
    return yaml_path


# ---------------------------------------------------------------------------
# Defaults (no env, no file)
# ---------------------------------------------------------------------------


class TestDefaults:
    """When no env vars and no YAML file, defaults apply."""

    def test_default_throttle(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Default throttle_seconds is 86400."""
        monkeypatch.delenv("SPEC_KITTY_NAG_THROTTLE_SECONDS", raising=False)
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        _patch_config_dir(monkeypatch, tmp_path)  # points to empty dir (no yaml)

        cfg = UpgradeConfig.load()
        assert cfg.throttle_seconds == _DEFAULT_THROTTLE_SECONDS

    def test_default_nag_enabled(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Default nag_enabled is True."""
        monkeypatch.delenv("SPEC_KITTY_NAG_THROTTLE_SECONDS", raising=False)
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        _patch_config_dir(monkeypatch, tmp_path)

        cfg = UpgradeConfig.load()
        assert cfg.nag_enabled is True


# ---------------------------------------------------------------------------
# Env-only overrides
# ---------------------------------------------------------------------------


class TestEnvOnly:
    """Environment variables override YAML and defaults."""

    def test_env_throttle_overrides_default(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """SPEC_KITTY_NAG_THROTTLE_SECONDS env overrides default."""
        monkeypatch.setenv("SPEC_KITTY_NAG_THROTTLE_SECONDS", "3600")
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        _patch_config_dir(monkeypatch, tmp_path)

        cfg = UpgradeConfig.load()
        assert cfg.throttle_seconds == 3600

    def test_no_nag_env_1_disables(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """SPEC_KITTY_NO_NAG=1 disables nag."""
        monkeypatch.delenv("SPEC_KITTY_NAG_THROTTLE_SECONDS", raising=False)
        monkeypatch.setenv("SPEC_KITTY_NO_NAG", "1")
        _patch_config_dir(monkeypatch, tmp_path)

        cfg = UpgradeConfig.load()
        assert cfg.nag_enabled is False

    def test_no_nag_env_true_disables(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """SPEC_KITTY_NO_NAG=true disables nag."""
        monkeypatch.delenv("SPEC_KITTY_NAG_THROTTLE_SECONDS", raising=False)
        monkeypatch.setenv("SPEC_KITTY_NO_NAG", "true")
        _patch_config_dir(monkeypatch, tmp_path)

        cfg = UpgradeConfig.load()
        assert cfg.nag_enabled is False

    def test_no_nag_env_yes_disables(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """SPEC_KITTY_NO_NAG=yes disables nag."""
        monkeypatch.delenv("SPEC_KITTY_NAG_THROTTLE_SECONDS", raising=False)
        monkeypatch.setenv("SPEC_KITTY_NO_NAG", "yes")
        _patch_config_dir(monkeypatch, tmp_path)

        cfg = UpgradeConfig.load()
        assert cfg.nag_enabled is False

    def test_no_nag_env_empty_keeps_enabled(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """SPEC_KITTY_NO_NAG='' leaves nag enabled."""
        monkeypatch.delenv("SPEC_KITTY_NAG_THROTTLE_SECONDS", raising=False)
        monkeypatch.setenv("SPEC_KITTY_NO_NAG", "")
        _patch_config_dir(monkeypatch, tmp_path)

        cfg = UpgradeConfig.load()
        assert cfg.nag_enabled is True

    def test_no_nag_env_0_keeps_enabled(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """SPEC_KITTY_NO_NAG=0 leaves nag enabled (not a truthy value)."""
        monkeypatch.delenv("SPEC_KITTY_NAG_THROTTLE_SECONDS", raising=False)
        monkeypatch.setenv("SPEC_KITTY_NO_NAG", "0")
        _patch_config_dir(monkeypatch, tmp_path)

        cfg = UpgradeConfig.load()
        assert cfg.nag_enabled is True


# ---------------------------------------------------------------------------
# File-only (no env override)
# ---------------------------------------------------------------------------


class TestFileOnly:
    """YAML file overrides defaults when no env var is set."""

    def test_file_throttle_overrides_default(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """YAML nag.throttle_seconds overrides default."""
        monkeypatch.delenv("SPEC_KITTY_NAG_THROTTLE_SECONDS", raising=False)
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        yaml_path = _patch_config_dir(monkeypatch, tmp_path)
        _write_yaml(yaml_path, "nag:\n  throttle_seconds: 7200\n")

        cfg = UpgradeConfig.load()
        assert cfg.throttle_seconds == 7200

    def test_file_nag_disabled(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """YAML nag.enabled: false disables nag."""
        monkeypatch.delenv("SPEC_KITTY_NAG_THROTTLE_SECONDS", raising=False)
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        yaml_path = _patch_config_dir(monkeypatch, tmp_path)
        _write_yaml(yaml_path, "nag:\n  enabled: false\n")

        cfg = UpgradeConfig.load()
        assert cfg.nag_enabled is False

    def test_file_nag_enabled_explicitly(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """YAML nag.enabled: true leaves nag enabled."""
        monkeypatch.delenv("SPEC_KITTY_NAG_THROTTLE_SECONDS", raising=False)
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        yaml_path = _patch_config_dir(monkeypatch, tmp_path)
        _write_yaml(yaml_path, "nag:\n  enabled: true\n")

        cfg = UpgradeConfig.load()
        assert cfg.nag_enabled is True


# ---------------------------------------------------------------------------
# Env wins over file
# ---------------------------------------------------------------------------


class TestEnvWinsOverFile:
    """Env values override YAML file values."""

    def test_env_throttle_wins_over_yaml(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Env SPEC_KITTY_NAG_THROTTLE_SECONDS beats YAML nag.throttle_seconds."""
        monkeypatch.setenv("SPEC_KITTY_NAG_THROTTLE_SECONDS", "1800")
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        yaml_path = _patch_config_dir(monkeypatch, tmp_path)
        _write_yaml(yaml_path, "nag:\n  throttle_seconds: 7200\n")

        cfg = UpgradeConfig.load()
        assert cfg.throttle_seconds == 1800

    def test_env_no_nag_wins_over_yaml_enabled(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """SPEC_KITTY_NO_NAG=1 beats YAML nag.enabled: true."""
        monkeypatch.delenv("SPEC_KITTY_NAG_THROTTLE_SECONDS", raising=False)
        monkeypatch.setenv("SPEC_KITTY_NO_NAG", "1")
        yaml_path = _patch_config_dir(monkeypatch, tmp_path)
        _write_yaml(yaml_path, "nag:\n  enabled: true\n")

        cfg = UpgradeConfig.load()
        assert cfg.nag_enabled is False


# ---------------------------------------------------------------------------
# Missing file
# ---------------------------------------------------------------------------


class TestMissingFile:
    """Missing YAML file is fine — defaults apply."""

    def test_missing_file_uses_defaults(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """No YAML file → defaults apply without error."""
        monkeypatch.delenv("SPEC_KITTY_NAG_THROTTLE_SECONDS", raising=False)
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        # Point to a directory with no upgrade.yaml
        empty_dir = tmp_path / "empty-spec-kitty"
        empty_dir.mkdir()
        monkeypatch.setattr("specify_cli.compat.config._resolve_config_dir", lambda: str(empty_dir))

        cfg = UpgradeConfig.load()
        assert cfg.throttle_seconds == _DEFAULT_THROTTLE_SECONDS
        assert cfg.nag_enabled is True


# ---------------------------------------------------------------------------
# Malformed YAML
# ---------------------------------------------------------------------------


class TestMalformedYaml:
    """Malformed YAML falls back to defaults without raising."""

    def test_malformed_yaml_uses_defaults(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Malformed YAML → defaults, no exception."""
        monkeypatch.delenv("SPEC_KITTY_NAG_THROTTLE_SECONDS", raising=False)
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        yaml_path = _patch_config_dir(monkeypatch, tmp_path)
        _write_yaml(yaml_path, "nag: [unclosed: {bracket")

        cfg = UpgradeConfig.load()
        assert cfg.throttle_seconds == _DEFAULT_THROTTLE_SECONDS
        assert cfg.nag_enabled is True

    def test_non_mapping_yaml_uses_defaults(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Top-level YAML list → defaults."""
        monkeypatch.delenv("SPEC_KITTY_NAG_THROTTLE_SECONDS", raising=False)
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        yaml_path = _patch_config_dir(monkeypatch, tmp_path)
        _write_yaml(yaml_path, "- item1\n- item2\n")

        cfg = UpgradeConfig.load()
        assert cfg.throttle_seconds == _DEFAULT_THROTTLE_SECONDS


# ---------------------------------------------------------------------------
# Range validation
# ---------------------------------------------------------------------------


class TestRangeValidation:
    """Out-of-range throttle values fall back to default (CHK025)."""

    def test_throttle_below_min_falls_back(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Throttle < 60 → falls back to default."""
        monkeypatch.setenv("SPEC_KITTY_NAG_THROTTLE_SECONDS", "59")
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        _patch_config_dir(monkeypatch, tmp_path)

        cfg = UpgradeConfig.load()
        assert cfg.throttle_seconds == _DEFAULT_THROTTLE_SECONDS

    def test_throttle_above_max_falls_back(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Throttle > 31_536_000 → falls back to default."""
        too_large = _MAX_THROTTLE_SECONDS + 1
        monkeypatch.setenv("SPEC_KITTY_NAG_THROTTLE_SECONDS", str(too_large))
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        _patch_config_dir(monkeypatch, tmp_path)

        cfg = UpgradeConfig.load()
        assert cfg.throttle_seconds == _DEFAULT_THROTTLE_SECONDS

    def test_throttle_at_min_is_accepted(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Throttle == 60 → accepted."""
        monkeypatch.setenv("SPEC_KITTY_NAG_THROTTLE_SECONDS", "60")
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        _patch_config_dir(monkeypatch, tmp_path)

        cfg = UpgradeConfig.load()
        assert cfg.throttle_seconds == _MIN_THROTTLE_SECONDS

    def test_throttle_at_max_is_accepted(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Throttle == 31_536_000 → accepted."""
        monkeypatch.setenv("SPEC_KITTY_NAG_THROTTLE_SECONDS", str(_MAX_THROTTLE_SECONDS))
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        _patch_config_dir(monkeypatch, tmp_path)

        cfg = UpgradeConfig.load()
        assert cfg.throttle_seconds == _MAX_THROTTLE_SECONDS

    def test_non_integer_env_falls_back(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Non-integer SPEC_KITTY_NAG_THROTTLE_SECONDS → falls back to default."""
        monkeypatch.setenv("SPEC_KITTY_NAG_THROTTLE_SECONDS", "not-a-number")
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        _patch_config_dir(monkeypatch, tmp_path)

        cfg = UpgradeConfig.load()
        assert cfg.throttle_seconds == _DEFAULT_THROTTLE_SECONDS

    def test_out_of_range_yaml_falls_back(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Out-of-range YAML throttle → falls back to default."""
        monkeypatch.delenv("SPEC_KITTY_NAG_THROTTLE_SECONDS", raising=False)
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        yaml_path = _patch_config_dir(monkeypatch, tmp_path)
        _write_yaml(yaml_path, "nag:\n  throttle_seconds: 10\n")

        cfg = UpgradeConfig.load()
        assert cfg.throttle_seconds == _DEFAULT_THROTTLE_SECONDS

    def test_non_integer_yaml_falls_back(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Non-integer YAML throttle → falls back to default."""
        monkeypatch.delenv("SPEC_KITTY_NAG_THROTTLE_SECONDS", raising=False)
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        yaml_path = _patch_config_dir(monkeypatch, tmp_path)
        _write_yaml(yaml_path, "nag:\n  throttle_seconds: 'not-a-number'\n")

        cfg = UpgradeConfig.load()
        assert cfg.throttle_seconds == _DEFAULT_THROTTLE_SECONDS

    def test_no_exception_on_out_of_range(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Out-of-range throttle must not raise any exception."""
        monkeypatch.setenv("SPEC_KITTY_NAG_THROTTLE_SECONDS", "0")
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        _patch_config_dir(monkeypatch, tmp_path)

        # Must not raise.
        cfg = UpgradeConfig.load()
        assert cfg.throttle_seconds == _DEFAULT_THROTTLE_SECONDS
