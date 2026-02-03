"""Unit tests for CredentialStore."""

from __future__ import annotations

import os
from datetime import datetime, timedelta

import pytest
import toml

from specify_cli.sync.auth import CredentialStore


@pytest.fixture
def temp_credentials_dir(tmp_path):
    """Create a temporary credentials directory."""
    cred_dir = tmp_path / ".spec-kitty"
    cred_dir.mkdir()
    return cred_dir


@pytest.fixture
def credential_store(temp_credentials_dir):
    """Create CredentialStore pointing to temp directory."""
    store = CredentialStore()
    store.credentials_path = temp_credentials_dir / "credentials"
    store.lock_path = store.credentials_path.with_suffix(".lock")
    return store


class TestCredentialStoreSave:
    """Tests for CredentialStore.save()."""

    def test_save_creates_file(self, credential_store):
        """save() should create credentials file."""
        credential_store.save(
            access_token="test_access",
            refresh_token="test_refresh",
            access_expires_at=datetime.utcnow() + timedelta(minutes=15),
            refresh_expires_at=datetime.utcnow() + timedelta(days=7),
            username="test@example.com",
            server_url="https://test.example.com",
        )

        assert credential_store.credentials_path.exists()

    def test_save_writes_valid_toml(self, credential_store):
        """save() should write valid TOML format."""
        credential_store.save(
            access_token="test_access",
            refresh_token="test_refresh",
            access_expires_at=datetime.utcnow() + timedelta(minutes=15),
            refresh_expires_at=datetime.utcnow() + timedelta(days=7),
            username="test@example.com",
            server_url="https://test.example.com",
        )

        data = toml.load(credential_store.credentials_path)
        assert data["tokens"]["access"] == "test_access"
        assert data["tokens"]["refresh"] == "test_refresh"
        assert data["user"]["username"] == "test@example.com"
        assert data["server"]["url"] == "https://test.example.com"

    @pytest.mark.skipif(os.name == "nt", reason="Unix permissions only")
    def test_save_sets_permissions(self, credential_store):
        """save() should set file permissions to 600."""
        credential_store.save(
            access_token="test",
            refresh_token="test",
            access_expires_at=datetime.utcnow() + timedelta(minutes=15),
            refresh_expires_at=datetime.utcnow() + timedelta(days=7),
            username="test@example.com",
            server_url="https://test.example.com",
        )

        mode = credential_store.credentials_path.stat().st_mode & 0o777
        assert mode == 0o600


class TestCredentialStoreLoad:
    """Tests for CredentialStore.load()."""

    def test_load_returns_none_when_no_file(self, credential_store):
        """load() should return None when file doesn't exist."""
        assert credential_store.load() is None

    def test_load_returns_data(self, credential_store):
        """load() should return stored data."""
        credential_store.save(
            access_token="test_access",
            refresh_token="test_refresh",
            access_expires_at=datetime.utcnow() + timedelta(minutes=15),
            refresh_expires_at=datetime.utcnow() + timedelta(days=7),
            username="test@example.com",
            server_url="https://test.example.com",
        )

        data = credential_store.load()
        assert data is not None
        assert data["tokens"]["access"] == "test_access"

    def test_load_handles_corrupted_file(self, credential_store):
        """load() should return None for corrupted file."""
        credential_store.credentials_path.parent.mkdir(exist_ok=True)
        credential_store.credentials_path.write_text("invalid toml {{{")

        assert credential_store.load() is None


class TestCredentialStoreClear:
    """Tests for CredentialStore.clear()."""

    def test_clear_removes_file(self, credential_store):
        """clear() should delete credentials file."""
        credential_store.save(
            access_token="test",
            refresh_token="test",
            access_expires_at=datetime.utcnow() + timedelta(minutes=15),
            refresh_expires_at=datetime.utcnow() + timedelta(days=7),
            username="test@example.com",
            server_url="https://test.example.com",
        )

        credential_store.clear()
        assert not credential_store.credentials_path.exists()

    def test_clear_handles_missing_file(self, credential_store):
        """clear() should not error when file doesn't exist."""
        credential_store.clear()


class TestCredentialStoreTokenExpiry:
    """Tests for token expiry methods."""

    def test_get_access_token_returns_valid_token(self, credential_store):
        """get_access_token() should return token when not expired."""
        credential_store.save(
            access_token="valid_access",
            refresh_token="test",
            access_expires_at=datetime.utcnow() + timedelta(minutes=15),
            refresh_expires_at=datetime.utcnow() + timedelta(days=7),
            username="test@example.com",
            server_url="https://test.example.com",
        )

        assert credential_store.get_access_token() == "valid_access"

    def test_get_access_token_returns_none_when_expired(self, credential_store):
        """get_access_token() should return None when expired."""
        credential_store.save(
            access_token="expired_access",
            refresh_token="test",
            access_expires_at=datetime.utcnow() - timedelta(minutes=1),
            refresh_expires_at=datetime.utcnow() + timedelta(days=7),
            username="test@example.com",
            server_url="https://test.example.com",
        )

        assert credential_store.get_access_token() is None

    def test_is_access_token_valid(self, credential_store):
        """is_access_token_valid() should check expiry."""
        credential_store.save(
            access_token="test",
            refresh_token="test",
            access_expires_at=datetime.utcnow() + timedelta(minutes=15),
            refresh_expires_at=datetime.utcnow() + timedelta(days=7),
            username="test@example.com",
            server_url="https://test.example.com",
        )

        assert credential_store.is_access_token_valid() is True
