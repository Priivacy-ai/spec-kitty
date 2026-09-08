"""Tests for ``specify_cli.auth.config`` (feature 080, WP01 T002)."""

from __future__ import annotations

import pytest

from specify_cli.auth.config import (
    DEFAULT_HOSTED_SAAS_URL,
    get_saas_base_url,
    get_saas_url_env_override,
)
from specify_cli.auth.errors import ConfigurationError


pytestmark = [pytest.mark.integration]

def test_get_saas_base_url_reads_env_var(monkeypatch):
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://saas.test")
    assert get_saas_base_url() == "https://saas.test"


def test_get_saas_base_url_strips_trailing_slash(monkeypatch):
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://saas.test/")
    assert get_saas_base_url() == "https://saas.test"


def test_get_saas_base_url_strips_multiple_trailing_slashes(monkeypatch):
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://saas.test///")
    assert get_saas_base_url() == "https://saas.test"


def test_get_saas_base_url_returns_packaged_default_when_unset(monkeypatch):
    """#3980 (D-5 revised): the packaged default is the target — an unset
    override resolves to it instead of raising."""
    monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
    assert get_saas_base_url() == DEFAULT_HOSTED_SAAS_URL


def test_get_saas_base_url_returns_packaged_default_when_empty(monkeypatch):
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "")
    assert get_saas_base_url() == DEFAULT_HOSTED_SAAS_URL


def test_get_saas_url_env_override_reader_is_env_only(monkeypatch):
    """The env-override accessor the resolver consumes: unset/blank is no
    opinion (``None``), never the packaged default itself."""
    monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
    assert get_saas_url_env_override() is None
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "  ")
    assert get_saas_url_env_override() is None
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://env.test/")
    assert get_saas_url_env_override() == "https://env.test"


def test_configuration_error_is_authentication_error():
    from specify_cli.auth.errors import AuthenticationError

    assert issubclass(ConfigurationError, AuthenticationError)
