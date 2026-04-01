"""Scope: mock-boundary tests for tracker credential storage — no real git."""

from __future__ import annotations

import os

import pytest

from specify_cli.tracker.credentials import TrackerCredentialStore

pytestmark = pytest.mark.fast


def test_provider_credentials_round_trip(tmp_path) -> None:
    """Credentials written with set_provider are readable back with correct values."""
    # Arrange
    path = tmp_path / "credentials"
    store = TrackerCredentialStore(path)

    # Assumption check
    assert not path.exists(), "credentials file must not exist yet"

    # Act
    store.set_provider(
        "beads",
        {
            "command": "beads",
            "workspace": "spec-kitty-demo",
        },
    )
    loaded = store.get_provider("beads")

    # Assert
    assert loaded["command"] == "beads"
    assert loaded["workspace"] == "spec-kitty-demo"


def test_provider_credentials_clear(tmp_path) -> None:
    """clear_provider removes stored credentials so get_provider returns an empty dict."""
    # Arrange
    path = tmp_path / "credentials"
    store = TrackerCredentialStore(path)
    store.set_provider("fp", {"command": "fp", "workspace": "feature-1"})

    # Assumption check
    assert store.get_provider("fp"), "credentials must be present before clearing"

    # Act
    store.clear_provider("fp")

    # Assert
    assert store.get_provider("fp") == {}


def test_credentials_file_permissions_posix(tmp_path) -> None:
    """Credentials file is written with mode 0o600 on POSIX systems."""
    # Arrange
    path = tmp_path / "credentials"
    store = TrackerCredentialStore(path)

    # Assumption check
    # (no precondition)

    # Act
    store.set_provider("beads", {"command": "beads", "workspace": "spec-kitty-demo"})

    # Assert
    if os.name != "nt":
        mode = path.stat().st_mode & 0o777
        assert mode == 0o600
