"""Tests for ``specify_cli.auth.secure_storage.keychain`` (feature 080, WP01 T005).

Uses a fake ``keyring.backend.KeyringBackend`` so no host keychain is touched.
"""

from __future__ import annotations

from datetime import datetime, timedelta, UTC

import keyring
import keyring.backend
import keyring.errors
import pytest

from specify_cli.auth.errors import SecureStorageError
from specify_cli.auth.secure_storage.keychain import KeychainStorage
from specify_cli.auth.session import StoredSession, Team


class InMemoryKeyring(keyring.backend.KeyringBackend):
    """Fake keyring backend that stores passwords in a dict."""

    priority = 10  # non-zero means "available"

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], str] = {}

    def set_password(self, service, username, password):
        self._store[(service, username)] = password

    def get_password(self, service, username):
        return self._store.get((service, username))

    def delete_password(self, service, username):
        if (service, username) not in self._store:
            raise keyring.errors.PasswordDeleteError("not set")
        del self._store[(service, username)]


class FailingKeyring(keyring.backend.KeyringBackend):
    """Fake backend where every operation raises ``KeyringError``."""

    priority = 10

    def set_password(self, service, username, password):
        raise keyring.errors.KeyringError("simulated set failure")

    def get_password(self, service, username):
        raise keyring.errors.KeyringError("simulated get failure")

    def delete_password(self, service, username):
        raise keyring.errors.KeyringError("simulated delete failure")


class StubFailBackend(keyring.backend.KeyringBackend):
    """Stub backend whose module name contains 'fail' to simulate unavailable state."""

    priority = 1

    def set_password(self, service, username, password):  # pragma: no cover
        raise NotImplementedError

    def get_password(self, service, username):  # pragma: no cover
        return None

    def delete_password(self, service, username):  # pragma: no cover
        raise NotImplementedError


# Force the fail module name so ``is_available`` detects it as a stub.
StubFailBackend.__module__ = "keyring.backends.fail"


def _now() -> datetime:
    return datetime.now(UTC)


def _make_session() -> StoredSession:
    now = _now()
    return StoredSession(
        user_id="user-1",
        email="a@b.com",
        name="A B",
        teams=[Team(id="t1", name="T1", role="owner")],
        default_team_id="t1",
        access_token="access",
        refresh_token="refresh",
        session_id="sess",
        issued_at=now,
        access_token_expires_at=now + timedelta(hours=1),
        refresh_token_expires_at=None,
        scope="openid",
        storage_backend="keychain",
        last_used_at=now,
        auth_method="authorization_code",
    )


@pytest.fixture
def in_memory_keyring():
    prev = keyring.get_keyring()
    backend = InMemoryKeyring()
    keyring.set_keyring(backend)
    try:
        yield backend
    finally:
        keyring.set_keyring(prev)


def test_is_available_with_real_backend(in_memory_keyring):
    assert KeychainStorage().is_available() is True


def test_is_available_false_with_fail_backend():
    prev = keyring.get_keyring()
    keyring.set_keyring(StubFailBackend())
    try:
        assert KeychainStorage().is_available() is False
    finally:
        keyring.set_keyring(prev)


def test_read_returns_none_when_empty(in_memory_keyring):
    storage = KeychainStorage()
    assert storage.read() is None


def test_roundtrip_write_read_delete(in_memory_keyring):
    storage = KeychainStorage()
    s = _make_session()
    storage.write(s)
    loaded = storage.read()
    assert loaded == s
    storage.delete()
    assert storage.read() is None


def test_delete_is_idempotent(in_memory_keyring):
    storage = KeychainStorage()
    # Should not raise even when nothing is stored.
    storage.delete()
    storage.delete()


def test_read_wraps_keyring_errors():
    prev = keyring.get_keyring()
    keyring.set_keyring(FailingKeyring())
    try:
        storage = KeychainStorage()
        with pytest.raises(SecureStorageError):
            storage.read()
    finally:
        keyring.set_keyring(prev)


def test_write_wraps_keyring_errors():
    prev = keyring.get_keyring()
    keyring.set_keyring(FailingKeyring())
    try:
        storage = KeychainStorage()
        with pytest.raises(SecureStorageError):
            storage.write(_make_session())
    finally:
        keyring.set_keyring(prev)


def test_backend_name_matches_platform():
    import platform

    storage = KeychainStorage()
    name = storage.backend_name
    system = platform.system()
    if system == "Darwin":
        assert name == "keychain"
    elif system == "Windows":
        assert name == "credential_manager"
    elif system == "Linux":
        assert name == "secret_service"
    else:
        assert name == "keychain"


def test_from_environment_picks_keychain_when_available(in_memory_keyring):
    from specify_cli.auth.secure_storage import SecureStorage

    storage = SecureStorage.from_environment()
    assert isinstance(storage, KeychainStorage)


def test_from_environment_falls_back_when_keychain_fails():
    from specify_cli.auth.secure_storage import SecureStorage
    from specify_cli.auth.secure_storage.file_fallback import FileFallbackStorage

    prev = keyring.get_keyring()
    keyring.set_keyring(StubFailBackend())
    try:
        storage = SecureStorage.from_environment()
        assert isinstance(storage, FileFallbackStorage)
    finally:
        keyring.set_keyring(prev)
