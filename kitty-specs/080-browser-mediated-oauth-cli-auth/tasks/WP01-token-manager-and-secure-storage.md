---
work_package_id: WP01
title: TokenManager + SecureStorage Foundation
dependencies: []
requirement_refs:
- FR-006
- FR-007
- FR-009
- FR-010
- FR-012
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
history: []
authoritative_surface: src/specify_cli/auth/
execution_mode: code_change
owned_files:
- pyproject.toml
- src/specify_cli/auth/__init__.py
- src/specify_cli/auth/config.py
- src/specify_cli/auth/errors.py
- src/specify_cli/auth/session.py
- src/specify_cli/auth/token_manager.py
- src/specify_cli/auth/secure_storage/**
- tests/auth/test_config.py
- tests/auth/test_session.py
- tests/auth/test_token_manager.py
- tests/auth/test_secure_storage_keychain.py
- tests/auth/test_secure_storage_file.py
status: pending
tags: []
---

# WP01: TokenManager + SecureStorage Foundation

**Objective**: Build the foundation of the new auth system: a process-wide
`TokenManager` accessed via `get_token_manager()` factory, a pluggable
`SecureStorage` abstraction with keychain (preferred) and encrypted file
fallback (last resort) backends, the `StoredSession` data model, and the
error hierarchy that the rest of the WPs use.

**Context**: This is the root WP. Every other WP imports from
`specify_cli.auth`. Everything depends on this getting the API right —
specifically the public surface of `get_token_manager()` and `TokenManager`,
because the post-merge review of the previous run found that an inconsistent
TokenManager API is what caused WP09 to ship stubs.

**Acceptance Criteria**:
- [ ] `from specify_cli.auth import get_token_manager` works from any module
- [ ] `get_token_manager()` returns the same TokenManager instance on repeated calls (process-wide)
- [ ] `get_saas_base_url()` reads `SPEC_KITTY_SAAS_URL` env var and raises `ConfigurationError` if unset (no fallback to a hardcoded domain)
- [ ] `StoredSession` and `Team` dataclasses match the schema in `data-model.md`
- [ ] `SecureStorage.from_environment()` returns a keychain backend on macOS/Windows/Linux when `keyring` finds a backend, otherwise returns the encrypted file backend
- [ ] File fallback uses scrypt KDF with random 16-byte salt stored at `~/.config/spec-kitty/credentials.salt` (0600 perms), key derived from `f"{hostname}:{uid}"`, encrypts with AES-256-GCM
- [ ] `TokenManager.get_access_token()` auto-refreshes when access token expires within 5 seconds
- [ ] `TokenManager.refresh_if_needed()` is single-flight: 10+ concurrent calls coordinate to a single network refresh
- [ ] All unit tests pass and cover the storage backends, session model, and refresh races

---

## Subtask Guidance

### T001 (preflight): Add keyring + cryptography to pyproject.toml

**Purpose**: Both libraries are imported by WP01 modules but neither is
declared in `pyproject.toml`. The mission's earlier plan was wrong on this
point. Add them as the very first action of WP01.

**Steps**:

1. Edit `pyproject.toml`. Find the `dependencies = [...]` array under
   `[project]`. Add the two new entries (alphabetical order):
   ```toml
   dependencies = [
       ...
       "cryptography>=42.0",   # NEW: AES-256-GCM + scrypt KDF for file fallback (per C-011)
       ...
       "keyring>=24.0",         # NEW: OS keystore abstraction for secure storage backends
       ...
   ]
   ```

2. Verify the imports work:
   ```bash
   pip install -e .
   python -c "import keyring; import cryptography; print('ok')"
   ```

3. The `pip install` may fail if a CI sandbox blocks network. In that case,
   document the blocker in the WP activity log and have the implementer
   re-run after the sandbox is opened. The dependency declaration itself is
   the deliverable; actual install happens in CI.

**Files**: `pyproject.toml` (add 2 lines)

**Validation**:
- [ ] `pyproject.toml` declares `cryptography>=42.0` and `keyring>=24.0`
- [ ] `python -c "import keyring; import cryptography"` succeeds (after install)

---

### T001: Create `auth/__init__.py` with `get_token_manager()` factory

**Purpose**: Provide the single shared TokenManager that every other WP depends on.

**Steps**:

1. Create `src/specify_cli/auth/__init__.py`. Module-level globals + lock:
   ```python
   from __future__ import annotations
   import threading
   from typing import Optional
   from .token_manager import TokenManager
   from .secure_storage import SecureStorage
   from .errors import (
       AuthenticationError,
       NotAuthenticatedError,
       TokenRefreshError,
       ConfigurationError,
       CallbackTimeoutError,
       CallbackValidationError,
       DeviceFlowDenied,
       DeviceFlowExpired,
   )

   __all__ = [
       "get_token_manager",
       "reset_token_manager",
       "TokenManager",
       "SecureStorage",
       "AuthenticationError",
       "NotAuthenticatedError",
       "TokenRefreshError",
       "ConfigurationError",
       "CallbackTimeoutError",
       "CallbackValidationError",
       "DeviceFlowDenied",
       "DeviceFlowExpired",
   ]

   _tm: Optional[TokenManager] = None
   _tm_lock = threading.Lock()


   def get_token_manager() -> TokenManager:
       """Return the process-wide TokenManager instance.

       Lazy-initializes from secure storage on first call. Subsequent calls
       return the same instance. Thread-safe.
       """
       global _tm
       if _tm is None:
           with _tm_lock:
               if _tm is None:
                   storage = SecureStorage.from_environment()
                   _tm = TokenManager(storage)
                   _tm.load_from_storage_sync()
       return _tm


   def reset_token_manager() -> None:
       """Reset the global TokenManager. For tests only."""
       global _tm
       with _tm_lock:
           _tm = None
   ```

2. The double-checked locking pattern is required because tests call
   `reset_token_manager()` between test cases and we need to avoid races.

3. `reset_token_manager()` is the test-only entry point. Tests use it via a
   pytest fixture (`autouse=True` on the auth test module) so each test gets
   a fresh TokenManager.

**Files**: `src/specify_cli/auth/__init__.py` (~80 lines)

**Validation**:
- [ ] `from specify_cli.auth import get_token_manager` works
- [ ] Calling `get_token_manager()` twice returns the same instance
- [ ] `reset_token_manager()` causes the next call to create a new instance

---

### T002: Create `auth/config.py` with `get_saas_base_url()` env helper

**Purpose**: Single source of truth for the SaaS base URL. No hardcoded
domains anywhere in the codebase (D-5).

**Steps**:

1. Create `src/specify_cli/auth/config.py`:
   ```python
   from __future__ import annotations
   import os
   from .errors import ConfigurationError

   _ENV_VAR = "SPEC_KITTY_SAAS_URL"


   def get_saas_base_url() -> str:
       """Return the SaaS base URL from the SPEC_KITTY_SAAS_URL environment variable.

       Raises ConfigurationError if the env var is not set. There is NO fallback
       to a hardcoded domain — fly.io deployments use generated hostnames and
       there is no stable production domain.
       """
       url = os.environ.get(_ENV_VAR)
       if not url:
           raise ConfigurationError(
               f"{_ENV_VAR} environment variable is not set. "
               f"Set it to your spec-kitty-saas instance URL (e.g. "
               f"https://api.spec-kitty.example.com) and try again."
           )
       return url.rstrip("/")
   ```

2. Tests use `monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://saas.test")`
   and verify the returned value, plus a test that `monkeypatch.delenv` causes
   `ConfigurationError`.

**Files**: `src/specify_cli/auth/config.py` (~30 lines), `tests/auth/test_config.py` (~50 lines)

**Validation**:
- [ ] Env var unset → `ConfigurationError`
- [ ] Env var set with trailing slash → returned without trailing slash
- [ ] Env var set without trailing slash → returned as-is

---

### T003: Create `auth/errors.py` with full exception hierarchy

**Purpose**: One module that defines every auth-related exception. All other
WPs import from here, never from flow-internal modules.

**Steps**:

1. Create `src/specify_cli/auth/errors.py`:
   ```python
   from __future__ import annotations


   class AuthenticationError(Exception):
       """Base class for all spec-kitty auth errors."""


   class NotAuthenticatedError(AuthenticationError):
       """Raised when an operation requires a session but none exists."""


   class ConfigurationError(AuthenticationError):
       """Raised when configuration (env vars, etc.) is missing or invalid."""


   class TokenRefreshError(AuthenticationError):
       """Base class for token refresh failures."""


   class RefreshTokenExpiredError(TokenRefreshError):
       """Raised when the refresh token itself has expired (re-login required)."""


   class SessionInvalidError(TokenRefreshError):
       """Raised when SaaS reports the session has been invalidated server-side."""


   class NetworkError(AuthenticationError):
       """Raised on network-level failures (timeouts, DNS, connection refused)."""


   # ----- Loopback / browser flow errors -----

   class CallbackError(AuthenticationError):
       """Base class for OAuth callback errors."""


   class CallbackTimeoutError(CallbackError):
       """Raised when the loopback callback server times out (5 minutes)."""


   class CallbackValidationError(CallbackError):
       """Raised when the callback fails CSRF state validation or is malformed."""


   class StateExpiredError(CallbackError):
       """Raised when the PKCEState used for the callback has expired."""


   class BrowserLaunchError(AuthenticationError):
       """Raised when no browser is available to launch."""


   # ----- Device flow errors -----

   class DeviceFlowError(AuthenticationError):
       """Base class for device authorization flow errors."""


   class DeviceFlowDenied(DeviceFlowError):
       """Raised when the user denies device authorization."""


   class DeviceFlowExpired(DeviceFlowError):
       """Raised when the device code expires before user approval."""


   # ----- Storage errors -----

   class SecureStorageError(AuthenticationError):
       """Base class for secure storage backend errors."""


   class StorageBackendUnavailableError(SecureStorageError):
       """Raised when no secure storage backend is available."""


   class StorageDecryptionError(SecureStorageError):
       """Raised when an encrypted file cannot be decrypted (corruption, wrong key)."""
   ```

2. The hierarchy is flat under `AuthenticationError` and the flow-specific
   subclasses are grouped by section. This module is imported by every other
   WP via `from specify_cli.auth.errors import ...`.

**Files**: `src/specify_cli/auth/errors.py` (~80 lines)

**Validation**:
- [ ] Every error class is exported from `auth/__init__.py` at least once
- [ ] All error classes inherit from `AuthenticationError`

---

### T004: Create `auth/session.py` with Team + StoredSession dataclasses

**Purpose**: The data model for an authenticated session. Every WP that
returns a session uses this exact shape.

**IMPORTANT**: The field is `email` (NOT `username`) — it is sourced from the
SaaS `GET /api/v1/me` response's `.email` field. The field
`refresh_token_expires_at` is `Optional[datetime]` and may be `None`; see
constraint C-012 in spec.md and `contracts/saas-amendment-refresh-ttl.md`
for the binding to the SaaS contract amendment.

**Steps**:

1. Create `src/specify_cli/auth/session.py`:
   ```python
   from __future__ import annotations
   from dataclasses import dataclass, field, asdict
   from datetime import datetime, timedelta, timezone
   from typing import Literal, Optional
   import json

   StorageBackend = Literal["keychain", "credential_manager", "secret_service", "file"]


   @dataclass(frozen=True)
   class Team:
       id: str
       name: str
       role: str  # "admin" | "member" | etc.

       def to_dict(self) -> dict:
           return asdict(self)

       @classmethod
       def from_dict(cls, data: dict) -> "Team":
           return cls(id=data["id"], name=data["name"], role=data["role"])


   @dataclass
   class StoredSession:
       user_id: str
       email: str                       # ← from /api/v1/me .email (NOT "username")
       name: str
       teams: list[Team]
       default_team_id: str             # ← CLIENT-PICKED, not server-supplied

       access_token: str
       refresh_token: str
       session_id: str

       issued_at: datetime
       access_token_expires_at: datetime
       refresh_token_expires_at: Optional[datetime]
       # ↑ None when SaaS does not provide refresh_token_expires_in.
       # The CLI never hardcodes a TTL. See C-012 in spec.md.

       scope: str
       storage_backend: StorageBackend
       last_used_at: datetime
       auth_method: Literal["authorization_code", "device_code"]

       def is_access_token_expired(self, buffer_seconds: int = 0) -> bool:
           now = datetime.now(timezone.utc)
           return self.access_token_expires_at <= now + timedelta(seconds=buffer_seconds)

       def is_refresh_token_expired(self) -> bool:
           """Return True ONLY if we have a known refresh expiry and it has passed.

           When refresh_token_expires_at is None (SaaS amendment not landed),
           this method returns False. The CLI then learns about expiry from a
           400 invalid_grant response on a refresh attempt. See C-012.
           """
           if self.refresh_token_expires_at is None:
               return False  # server-managed; client cannot decide
           return self.refresh_token_expires_at <= datetime.now(timezone.utc)

       def touch(self) -> None:
           """Update last_used_at to now."""
           self.last_used_at = datetime.now(timezone.utc)

       def to_dict(self) -> dict:
           return {
               "user_id": self.user_id,
               "email": self.email,
               "name": self.name,
               "teams": [t.to_dict() for t in self.teams],
               "default_team_id": self.default_team_id,
               "access_token": self.access_token,
               "refresh_token": self.refresh_token,
               "session_id": self.session_id,
               "issued_at": self.issued_at.isoformat(),
               "access_token_expires_at": self.access_token_expires_at.isoformat(),
               "refresh_token_expires_at": (
                   self.refresh_token_expires_at.isoformat()
                   if self.refresh_token_expires_at is not None
                   else None
               ),
               "scope": self.scope,
               "storage_backend": self.storage_backend,
               "last_used_at": self.last_used_at.isoformat(),
               "auth_method": self.auth_method,
           }

       @classmethod
       def from_dict(cls, data: dict) -> "StoredSession":
           refresh_exp_raw = data.get("refresh_token_expires_at")
           refresh_exp = (
               datetime.fromisoformat(refresh_exp_raw) if refresh_exp_raw else None
           )
           return cls(
               user_id=data["user_id"],
               email=data["email"],
               name=data["name"],
               teams=[Team.from_dict(t) for t in data["teams"]],
               default_team_id=data["default_team_id"],
               access_token=data["access_token"],
               refresh_token=data["refresh_token"],
               session_id=data["session_id"],
               issued_at=datetime.fromisoformat(data["issued_at"]),
               access_token_expires_at=datetime.fromisoformat(data["access_token_expires_at"]),
               refresh_token_expires_at=refresh_exp,
               scope=data["scope"],
               storage_backend=data["storage_backend"],
               last_used_at=datetime.fromisoformat(data["last_used_at"]),
               auth_method=data["auth_method"],
           )

       def to_json(self) -> str:
           return json.dumps(self.to_dict())

       @classmethod
       def from_json(cls, raw: str) -> "StoredSession":
           return cls.from_dict(json.loads(raw))
   ```

2. The `auth_method` field tracks whether the session came from browser PKCE
   or device flow — useful for `auth status` display and debugging.

3. `to_dict()` / `from_dict()` are used by the file fallback backend.
   `to_json()` is used by the keychain backend (which stores a single string).

4. **Critical**: tests must cover both branches of `is_refresh_token_expired`:
   - When `refresh_token_expires_at` is None → returns False unconditionally
   - When `refresh_token_expires_at` is set and in the past → returns True
   - When `refresh_token_expires_at` is set and in the future → returns False

**Files**: `src/specify_cli/auth/session.py` (~170 lines), `tests/auth/test_session.py` (~120 lines)

**Validation**:
- [ ] Round-trip: `StoredSession.from_dict(s.to_dict()) == s` (with and without `refresh_token_expires_at`)
- [ ] Round-trip: `StoredSession.from_json(s.to_json()) == s`
- [ ] `is_access_token_expired(buffer_seconds=10)` returns True when expiry is 5 seconds from now
- [ ] `is_refresh_token_expired()` returns False when `refresh_token_expires_at is None`
- [ ] No hardcoded "90 days" anywhere in this module

---

### T005: Create `auth/secure_storage/` package with abstract base + keychain backend

**Purpose**: Pluggable backend for storing the StoredSession. Keychain when
available; file fallback otherwise.

**Steps**:

1. Create `src/specify_cli/auth/secure_storage/__init__.py`:
   ```python
   from __future__ import annotations
   from .abstract import SecureStorage

   __all__ = ["SecureStorage"]
   ```

2. Create `src/specify_cli/auth/secure_storage/abstract.py`:
   ```python
   from __future__ import annotations
   from abc import ABC, abstractmethod
   from typing import Optional
   from ..session import StoredSession


   class SecureStorage(ABC):
       """Abstract storage backend for StoredSession."""

       @abstractmethod
       def read(self) -> Optional[StoredSession]: ...

       @abstractmethod
       def write(self, session: StoredSession) -> None: ...

       @abstractmethod
       def delete(self) -> None: ...

       @property
       @abstractmethod
       def backend_name(self) -> str:
           """Return the StorageBackend literal value."""

       @classmethod
       def from_environment(cls) -> "SecureStorage":
           """Return the best available backend on the current platform."""
           # Try keychain first
           try:
               from .keychain import KeychainStorage
               kc = KeychainStorage()
               if kc.is_available():
                   return kc
           except Exception:
               pass
           # Fall back to encrypted file
           from .file_fallback import FileFallbackStorage
           return FileFallbackStorage()
   ```

3. Create `src/specify_cli/auth/secure_storage/keychain.py`:
   ```python
   from __future__ import annotations
   import platform
   from typing import Optional
   import keyring
   import keyring.errors
   from ..session import StoredSession
   from ..errors import SecureStorageError
   from .abstract import SecureStorage

   _SERVICE = "spec-kitty-cli"
   _ACCOUNT = "session"


   class KeychainStorage(SecureStorage):
       """OS-keychain-backed storage via the `keyring` library."""

       def is_available(self) -> bool:
           backend = keyring.get_keyring()
           # The default fail backend has class name 'fail.Keyring'
           name = type(backend).__module__
           return "fail" not in name and "null" not in name

       def read(self) -> Optional[StoredSession]:
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
               pass  # Already absent
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
           return "keychain"  # default
   ```

4. Tests use a fake keyring backend (`keyring.set_keyring(...)`) to verify
   the read/write/delete cycle without touching the host keychain.

**Files**:
- `src/specify_cli/auth/secure_storage/__init__.py` (~10 lines)
- `src/specify_cli/auth/secure_storage/abstract.py` (~50 lines)
- `src/specify_cli/auth/secure_storage/keychain.py` (~80 lines)
- `tests/auth/test_secure_storage_keychain.py` (~120 lines)

**Validation**:
- [ ] `SecureStorage.from_environment()` returns KeychainStorage on a system with a real keychain
- [ ] Round-trip write/read/delete works with a fake keyring backend
- [ ] backend_name returns the correct platform-specific string

---

### T006: Implement file fallback with scrypt KDF + AES-256-GCM

**Purpose**: Encrypted-at-rest storage for systems without an OS keychain.
Uses scrypt with random salt (D-8) — NOT raw SHA256(hostname) like the
previous run.

**Steps**:

1. Create `src/specify_cli/auth/secure_storage/file_fallback.py`:
   ```python
   from __future__ import annotations
   import json
   import os
   import secrets
   import socket
   import stat
   from pathlib import Path
   from typing import Optional
   from cryptography.hazmat.primitives.ciphers.aead import AESGCM
   from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
   from filelock import FileLock
   from ..session import StoredSession
   from ..errors import SecureStorageError, StorageDecryptionError
   from .abstract import SecureStorage

   _DIR = Path.home() / ".config" / "spec-kitty"
   _CRED_FILE = _DIR / "credentials.json"
   _SALT_FILE = _DIR / "credentials.salt"
   _LOCK_FILE = _DIR / "credentials.lock"
   _FILE_FORMAT_VERSION = 2  # v1 was plaintext (rejected); v2 is AES-256-GCM


   class FileFallbackStorage(SecureStorage):
       """AES-256-GCM-encrypted file storage with scrypt key derivation."""

       def __init__(self) -> None:
           self._dir = _DIR
           self._cred_file = _CRED_FILE
           self._salt_file = _SALT_FILE
           self._lock_file = _LOCK_FILE

       @property
       def backend_name(self) -> str:
           return "file"

       def _ensure_dir(self) -> None:
           self._dir.mkdir(mode=0o700, parents=True, exist_ok=True)

       def _load_or_create_salt(self) -> bytes:
           self._ensure_dir()
           if self._salt_file.exists():
               salt = self._salt_file.read_bytes()
               if len(salt) != 16:
                   raise StorageDecryptionError(
                       f"Salt file {self._salt_file} has wrong length ({len(salt)} bytes)"
                   )
               return salt
           # Create new salt
           salt = secrets.token_bytes(16)
           self._salt_file.write_bytes(salt)
           os.chmod(self._salt_file, 0o600)
           return salt

       def _derive_key(self, salt: bytes) -> bytes:
           passphrase = f"{socket.gethostname()}:{os.getuid()}".encode("utf-8")
           kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
           return kdf.derive(passphrase)

       def _encrypt(self, plaintext: bytes) -> dict:
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

       def _decrypt(self, blob: dict) -> bytes:
           if blob.get("version") != _FILE_FORMAT_VERSION:
               raise StorageDecryptionError(
                   f"Unsupported file format version {blob.get('version')}; "
                   f"expected {_FILE_FORMAT_VERSION}. v1 plaintext files are rejected."
               )
           if not self._salt_file.exists():
               raise StorageDecryptionError(
                   f"Salt file {self._salt_file} is missing; cannot decrypt."
               )
           salt = self._salt_file.read_bytes()
           key = self._derive_key(salt)
           nonce = bytes.fromhex(blob["nonce"])
           ciphertext = bytes.fromhex(blob["ciphertext"])
           aesgcm = AESGCM(key)
           try:
               return aesgcm.decrypt(nonce, ciphertext, None)
           except Exception as exc:
               raise StorageDecryptionError(
                   f"Failed to decrypt credentials file: {exc}"
               ) from exc

       def read(self) -> Optional[StoredSession]:
           if not self._cred_file.exists():
               return None
           with FileLock(str(self._lock_file), timeout=10):
               raw = self._cred_file.read_text(encoding="utf-8")
           try:
               blob = json.loads(raw)
           except json.JSONDecodeError as exc:
               raise StorageDecryptionError(f"Credentials file is not valid JSON: {exc}") from exc
           plaintext = self._decrypt(blob)
           return StoredSession.from_json(plaintext.decode("utf-8"))

       def write(self, session: StoredSession) -> None:
           self._ensure_dir()
           plaintext = session.to_json().encode("utf-8")
           blob = self._encrypt(plaintext)
           with FileLock(str(self._lock_file), timeout=10):
               # Atomic write: write to temp, then rename
               tmp = self._cred_file.with_suffix(".json.tmp")
               tmp.write_text(json.dumps(blob), encoding="utf-8")
               os.chmod(tmp, 0o600)
               tmp.replace(self._cred_file)

       def delete(self) -> None:
           with FileLock(str(self._lock_file), timeout=10):
               if self._cred_file.exists():
                   self._cred_file.unlink()
               # Also delete the salt — fresh login will create a new one
               if self._salt_file.exists():
                   self._salt_file.unlink()
   ```

2. Tests verify:
   - Salt file is created on first write with 0600 perms
   - Reading without salt file → `StorageDecryptionError`
   - v1 plaintext format → rejected with clear error
   - Tampered ciphertext → AES-GCM authentication fails → `StorageDecryptionError`
   - Round-trip write/read/delete works
   - Concurrent writes coordinated by FileLock (no corruption)

**Files**: `src/specify_cli/auth/secure_storage/file_fallback.py` (~180 lines), `tests/auth/test_secure_storage_file.py` (~150 lines)

**Validation**:
- [ ] Salt file created on first write at 0600
- [ ] Credentials file at 0600
- [ ] Round-trip works
- [ ] v1 format → rejected
- [ ] Tampered ciphertext → rejected
- [ ] Wrong UID/hostname → cannot decrypt

---

### T007: Create `auth/token_manager.py` with single-flight refresh

**Purpose**: The central token gateway. Every WP that needs a bearer token
calls `await get_token_manager().get_access_token()`.

**Steps**:

1. Create `src/specify_cli/auth/token_manager.py`:
   ```python
   from __future__ import annotations
   import asyncio
   import logging
   from datetime import datetime, timedelta, timezone
   from typing import Optional
   from .session import StoredSession
   from .secure_storage import SecureStorage
   from .errors import (
       NotAuthenticatedError,
       TokenRefreshError,
       RefreshTokenExpiredError,
       SessionInvalidError,
   )

   log = logging.getLogger(__name__)

   _REFRESH_BUFFER_SECONDS = 5  # Refresh if expires within this window


   class TokenManager:
       """Centralized token provisioning with single-flight refresh."""

       def __init__(self, storage: SecureStorage) -> None:
           self._storage = storage
           self._session: Optional[StoredSession] = None
           self._refresh_lock: Optional[asyncio.Lock] = None

       def _get_lock(self) -> asyncio.Lock:
           # Lazy-create the lock so we don't bind it to the wrong event loop
           if self._refresh_lock is None:
               self._refresh_lock = asyncio.Lock()
           return self._refresh_lock

       def load_from_storage_sync(self) -> None:
           """Synchronous load (called once at process startup from get_token_manager)."""
           try:
               self._session = self._storage.read()
           except Exception as exc:
               log.warning("Could not load session from storage: %s", exc)
               self._session = None

       def set_session(self, session: StoredSession) -> None:
           """Persist a new session (called by AuthorizationCodeFlow / DeviceCodeFlow on success)."""
           self._session = session
           self._storage.write(session)

       def clear_session(self) -> None:
           """Delete the current session (called by logout)."""
           self._session = None
           try:
               self._storage.delete()
           except Exception as exc:
               log.warning("Could not delete session from storage: %s", exc)

       def get_current_session(self) -> Optional[StoredSession]:
           """Sync access to the current session for status display."""
           return self._session

       @property
       def is_authenticated(self) -> bool:
           """Return True if we have a session and (when known) the refresh token is still valid.

           When refresh_token_expires_at is None (SaaS amendment not landed),
           we cannot proactively decide the session is invalid. The caller will
           learn about expiry from a 400 invalid_grant on the next refresh attempt.
           """
           if self._session is None:
               return False
           if self._session.is_refresh_token_expired():
               return False
           return True

       async def get_access_token(self) -> str:
           """Return a valid access token, refreshing if necessary."""
           if self._session is None:
               raise NotAuthenticatedError(
                   "No active session. Run `spec-kitty auth login` to authenticate."
               )
           if self._session.is_access_token_expired(buffer_seconds=_REFRESH_BUFFER_SECONDS):
               await self.refresh_if_needed()
           return self._session.access_token

       async def refresh_if_needed(self) -> bool:
           """Refresh the access token if it's near expiry. Single-flight."""
           lock = self._get_lock()
           async with lock:
               # Double-check inside the lock — another task may have refreshed
               if self._session is None:
                   raise NotAuthenticatedError("No session to refresh")
               if not self._session.is_access_token_expired(buffer_seconds=_REFRESH_BUFFER_SECONDS):
                   return False  # Already refreshed by another caller
               if self._session.is_refresh_token_expired():
                   raise RefreshTokenExpiredError(
                       "Refresh token expired. Run `spec-kitty auth login` to log in again."
                   )

               # Lazy-import to avoid circular imports (auth/flows depends on auth)
               from .flows.refresh import TokenRefreshFlow
               flow = TokenRefreshFlow()
               try:
                   updated = await flow.refresh(self._session)
               except SessionInvalidError:
                   self.clear_session()
                   raise
               self._session = updated
               self._storage.write(updated)
               return True
   ```

2. Critical: the `_refresh_lock` is created lazily inside the running event
   loop. If we created it in `__init__`, it would be bound to whatever loop
   was active at module import time, which may not be the loop the CLI uses.

3. Critical: the double-check inside the lock prevents thundering herd. The
   first caller through the lock refreshes; subsequent callers see the
   already-refreshed token and return early.

4. The `NotAuthenticatedError` is raised when `_session is None`. The
   `RefreshTokenExpiredError` is raised when refresh token is expired (the
   user must log in again — there is nothing the auto-refresh can do).
   `SessionInvalidError` is raised by the refresh flow itself when SaaS
   reports `session_invalid` — TokenManager catches it, clears the session,
   and re-raises so the caller can prompt re-login.

**Files**: `src/specify_cli/auth/token_manager.py` (~150 lines), `tests/auth/test_token_manager.py` (~250 lines)

**Validation**:
- [ ] `get_access_token()` returns the stored token when not expired
- [ ] `get_access_token()` triggers refresh when expired
- [ ] 10 concurrent `get_access_token()` calls with an expired token result in exactly 1 `refresh()` call (use a counter inside a mocked TokenRefreshFlow)
- [ ] `refresh_if_needed()` raises `RefreshTokenExpiredError` when refresh token is expired
- [ ] `set_session()` writes to storage
- [ ] `clear_session()` deletes from storage and clears in-memory session
- [ ] `is_authenticated` reflects current state correctly

---

### T008: Write unit tests for WP01 components

**Purpose**: Comprehensive coverage of the foundation. Run `pytest tests/auth/`
with all of WP01's test files.

**Steps**:

1. `tests/auth/test_config.py` covers `get_saas_base_url()` env handling
2. `tests/auth/test_session.py` covers serialization round-trips and expiry checks
3. `tests/auth/test_secure_storage_keychain.py` covers keychain backend with a fake keyring
4. `tests/auth/test_secure_storage_file.py` covers file fallback (encryption, salt, perms, concurrency)
5. `tests/auth/test_token_manager.py` covers TokenManager with mocked storage and mocked refresh flow

6. Add a `conftest.py` fixture in `tests/auth/` that calls `reset_token_manager()`
   between tests to avoid state leakage:
   ```python
   import pytest
   from specify_cli.auth import reset_token_manager

   @pytest.fixture(autouse=True)
   def _reset_tm():
       reset_token_manager()
       yield
       reset_token_manager()
   ```

7. Run `pytest tests/auth/test_config.py tests/auth/test_session.py tests/auth/test_secure_storage_*.py tests/auth/test_token_manager.py -v` and verify all pass.

**Files**: `tests/auth/conftest.py` (~30 lines), test files mentioned above

**Validation**:
- [ ] All tests pass
- [ ] No state leakage between tests (reset fixture works)
- [ ] Coverage ≥ 90% for `auth/__init__.py`, `auth/config.py`, `auth/errors.py`, `auth/session.py`, `auth/token_manager.py`, `auth/secure_storage/**`

---

## Definition of Done

- [ ] All 8 subtasks completed
- [ ] All unit tests pass
- [ ] `from specify_cli.auth import get_token_manager` works
- [ ] `get_token_manager()` returns a usable TokenManager
- [ ] No hardcoded SaaS URLs anywhere — only `get_saas_base_url()`
- [ ] File fallback uses scrypt + random salt (D-8 honored)
- [ ] Single-flight refresh verified by concurrency test
- [ ] No TODO/FIXME comments in shipped code
- [ ] No tokens or secrets logged at any level

## Reviewer Guidance

- Verify `get_token_manager()` is a real factory, not a singleton class attribute
- Verify the file fallback uses scrypt with random salt (NOT SHA256(hostname) like the previous run)
- Verify the single-flight test actually exercises 10+ concurrent tasks and asserts the refresh count == 1
- Verify `auth/__init__.py` exports `get_token_manager`, `reset_token_manager`, `TokenManager`, and all error classes
- Verify there's no `class TokenManagerSingleton` or similar — the lifecycle is via factory function
- Verify no test imports a hardcoded `https://api.spec-kitty.com` — all tests use `monkeypatch.setenv("SPEC_KITTY_SAAS_URL", ...)`

## Risks & Edge Cases

- **Risk**: scrypt is too slow on cold start → tests may be slow. **Mitigation**: tests can mock the file backend or use small `n` parameter for test speed (but production uses `n=2**14`).
- **Risk**: `keyring` library on Linux without Secret Service may use a stub backend that silently no-ops. **Mitigation**: `KeychainStorage.is_available()` checks the backend module name to detect the stub case.
- **Risk**: Two CLI processes refreshing simultaneously → race in refresh flow. **Mitigation**: WP08 will add file-lock-based cross-process coordination on top of the in-process asyncio lock.
- **Edge case**: TokenManager created before any event loop exists. **Mitigation**: `_refresh_lock` is created lazily inside `_get_lock()`, only when `refresh_if_needed()` is called.
- **Edge case**: User has stale v1 plaintext credentials.json from a prior version. **Mitigation**: `_decrypt()` rejects `version != 2` with a clear error message telling them to re-login.
