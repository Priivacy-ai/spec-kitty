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
        "jira",
        {
            "base_url": "https://jira.example.com",
            "email": "alice@example.com",
            "api_token": "secret",
        },
    )
    loaded = store.get_provider("jira")

    # Assert
    assert loaded["base_url"] == "https://jira.example.com"
    assert loaded["email"] == "alice@example.com"
    assert loaded["api_token"] == "secret"


def test_provider_credentials_clear(tmp_path) -> None:
    """clear_provider removes stored credentials so get_provider returns an empty dict."""
    # Arrange
    path = tmp_path / "credentials"
    store = TrackerCredentialStore(path)
    store.set_provider("linear", {"api_key": "token", "team_id": "team-1"})

    # Assumption check
    assert store.get_provider("linear"), "credentials must be present before clearing"

    # Act
    store.clear_provider("linear")

    # Assert
    assert store.get_provider("linear") == {}


def test_credentials_file_permissions_posix(tmp_path) -> None:
    """Credentials file is written with mode 0o600 on POSIX systems."""
    # Arrange
    path = tmp_path / "credentials"
    store = TrackerCredentialStore(path)

    # Assumption check
    # (no precondition)

    # Act
    store.set_provider("github", {"token": "abc", "owner": "org", "repo": "repo"})

    # Assert
    if os.name != "nt":
        mode = path.stat().st_mode & 0o777
        assert mode == 0o600
