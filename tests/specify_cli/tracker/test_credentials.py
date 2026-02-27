"""Tests for tracker credential storage."""

from __future__ import annotations

import os

from specify_cli.tracker.credentials import TrackerCredentialStore


def test_provider_credentials_round_trip(tmp_path) -> None:
    path = tmp_path / "credentials"
    store = TrackerCredentialStore(path)

    store.set_provider(
        "jira",
        {
            "base_url": "https://jira.example.com",
            "email": "alice@example.com",
            "api_token": "secret",
        },
    )

    loaded = store.get_provider("jira")
    assert loaded["base_url"] == "https://jira.example.com"
    assert loaded["email"] == "alice@example.com"
    assert loaded["api_token"] == "secret"


def test_provider_credentials_clear(tmp_path) -> None:
    path = tmp_path / "credentials"
    store = TrackerCredentialStore(path)

    store.set_provider("linear", {"api_key": "token", "team_id": "team-1"})
    assert store.get_provider("linear")

    store.clear_provider("linear")
    assert store.get_provider("linear") == {}


def test_credentials_file_permissions_posix(tmp_path) -> None:
    path = tmp_path / "credentials"
    store = TrackerCredentialStore(path)
    store.set_provider("github", {"token": "abc", "owner": "org", "repo": "repo"})

    if os.name != "nt":
        mode = path.stat().st_mode & 0o777
        assert mode == 0o600
