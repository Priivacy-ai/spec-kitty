"""Tests for resolve_upgrade_provider."""

from __future__ import annotations

from typing import Any

import pytest

from specify_cli.compat.provider import FakeLatestVersionProvider, PyPIProvider
from specify_cli.distribution.upgrade_provider import (

    PROVIDER_SELECT_ENV_VAR,
    clear_upgrade_provider_cache,
    resolve_upgrade_provider,
)

pytestmark = pytest.mark.fast



class _FakeEntryPoint:
    def __init__(self, name: str, payload: Any) -> None:
        self.name = name
        self._payload = payload

    def load(self) -> Any:
        if isinstance(self._payload, BaseException):
            raise self._payload
        return self._payload


class _GoodProvider:
    def get_latest(self, package: str) -> Any:
        return FakeLatestVersionProvider(version="9.9.9").get_latest(package)


class _BadProvider:
    pass


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    clear_upgrade_provider_cache()
    yield
    clear_upgrade_provider_cache()


def test_default_pypi_when_none_registered(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "specify_cli.distribution.upgrade_provider.entry_points",
        lambda group: [],
    )
    provider = resolve_upgrade_provider()
    assert isinstance(provider, PyPIProvider)


def test_single_registered_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "specify_cli.distribution.upgrade_provider.entry_points",
        lambda group: [_FakeEntryPoint("acme", _GoodProvider)],
    )
    provider = resolve_upgrade_provider()
    assert isinstance(provider, _GoodProvider)


def test_env_selects_among_multiple(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(PROVIDER_SELECT_ENV_VAR, "zeta")
    monkeypatch.setattr(
        "specify_cli.distribution.upgrade_provider.entry_points",
        lambda group: [
            _FakeEntryPoint("alpha", _BadProvider),
            _FakeEntryPoint("zeta", _GoodProvider),
        ],
    )
    provider = resolve_upgrade_provider()
    assert isinstance(provider, _GoodProvider)


def test_alphabetical_when_multi_and_no_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(PROVIDER_SELECT_ENV_VAR, raising=False)
    monkeypatch.setattr(
        "specify_cli.distribution.upgrade_provider.entry_points",
        lambda group: [
            _FakeEntryPoint("zeta", _BadProvider),
            _FakeEntryPoint("alpha", _GoodProvider),
        ],
    )
    provider = resolve_upgrade_provider()
    assert isinstance(provider, _GoodProvider)


def test_unknown_env_falls_back_to_alphabetical(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(PROVIDER_SELECT_ENV_VAR, "does-not-exist")
    monkeypatch.setattr(
        "specify_cli.distribution.upgrade_provider.entry_points",
        lambda group: [
            _FakeEntryPoint("zeta", _BadProvider),
            _FakeEntryPoint("alpha", _GoodProvider),
        ],
    )
    provider = resolve_upgrade_provider()
    assert isinstance(provider, _GoodProvider)


def test_load_failure_returns_pypi(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "specify_cli.distribution.upgrade_provider.entry_points",
        lambda group: [_FakeEntryPoint("broken", RuntimeError("nope"))],
    )
    provider = resolve_upgrade_provider()
    assert isinstance(provider, PyPIProvider)


def test_missing_get_latest_returns_pypi(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "specify_cli.distribution.upgrade_provider.entry_points",
        lambda group: [_FakeEntryPoint("bad", _BadProvider)],
    )
    provider = resolve_upgrade_provider()
    assert isinstance(provider, PyPIProvider)


def test_never_raises_on_entry_points_blowup(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*, group: str) -> list[Any]:
        raise RuntimeError("metadata broken")

    monkeypatch.setattr(
        "specify_cli.distribution.upgrade_provider.entry_points",
        boom,
    )
    provider = resolve_upgrade_provider()
    assert isinstance(provider, PyPIProvider)


def test_memoizes_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def counting(*, group: str) -> list[_FakeEntryPoint]:
        calls["n"] += 1
        return [_FakeEntryPoint("once", _GoodProvider)]

    monkeypatch.setattr(
        "specify_cli.distribution.upgrade_provider.entry_points",
        counting,
    )
    assert isinstance(resolve_upgrade_provider(), _GoodProvider)
    assert isinstance(resolve_upgrade_provider(), _GoodProvider)
    assert calls["n"] == 1
