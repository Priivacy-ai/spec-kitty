"""Hosted deployments still use the current GitHub Releases channel.

Issue #214: a hosted Team Kitty target no longer suppresses the startup
no-upgrade notice. The notice now checks the programme's private GitHub
Releases channel, so it can catch a build installed from the abandoned
pre-fork line even when ``SPEC_KITTY_SAAS_URL`` is configured.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.core.version_checker import maybe_emit_no_upgrade_notice

pytestmark = [pytest.mark.fast]

SAAS_URL_ENV_VAR = "SPEC_KITTY_SAAS_URL"

_EMIT_SEAM = "specify_cli.core.upgrade_notifier.maybe_emit_upgrade_notice"


@pytest.fixture
def isolated_target(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Isolate config.toml under a throwaway ``SPEC_KITTY_HOME``, no env leakage."""
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path))
    monkeypatch.delenv(SAAS_URL_ENV_VAR, raising=False)
    monkeypatch.setenv("SPEC_KITTY_CLI_VERSION", "3.2.6rc3")
    return tmp_path


def _gate_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the inputs so only the hosted-target configuration can vary."""
    from specify_cli.distribution.profile import DistributionProfile

    monkeypatch.setattr(
        "specify_cli.distribution.resolve_distribution_profile",
        lambda: DistributionProfile(package_name="spec-kitty-cli"),
    )
    monkeypatch.setattr(
        "specify_cli.core.version_checker.should_check_version",
        lambda _name: True,
    )


def _spy_emit(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Replace the downstream notifier with a spy; returns the versions it saw."""
    seen: list[str] = []
    monkeypatch.setattr(_EMIT_SEAM, lambda version: seen.append(version) or True)
    return seen


def test_env_configured_target_still_checks_release_channel(isolated_target: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(SAAS_URL_ENV_VAR, "https://team.example.exe.xyz")
    _gate_profile(monkeypatch)
    seen = _spy_emit(monkeypatch)

    assert maybe_emit_no_upgrade_notice("status") is True
    assert seen == ["3.2.6rc3"]


def test_config_toml_target_still_checks_release_channel(isolated_target: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (isolated_target / "config.toml").write_text('[sync]\nserver_url = "https://team.spec-kitty.ai"\n', encoding="utf-8")
    _gate_profile(monkeypatch)
    seen = _spy_emit(monkeypatch)

    assert maybe_emit_no_upgrade_notice("status") is True
    assert seen == ["3.2.6rc3"]
