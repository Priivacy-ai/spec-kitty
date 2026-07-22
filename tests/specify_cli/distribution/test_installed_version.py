"""Direct unit tests for resolve_installed_distribution_version (#2859 review fold).

renata: the resolver's alias fall-through, empty-name skip, exception branch, and
default return were only exercised indirectly (monkeypatched away in the planner
tests). These pin the real behaviour.
"""

from __future__ import annotations

import importlib.metadata

import pytest

from specify_cli.distribution.installed_version import (
    resolve_installed_distribution_version,
)


def test_primary_name_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "specify_cli.distribution.installed_version.version",
        lambda name: "1.2.3" if name == "acme-kitty-cli" else _raise_not_found(name),
    )
    assert resolve_installed_distribution_version("acme-kitty-cli") == "1.2.3"


def test_alias_fall_through(monkeypatch: pytest.MonkeyPatch) -> None:
    def _version(name: str) -> str:
        if name == "acme-alias":
            return "9.9.9"
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr("specify_cli.distribution.installed_version.version", _version)
    assert (
        resolve_installed_distribution_version("acme-kitty-cli", ("acme-alias",)) == "9.9.9"
    )


def test_empty_names_are_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def _version(name: str) -> str:
        seen.append(name)
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr("specify_cli.distribution.installed_version.version", _version)
    resolve_installed_distribution_version("", ("", "real"))
    assert seen == ["real"]  # blank candidates never reach version()


def test_all_miss_returns_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "specify_cli.distribution.installed_version.version",
        lambda name: _raise_not_found(name),
    )
    assert resolve_installed_distribution_version("nope", default="fallback") == "fallback"


def test_unexpected_error_degrades_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(name: str) -> str:
        raise RuntimeError("corrupt metadata")

    monkeypatch.setattr("specify_cli.distribution.installed_version.version", _boom)
    assert resolve_installed_distribution_version("x", default="unknown") == "unknown"


def _raise_not_found(name: str) -> str:
    raise importlib.metadata.PackageNotFoundError(name)
