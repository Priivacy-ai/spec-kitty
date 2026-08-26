"""Issue #178: the WP09 no-upgrade notices stay quiet on hosted deployments.

The notices compare the running build against **public PyPI**. During the
programme nothing is published to PyPI — releases land as GitHub Releases on
``spec-kitty/EXPERIMENTAL-spec-kitty`` (planning#94) — so when an explicit
hosted Team Kitty target is configured (``SPEC_KITTY_SAAS_URL`` or
``config.toml [sync].server_url``) the comparison is meaningless noise
("build is ahead of the latest PyPI release") and
:func:`maybe_emit_no_upgrade_notice` stays silent, skipping the probe
entirely. With nothing configured, stock behaviour is unchanged.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.core.version_checker import maybe_emit_no_upgrade_notice

pytestmark = [pytest.mark.fast]

SAAS_URL_ENV_VAR = "SPEC_KITTY_SAAS_URL"

_EMIT_SEAM = "specify_cli.core.upgrade_notifier.maybe_emit_upgrade_notice"
_RESOLVE_SEAM = "specify_cli.auth.server_target.resolve_server_target"


@pytest.fixture
def isolated_target(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Isolate config.toml under a throwaway ``SPEC_KITTY_HOME``, no env leakage."""
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path))
    monkeypatch.delenv(SAAS_URL_ENV_VAR, raising=False)
    # Deterministic installed version regardless of host/test-mode overrides.
    monkeypatch.setenv("SPEC_KITTY_CLI_VERSION", "3.2.0")
    return tmp_path


def _gate_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the FR-015 inputs so only the hosted-target gate can vary."""
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


def test_env_configured_target_suppresses_notice_and_skips_probe(
    isolated_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(SAAS_URL_ENV_VAR, "https://team.example.exe.xyz")
    _gate_profile(monkeypatch)
    seen = _spy_emit(monkeypatch)

    assert maybe_emit_no_upgrade_notice("status") is False
    assert seen == []


def test_config_toml_target_suppresses_notice_and_skips_probe(
    isolated_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (isolated_target / "config.toml").write_text(
        '[sync]\nserver_url = "https://team.spec-kitty.ai"\n', encoding="utf-8"
    )
    _gate_profile(monkeypatch)
    seen = _spy_emit(monkeypatch)

    assert maybe_emit_no_upgrade_notice("status") is False
    assert seen == []


def test_blank_env_value_counts_as_not_configured(
    isolated_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(SAAS_URL_ENV_VAR, "   ")
    _gate_profile(monkeypatch)
    seen = _spy_emit(monkeypatch)

    assert maybe_emit_no_upgrade_notice("status") is True
    assert seen == ["3.2.0"]


def test_nothing_configured_keeps_stock_behaviour(
    isolated_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _gate_profile(monkeypatch)
    seen = _spy_emit(monkeypatch)

    assert maybe_emit_no_upgrade_notice("status") is True
    assert seen == ["3.2.0"]


def test_resolver_failure_fails_open_to_stock_behaviour(
    isolated_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A broken target resolution must not take the notices down with it."""

    def _boom(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("resolver exploded")

    monkeypatch.setattr(_RESOLVE_SEAM, _boom)
    _gate_profile(monkeypatch)
    seen = _spy_emit(monkeypatch)

    assert maybe_emit_no_upgrade_notice("status") is True
    assert seen == ["3.2.0"]
