"""OS keychain backend via the ``keyring`` library.

Stores the session as a single JSON string under the
``spec-kitty-cli`` service / ``session`` account in the host keychain.
On macOS this is the Keychain; on Windows, the Credential Manager;
on Linux, the Secret Service (GNOME Keyring / KWallet).
"""

from __future__ import annotations

import platform

import keyring
import keyring.errors

from ..errors import SecureStorageError
from ..session import StoredSession
from .abstract import SecureStorage

_SERVICE = "spec-kitty-cli"
_ACCOUNT = "session"


class KeychainStorage(SecureStorage):
    """OS-keychain-backed :class:`SecureStorage` using the ``keyring`` library."""

    def is_available(self) -> bool:
        """Return True if a real (non-stub) keyring backend is configured.

        ``keyring`` falls back to stub backends named ``fail`` / ``null`` when
        no real backend is available (e.g. headless Linux without Secret
        Service). Those stubs silently no-op, which we must treat as
        "unavailable" so the caller can pick the encrypted file backend.
        """
        try:
            backend = keyring.get_keyring()
        except Exception:  # noqa: BLE001 — defensive: treat any import issue as unavailable
            return False
        name = type(backend).__module__
        return "fail" not in name and "null" not in name

    def read(self) -> StoredSession | None:
        try:
            raw = keyring.get_password(_SERVICE, _ACCOUNT)
        except keyring.errors.KeyringError as exc:
            raise SecureStorageError(f"Keychain read failed: {exc}") from exc
        if raw is None:
            return None
        return StoredSession.from_json(raw)

    def write(self, session: StoredSession) -> None:
        try:
            keyring.set_password(_SERVICE, _ACCOUNT, session.to_json())
        except keyring.errors.KeyringError as exc:
            raise SecureStorageError(f"Keychain write failed: {exc}") from exc

    def delete(self) -> None:
        try:
            keyring.delete_password(_SERVICE, _ACCOUNT)
        except keyring.errors.PasswordDeleteError:
            # Already absent — idempotent semantics per the base class contract.
            return
        except keyring.errors.KeyringError as exc:
            raise SecureStorageError(f"Keychain delete failed: {exc}") from exc

    @property
    def backend_name(self) -> str:
        system = platform.system()
        if system == "Darwin":
            return "keychain"
        if system == "Windows":
            return "credential_manager"
        if system == "Linux":
            return "secret_service"
        return "keychain"  # sensible default for unknown platforms
