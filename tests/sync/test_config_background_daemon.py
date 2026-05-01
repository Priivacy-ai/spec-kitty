"""T014 — Unit tests for BackgroundDaemonPolicy config extension on SyncConfig.

All tests monkeypatch Path.home() to tmp_path so SyncConfig resolves
~/.spec-kitty/config.toml to a throwaway directory.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.sync.config import BackgroundDaemonPolicy, SyncConfig

AUTO = BackgroundDaemonPolicy.AUTO
MANUAL = BackgroundDaemonPolicy.MANUAL

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_config(tmp_path: Path, content: str) -> None:
    """Write content to the config.toml inside the fake home dir."""
    config_dir = tmp_path / ".spec-kitty"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.toml").write_text(content)


def _make_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> SyncConfig:
    """Return a SyncConfig whose home is redirected to tmp_path."""
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    return SyncConfig()


# ---------------------------------------------------------------------------
# Default / missing key tests
# ---------------------------------------------------------------------------


def test_default_when_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """No config file at all → AUTO."""
    cfg = _make_config(monkeypatch, tmp_path)
    assert cfg.get_background_daemon() == AUTO


def test_default_when_sync_table_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Config file exists but has no [sync] table → AUTO."""
    _write_config(tmp_path, "[other]\nfoo = 1\n")
    cfg = _make_config(monkeypatch, tmp_path)
    assert cfg.get_background_daemon() == AUTO


def test_default_when_key_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """[sync] table present but background_daemon key absent → AUTO."""
    _write_config(tmp_path, '[sync]\nserver_url = "https://example.com"\n')
    cfg = _make_config(monkeypatch, tmp_path)
    assert cfg.get_background_daemon() == AUTO


# ---------------------------------------------------------------------------
# Case-insensitive "auto" parsing
# ---------------------------------------------------------------------------


def test_auto_lowercase(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """background_daemon = "auto" → AUTO."""
    _write_config(tmp_path, '[sync]\nbackground_daemon = "auto"\n')
    cfg = _make_config(monkeypatch, tmp_path)
    assert cfg.get_background_daemon() == AUTO


def test_auto_uppercase(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """background_daemon = "AUTO" → AUTO."""
    _write_config(tmp_path, '[sync]\nbackground_daemon = "AUTO"\n')
    cfg = _make_config(monkeypatch, tmp_path)
    assert cfg.get_background_daemon() == AUTO


def test_auto_mixed_case(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """background_daemon = "Auto" → AUTO."""
    _write_config(tmp_path, '[sync]\nbackground_daemon = "Auto"\n')
    cfg = _make_config(monkeypatch, tmp_path)
    assert cfg.get_background_daemon() == AUTO


# ---------------------------------------------------------------------------
# "manual" parsing
# ---------------------------------------------------------------------------


def test_manual_lowercase(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """background_daemon = "manual" → MANUAL."""
    _write_config(tmp_path, '[sync]\nbackground_daemon = "manual"\n')
    cfg = _make_config(monkeypatch, tmp_path)
    assert cfg.get_background_daemon() == MANUAL


def test_manual_mixed_case(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """background_daemon = "Manual" → MANUAL."""
    _write_config(tmp_path, '[sync]\nbackground_daemon = "Manual"\n')
    cfg = _make_config(monkeypatch, tmp_path)
    assert cfg.get_background_daemon() == MANUAL


# ---------------------------------------------------------------------------
# Unknown / bad values
# ---------------------------------------------------------------------------


def test_unknown_value_warns_and_defaults(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Unknown value "banana" → returns AUTO and prints warning to stderr."""
    _write_config(tmp_path, '[sync]\nbackground_daemon = "banana"\n')
    cfg = _make_config(monkeypatch, tmp_path)
    result = cfg.get_background_daemon()
    assert result == AUTO
    err = capsys.readouterr().err
    assert "banana" in err
    assert "unknown" in err
    assert "auto" in err


def test_empty_string_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Empty string value → raises ValueError."""
    _write_config(tmp_path, '[sync]\nbackground_daemon = ""\n')
    cfg = _make_config(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="must be 'auto' or 'manual'"):
        cfg.get_background_daemon()


def test_whitespace_value_accepted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Whitespace-padded "  auto  " → AUTO (strip then match)."""
    _write_config(tmp_path, '[sync]\nbackground_daemon = "  auto  "\n')
    cfg = _make_config(monkeypatch, tmp_path)
    assert cfg.get_background_daemon() == AUTO


# ---------------------------------------------------------------------------
# Backcompat: existing config without new key
# ---------------------------------------------------------------------------


def test_backcompat_existing_config_without_new_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Existing config with server_url + max_queue_size but no background_daemon
    still returns AUTO, and the existing getters still return their values."""
    _write_config(
        tmp_path,
        '[sync]\nserver_url = "https://example.com"\nmax_queue_size = 500\n',
    )
    cfg = _make_config(monkeypatch, tmp_path)
    assert cfg.get_background_daemon() == AUTO
    assert cfg.get_server_url() == "https://example.com"
    assert cfg.get_max_queue_size() == 500


# ---------------------------------------------------------------------------
# Roundtrip via setter
# ---------------------------------------------------------------------------


def test_setter_roundtrip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """set_background_daemon(MANUAL) then get_background_daemon() → MANUAL."""
    cfg = _make_config(monkeypatch, tmp_path)
    cfg.set_background_daemon(MANUAL)
    assert cfg.get_background_daemon() == MANUAL
