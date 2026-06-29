"""Sync server-URL resolution: D-5 compliance + #2146 target-authority.

`SyncConfig.get_server_url()` must honor `SPEC_KITTY_SAAS_URL` (the D-5 source
of truth) ahead of config, and must carry NO hardcoded SaaS domain — so `auth`
and `sync` can never resolve different targets, and an unconfigured checkout
fails loudly instead of silently pointing at a dead default.
"""

import pytest

from specify_cli.auth.errors import ConfigurationError
from specify_cli.sync.config import SyncConfig


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
    config = SyncConfig()
    config.config_file = tmp_path / "config.toml"
    return config


def test_env_takes_precedence_over_config(cfg, monkeypatch):
    cfg.set_server_url("https://from-config.example.com")
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "http://localhost:8000")
    assert cfg.get_server_url() == "http://localhost:8000"


def test_config_used_when_env_unset(cfg, monkeypatch):
    monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
    cfg.set_server_url("https://from-config.example.com/")
    assert cfg.get_server_url() == "https://from-config.example.com"


def test_env_trailing_slash_stripped(cfg, monkeypatch):
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "http://localhost:8000/")
    assert cfg.get_server_url() == "http://localhost:8000"


def test_no_hardcoded_default_raises_when_unconfigured(cfg, monkeypatch):
    monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
    # No env, no config key -> must NOT return a hardcoded domain (D-5).
    with pytest.raises(ConfigurationError):
        cfg.get_server_url()
