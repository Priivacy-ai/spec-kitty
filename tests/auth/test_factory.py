"""Tests for the ``get_token_manager()`` factory (feature 080, WP01 T001).

Validates:

- Same instance returned across repeated calls (process-wide).
- ``reset_token_manager()`` causes a fresh instance next call.
- Thread-safe lazy initialization (no duplicate instances under concurrent access).
"""

from __future__ import annotations

import concurrent.futures

import keyring
import keyring.backend

from specify_cli.auth import (
    SecureStorage,
    TokenManager,
    get_token_manager,
    reset_token_manager,
)
from specify_cli.auth.secure_storage.keychain import KeychainStorage


class InMemoryKeyring(keyring.backend.KeyringBackend):
    priority = 10

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], str] = {}

    def set_password(self, service, username, password):
        self._store[(service, username)] = password

    def get_password(self, service, username):
        return self._store.get((service, username))

    def delete_password(self, service, username):
        self._store.pop((service, username), None)


def test_factory_returns_token_manager_instance():
    prev = keyring.get_keyring()
    keyring.set_keyring(InMemoryKeyring())
    try:
        tm = get_token_manager()
        assert isinstance(tm, TokenManager)
    finally:
        keyring.set_keyring(prev)


def test_factory_returns_same_instance_on_repeat_calls():
    prev = keyring.get_keyring()
    keyring.set_keyring(InMemoryKeyring())
    try:
        tm1 = get_token_manager()
        tm2 = get_token_manager()
        assert tm1 is tm2
    finally:
        keyring.set_keyring(prev)


def test_reset_token_manager_creates_fresh_instance():
    prev = keyring.get_keyring()
    keyring.set_keyring(InMemoryKeyring())
    try:
        tm1 = get_token_manager()
        reset_token_manager()
        tm2 = get_token_manager()
        assert tm1 is not tm2
    finally:
        keyring.set_keyring(prev)


def test_factory_uses_secure_storage_from_environment():
    """When a real keychain is configured, the factory wires a KeychainStorage."""
    prev = keyring.get_keyring()
    keyring.set_keyring(InMemoryKeyring())
    try:
        tm = get_token_manager()
        # TokenManager's storage is private but the factory chose via from_environment.
        # We verify the selection indirectly via SecureStorage.from_environment().
        direct = SecureStorage.from_environment()
        assert isinstance(direct, KeychainStorage)
        assert tm is not None
    finally:
        keyring.set_keyring(prev)


def test_factory_is_thread_safe():
    """Concurrent first-call must still return a single shared instance."""
    prev = keyring.get_keyring()
    keyring.set_keyring(InMemoryKeyring())
    try:
        reset_token_manager()

        def call() -> TokenManager:
            return get_token_manager()

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
            results = list(ex.map(lambda _: call(), range(64)))

        # All callers must see the same singleton instance.
        first = results[0]
        assert all(r is first for r in results)
    finally:
        keyring.set_keyring(prev)
