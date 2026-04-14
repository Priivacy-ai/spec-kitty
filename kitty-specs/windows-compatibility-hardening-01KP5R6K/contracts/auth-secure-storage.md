# Contract: Auth Secure Storage (hard platform split)

**Spec IDs**: FR-001, FR-002, C-001
**Module**: `src/specify_cli/auth/secure_storage/`

## Public API

### `SecureStorage.from_environment() -> SecureStorage`

```python
def from_environment() -> "SecureStorage":
    """Return the platform-appropriate secure storage backend.

    Dispatch is by sys.platform. This is a HARD split: on Windows the
    keychain module is never imported and `keyring` is not on the Windows
    dependency surface.
    """
```

**Behavior**:

| Platform | Returned backend | Store location | `keyring` imported? |
|---|---|---|---|
| `sys.platform == "win32"` | `WindowsFileStorage` | `get_runtime_root().auth_dir` | **No** |
| `sys.platform == "darwin"` | `KeychainStorage` (existing) | macOS Keychain | Yes |
| `sys.platform == "linux"` | `KeychainStorage` or `LinuxFileStorage` (existing fallback) | Secret Service or `~/.config/spec-kitty/` (existing) | Yes (best-effort) |

**Guarantees**:
- G-01: On Windows, `SecureStorage.from_environment()` returns a `WindowsFileStorage` instance in O(1) without ever evaluating `import keyring` or `from . import keychain`.
- G-02: On Windows, after `from_environment()` runs in a fresh interpreter, `"specify_cli.auth.secure_storage.keychain"` is NOT in `sys.modules`.
- G-03: On non-Windows, behavior is unchanged from pre-mission.

### `WindowsFileStorage` (new)

Thin wrapper around the existing `EncryptedFileStorage` from `file_fallback.py`, parameterized to use `get_runtime_root().auth_dir` instead of the old `~/.config/spec-kitty`.

| Method | Contract |
|---|---|
| `__init__(store_path: Path \| None = None)` | Defaults to `get_runtime_root().auth_dir`. Creates the directory (and parents) if missing. |
| `store(key: str, value: bytes) -> None` | Encrypted write. Atomic via temp-file-then-rename. |
| `load(key: str) -> bytes \| None` | Returns `None` on missing. |
| `delete(key: str) -> None` | Idempotent: no-op if missing. |
| `list_keys() -> list[str]` | Returns stored key ids. |

### `EncryptedFileStorage._DEFAULT_DIR` (renamed to `default_store_dir()`)

Old: `_DEFAULT_DIR = Path.home() / ".config" / "spec-kitty"` (module-level constant)
New: `default_store_dir()` function that:
- On Windows, returns `get_runtime_root().auth_dir`.
- On POSIX, returns `Path.home() / ".config" / "spec-kitty"` (unchanged behavior).

**Rationale**: Module-level Path.home() evaluation happens at import time and cannot respond to platform. A function evaluates per-call and respects the platform split.

## Packaging contract

`pyproject.toml` dependency change:

```diff
 dependencies = [
     # ... existing ...
-    "keyring>=25",
+    "keyring>=25; sys_platform != \"win32\"",
     # ... existing ...
 ]
```

**Guarantees**:
- P-01: `pip install spec-kitty-cli` on `windows-latest` completes without pulling `keyring` or its transitive deps (`pywin32-ctypes`, etc.).
- P-02: `pip install spec-kitty-cli` on macOS/Linux still installs `keyring`.

## Test contract

| Test ID | File | windows_ci? | Asserts |
|---|---|---|---|
| T-AUTH-01 | `tests/auth/secure_storage/test_from_environment_platform_split.py` | No (platform-mocked) | G-01, G-02 via `sys.platform` monkeypatching |
| T-AUTH-02 | `tests/auth/secure_storage/test_file_fallback_windows_root.py` | Yes | Real `windows-latest` round-trip: store → load → delete in `%LOCALAPPDATA%\spec-kitty\auth\` |
| T-PKG-01 | `tests/packaging/test_windows_no_keyring.py` | Yes | `pip list` in the CI venv does not contain `keyring` |
