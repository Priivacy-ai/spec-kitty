"""State doctor reports the authoritative runtime root.

Mission spec-kitty-home-isolation (issue #2171), WP05 — FR-009, FR-010, SC-004.

The state doctor's reported global-sync root, and the per-surface presence
checks under ``StateRoot.GLOBAL_SYNC``, must resolve to
``get_runtime_root().base`` under every supported env configuration — never an
independently recomputed ``~/.spec-kitty`` literal.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.paths import get_runtime_root
from specify_cli.state import doctor as doctor_mod
from specify_cli.state.contract import (
    AuthorityClass,
    GitClass,
    StateFormat,
    StateRoot,
    StateSurface,
)
from specify_cli.state.doctor import StateRootsReport, check_state_roots

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _global_sync_root(report: StateRootsReport) -> Path:
    """Return the resolved global-sync root from a state-roots report."""
    return next(
        r.resolved_path for r in report.roots if r.name == "global_sync"
    )


def _sync_config_present(report: StateRootsReport) -> bool:
    """Return whether the ``sync_config`` surface was reported present."""
    return next(
        s.present for s in report.surfaces if s.surface.name == "sync_config"
    )


def test_reported_root_matches_runtime_root_with_env(tmp_path, monkeypatch):
    """SPEC_KITTY_HOME set: reported global-sync root == base == env value."""
    env_root = tmp_path / "custom-home"
    env_root.mkdir()
    monkeypatch.setenv("SPEC_KITTY_HOME", str(env_root))

    report = check_state_roots(tmp_path)

    assert _global_sync_root(report) == get_runtime_root().base == env_root


def test_reported_root_matches_runtime_root_without_env(tmp_path, monkeypatch):
    """SPEC_KITTY_HOME unset: reported root == base (default ~/.spec-kitty)."""
    monkeypatch.delenv("SPEC_KITTY_HOME", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    report = check_state_roots(tmp_path)

    assert _global_sync_root(report) == get_runtime_root().base
    assert _global_sync_root(report) == tmp_path / ".spec-kitty"


def test_global_sync_surface_resolves_under_env_root(tmp_path, monkeypatch):
    """A ``~/.spec-kitty/`` surface is found under the env root, not HOME."""
    real_home = tmp_path / "home"
    real_home.mkdir()
    env_root = tmp_path / "custom-home"
    env_root.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: real_home))
    monkeypatch.setenv("SPEC_KITTY_HOME", str(env_root))

    # sync_config pattern is "~/.spec-kitty/config.toml" -> base / "config.toml".
    (env_root / "config.toml").write_text("[sync]\n")

    assert _sync_config_present(check_state_roots(tmp_path)) is True


def test_global_sync_surface_ignores_legacy_default_home(tmp_path, monkeypatch):
    """A file only under ~/.spec-kitty is NOT present when env root wins."""
    real_home = tmp_path / "home"
    real_home.mkdir()
    env_root = tmp_path / "custom-home"
    env_root.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: real_home))
    monkeypatch.setenv("SPEC_KITTY_HOME", str(env_root))

    legacy = real_home / ".spec-kitty"
    legacy.mkdir()
    (legacy / "config.toml").write_text("[sync]\n")

    assert _sync_config_present(check_state_roots(tmp_path)) is False


def test_global_sync_bare_pattern_resolves_under_base(tmp_path, monkeypatch):
    """A bare (non-``~/``) GLOBAL_SYNC pattern joins directly onto base."""
    env_root = tmp_path / "custom-home"
    env_root.mkdir()
    monkeypatch.setenv("SPEC_KITTY_HOME", str(env_root))
    (env_root / "bare-marker").write_text("x")

    surface = StateSurface(
        name="synthetic_bare",
        path_pattern="bare-marker",
        root=StateRoot.GLOBAL_SYNC,
        format=StateFormat.TEXT,
        authority=AuthorityClass.LOCAL_RUNTIME,
        git_class=GitClass.OUTSIDE_REPO,
        owner_module="test",
        creation_trigger="test",
    )

    assert doctor_mod._check_surface_present(tmp_path, surface) is True
