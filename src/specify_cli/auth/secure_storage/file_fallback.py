"""Encrypted file fallback backend for systems without an OS keychain.

Implements decision D-8 / constraint C-011:

- Key derivation uses scrypt (``cryptography.hazmat.primitives.kdf.scrypt``)
  with a random 16-byte salt persisted at
  ``~/.config/spec-kitty/credentials.salt`` (0600 perms).
- The scrypt passphrase is ``f"{socket.gethostname()}:{os.getuid()}"`` — this
  binds the derived key to the machine AND the invoking UID. This is
  deliberately stronger than the previous run's raw SHA256(hostname).
- Ciphertext is AES-256-GCM (12-byte nonce, fresh per write).
- File format version is 2. Version 1 plaintext files are rejected with a
  clear error telling the user to re-login.
- Writes are atomic via ``write+rename`` and coordinated with
  :class:`filelock.FileLock` so parallel CLI processes cannot corrupt the file.
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import socket
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from filelock import FileLock

from ..errors import SecureStorageError, StorageDecryptionError
from ..session import StoredSession
from .abstract import SecureStorage

log = logging.getLogger(__name__)

_DEFAULT_DIR = Path.home() / ".config" / "spec-kitty"
_CRED_NAME = "credentials.json"
_SALT_NAME = "credentials.salt"
_LOCK_NAME = "credentials.lock"

_FILE_FORMAT_VERSION = 2  # v1 was plaintext (rejected); v2 is AES-256-GCM

# scrypt cost parameters (production). Tests may subclass and lower these via
# ``_scrypt_n`` to keep suite runtime reasonable; the production default is
# intentionally conservative (~100ms on modern hardware).
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1


def _get_uid() -> int:
    """Return the current process UID (0 on Windows, which lacks ``os.getuid``)."""
    getuid = getattr(os, "getuid", None)
    if getuid is None:
        return 0
    return int(getuid())


class FileFallbackStorage(SecureStorage):
    """AES-256-GCM-encrypted file storage with scrypt key derivation.

    Accepts an optional ``base_dir`` so tests can redirect the credentials
    directory without monkeypatching ``Path.home``.
    """

    _scrypt_n: int = _SCRYPT_N
    _scrypt_r: int = _SCRYPT_R
    _scrypt_p: int = _SCRYPT_P

    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = Path(base_dir) if base_dir is not None else _DEFAULT_DIR
        self._cred_file = self._dir / _CRED_NAME
        self._salt_file = self._dir / _SALT_NAME
        self._lock_file = self._dir / _LOCK_NAME

    @property
    def backend_name(self) -> str:
        return "file"

    # ---- internal helpers ------------------------------------------------

    def _ensure_dir(self) -> None:
        self._dir.mkdir(mode=0o700, parents=True, exist_ok=True)

    def _load_or_create_salt(self) -> bytes:
        self._ensure_dir()
        if self._salt_file.exists():
            salt = self._salt_file.read_bytes()
            if len(salt) != 16:
                raise StorageDecryptionError(
                    f"Salt file {self._salt_file} has wrong length ({len(salt)} bytes); expected 16"
                )
            return salt
        salt = secrets.token_bytes(16)
        self._salt_file.write_bytes(salt)
        os.chmod(self._salt_file, 0o600)
        return salt

    def _derive_key(self, salt: bytes) -> bytes:
        passphrase = f"{socket.gethostname()}:{_get_uid()}".encode()
        kdf = Scrypt(
            salt=salt,
            length=32,  # AES-256 key
            n=self._scrypt_n,
            r=self._scrypt_r,
            p=self._scrypt_p,
        )
        return kdf.derive(passphrase)

    def _encrypt(self, plaintext: bytes) -> dict[str, Any]:
        salt = self._load_or_create_salt()
        key = self._derive_key(salt)
        nonce = secrets.token_bytes(12)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        return {
            "version": _FILE_FORMAT_VERSION,
            "nonce": nonce.hex(),
            "ciphertext": ciphertext.hex(),
        }

    def _decrypt(self, blob: dict[str, Any]) -> bytes:
        version = blob.get("version")
        if version != _FILE_FORMAT_VERSION:
            raise StorageDecryptionError(
                f"Unsupported credentials file format version {version!r}; "
                f"expected {_FILE_FORMAT_VERSION}. v1 plaintext files are rejected; "
                f"please re-run `spec-kitty auth login`."
            )
        if not self._salt_file.exists():
            raise StorageDecryptionError(
                f"Salt file {self._salt_file} is missing; cannot decrypt credentials. "
                f"Re-run `spec-kitty auth login`."
            )
        salt = self._salt_file.read_bytes()
        if len(salt) != 16:
            raise StorageDecryptionError(
                f"Salt file {self._salt_file} has wrong length ({len(salt)} bytes); expected 16"
            )
        key = self._derive_key(salt)
        try:
            nonce = bytes.fromhex(blob["nonce"])
            ciphertext = bytes.fromhex(blob["ciphertext"])
        except (KeyError, ValueError) as exc:
            raise StorageDecryptionError(
                f"Credentials file is malformed: {exc}"
            ) from exc
        aesgcm = AESGCM(key)
        try:
            return aesgcm.decrypt(nonce, ciphertext, None)
        except Exception as exc:  # noqa: BLE001 — cryptography raises InvalidTag / others
            raise StorageDecryptionError(
                f"Failed to decrypt credentials file: {exc}"
            ) from exc

    # ---- public API ------------------------------------------------------

    def read(self) -> StoredSession | None:
        if not self._cred_file.exists():
            return None
        self._ensure_dir()
        with FileLock(str(self._lock_file), timeout=10):
            raw = self._cred_file.read_text(encoding="utf-8")
        try:
            blob = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise StorageDecryptionError(
                f"Credentials file {self._cred_file} is not valid JSON: {exc}"
            ) from exc
        if not isinstance(blob, dict):
            raise StorageDecryptionError(
                f"Credentials file {self._cred_file} is not a JSON object"
            )
        plaintext = self._decrypt(blob)
        try:
            return StoredSession.from_json(plaintext.decode("utf-8"))
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            raise StorageDecryptionError(
                f"Decrypted credentials payload is not a valid session: {exc}"
            ) from exc

    def write(self, session: StoredSession) -> None:
        self._ensure_dir()
        plaintext = session.to_json().encode("utf-8")
        blob = self._encrypt(plaintext)
        with FileLock(str(self._lock_file), timeout=10):
            tmp = self._cred_file.with_suffix(self._cred_file.suffix + ".tmp")
            tmp.write_text(json.dumps(blob), encoding="utf-8")
            try:
                os.chmod(tmp, 0o600)
            except OSError as exc:
                # Best-effort on platforms without POSIX perms (Windows).
                log.debug("Could not chmod %s: %s", tmp, exc)
            tmp.replace(self._cred_file)

    def delete(self) -> None:
        self._ensure_dir()
        with FileLock(str(self._lock_file), timeout=10):
            if self._cred_file.exists():
                try:
                    self._cred_file.unlink()
                except OSError as exc:
                    raise SecureStorageError(
                        f"Failed to delete credentials file: {exc}"
                    ) from exc
            # Also rotate the salt so the next login creates a fresh one.
            if self._salt_file.exists():
                try:
                    self._salt_file.unlink()
                except OSError as exc:
                    log.debug("Could not delete salt file %s: %s", self._salt_file, exc)
