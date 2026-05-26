"""Tests for charter preflight project-level config."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.charter_preflight.config import load_preflight_config


pytestmark = [pytest.mark.fast]

def test_missing_config_defaults_to_enabled_without_auto_refresh(tmp_path: Path) -> None:
    cfg = load_preflight_config(tmp_path)

    assert cfg.enabled is True
    assert cfg.auto_refresh is False


def test_config_can_disable_preflight(tmp_path: Path) -> None:
    config_path = tmp_path / ".kittify" / "config.yaml"
    config_path.parent.mkdir()
    config_path.write_text(
        "preflight:\n  enabled: false\n  auto_refresh: true\n",
        encoding="utf-8",
    )

    cfg = load_preflight_config(tmp_path)

    assert cfg.enabled is False
    assert cfg.auto_refresh is True
