"""Tests for ``specify_cli.auth.config`` (feature 080, WP01 T002)."""

from __future__ import annotations

import pytest

from specify_cli.auth.config import get_saas_base_url
from specify_cli.auth.errors import ConfigurationError


def test_get_saas_base_url_reads_env_var(monkeypatch):
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://saas.test")
    assert get_saas_base_url() == "https://saas.test"


def test_get_saas_base_url_strips_trailing_slash(monkeypatch):
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://saas.test/")
    assert get_saas_base_url() == "https://saas.test"


def test_get_saas_base_url_strips_multiple_trailing_slashes(monkeypatch):
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://saas.test///")
    assert get_saas_base_url() == "https://saas.test"


def test_get_saas_base_url_raises_when_unset(monkeypatch):
    monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
    with pytest.raises(ConfigurationError) as excinfo:
        get_saas_base_url()
    assert "SPEC_KITTY_SAAS_URL" in str(excinfo.value)


def test_get_saas_base_url_raises_when_empty(monkeypatch):
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "")
    with pytest.raises(ConfigurationError):
        get_saas_base_url()


def test_configuration_error_is_authentication_error():
    from specify_cli.auth.errors import AuthenticationError

    assert issubclass(ConfigurationError, AuthenticationError)
