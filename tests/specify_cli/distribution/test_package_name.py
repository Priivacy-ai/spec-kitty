"""Tests for resolve_cli_package_name."""

from __future__ import annotations

from typing import Any

import pytest

from specify_cli.distribution.package_name import (

    DEFAULT_CLI_PACKAGE_NAME,
    clear_cli_package_name_cache,
    resolve_cli_package_name,
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


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    clear_cli_package_name_cache()
    yield
    clear_cli_package_name_cache()


def test_default_when_no_entry_points_or_distributions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "specify_cli.distribution.package_name.entry_points",
        lambda group: [],
    )
    monkeypatch.setattr(
        "specify_cli.distribution.package_name.packages_distributions",
        lambda: {},
    )
    assert resolve_cli_package_name() == DEFAULT_CLI_PACKAGE_NAME


def test_string_entry_point(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "specify_cli.distribution.package_name.entry_points",
        lambda group: [_FakeEntryPoint("main", "acme-spec-kitty-cli")],
    )
    assert resolve_cli_package_name() == "acme-spec-kitty-cli"


def test_callable_entry_point(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "specify_cli.distribution.package_name.entry_points",
        lambda group: [_FakeEntryPoint("main", lambda: "from-callable")],
    )
    assert resolve_cli_package_name() == "from-callable"


def test_object_with_package_name(monkeypatch: pytest.MonkeyPatch) -> None:
    class Holder:
        package_name = "holder-pkg"

    monkeypatch.setattr(
        "specify_cli.distribution.package_name.entry_points",
        lambda group: [_FakeEntryPoint("main", Holder())],
    )
    assert resolve_cli_package_name() == "holder-pkg"


def test_packages_distributions_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "specify_cli.distribution.package_name.entry_points",
        lambda group: [],
    )
    monkeypatch.setattr(
        "specify_cli.distribution.package_name.packages_distributions",
        lambda: {"specify_cli": ["fork-cli"]},
    )
    assert resolve_cli_package_name() == "fork-cli"


def test_entry_point_load_failure_falls_through(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "specify_cli.distribution.package_name.entry_points",
        lambda group: [_FakeEntryPoint("broken", RuntimeError("boom"))],
    )
    monkeypatch.setattr(
        "specify_cli.distribution.package_name.packages_distributions",
        lambda: {},
    )
    assert resolve_cli_package_name() == DEFAULT_CLI_PACKAGE_NAME


def test_memoizes_result(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def counting_entry_points(*, group: str) -> list[_FakeEntryPoint]:
        calls["n"] += 1
        return []

    monkeypatch.setattr(
        "specify_cli.distribution.package_name.entry_points",
        counting_entry_points,
    )
    monkeypatch.setattr(
        "specify_cli.distribution.package_name.packages_distributions",
        lambda: {},
    )
    assert resolve_cli_package_name() == DEFAULT_CLI_PACKAGE_NAME
    assert resolve_cli_package_name() == DEFAULT_CLI_PACKAGE_NAME
    assert calls["n"] == 1


def test_never_uses_env_for_package_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEC_KITTY_CLI_PACKAGE", "should-not-win")
    monkeypatch.setattr(
        "specify_cli.distribution.package_name.entry_points",
        lambda group: [],
    )
    monkeypatch.setattr(
        "specify_cli.distribution.package_name.packages_distributions",
        lambda: {},
    )
    assert resolve_cli_package_name() == DEFAULT_CLI_PACKAGE_NAME
