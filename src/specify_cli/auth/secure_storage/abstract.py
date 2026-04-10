"""Abstract base class for secure storage backends.

Concrete subclasses live alongside this module:

- :mod:`.keychain` — :class:`KeychainStorage` using the ``keyring`` library
  (macOS Keychain, Windows Credential Manager, Linux Secret Service).
- :mod:`.file_fallback` — :class:`FileFallbackStorage` using AES-256-GCM
  with a scrypt-derived key and random salt (per decision D-8 / C-011).

``SecureStorage.from_environment()`` picks the best backend for the current
platform, preferring the keychain and falling back to the encrypted file.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from ..session import StoredSession

log = logging.getLogger(__name__)


class SecureStorage(ABC):
    """Abstract storage backend for :class:`StoredSession`.

    Concrete backends must implement read/write/delete plus the
    ``backend_name`` property (used for diagnostic display and to populate
    ``StoredSession.storage_backend``).
    """

    @abstractmethod
    def read(self) -> StoredSession | None:
        """Return the persisted session, or ``None`` if no session exists."""

    @abstractmethod
    def write(self, session: StoredSession) -> None:
        """Persist ``session`` to the backend, overwriting any previous value."""

    @abstractmethod
    def delete(self) -> None:
        """Delete the persisted session if present. Must be idempotent."""

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Return the backend identifier (matches ``StoredSession.storage_backend``)."""

    @classmethod
    def from_environment(cls) -> SecureStorage:
        """Return the best available backend for the current platform.

        Preference order:

        1. OS keychain via ``keyring`` (macOS / Windows / Linux Secret Service).
        2. Encrypted file fallback (AES-256-GCM with scrypt KDF).

        The file fallback is always available as the last resort.
        """
        # Try keychain first. Any exception during import or availability
        # probing falls through to the encrypted file backend.
        try:
            from .keychain import KeychainStorage

            kc = KeychainStorage()
            if kc.is_available():
                return kc
        except Exception as exc:  # noqa: BLE001 — we intentionally downgrade every failure
            log.debug("Keychain backend unavailable, falling back to file: %s", exc)

        from .file_fallback import FileFallbackStorage

        return FileFallbackStorage()
