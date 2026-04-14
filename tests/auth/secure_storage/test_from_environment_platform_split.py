"""T016 — Unit tests: SecureStorage.from_environment() hard platform dispatch.

These tests use monkeypatching so they run on POSIX without requiring Windows.
They exercise the hard platform split introduced by WP03 (FR-001, FR-002, C-001).

Note: importlib.reload() is fragile by design — this is a platform-dispatch
smoke test, not a general-purpose pattern.  Each test saves and restores the
original module objects to avoid polluting subsequent test collection.
"""

from __future__ import annotations

import importlib
import sys


def _snapshot_modules(*prefixes: str) -> dict[str, object]:
    """Return a copy of sys.modules for all keys matching any prefix."""
    return {k: v for k, v in sys.modules.items() if any(k.startswith(p) for p in prefixes)}


def _restore_modules(snapshot: dict[str, object], *prefixes: str) -> None:
    """Remove newly-added modules and restore the snapshotted state."""
    for key in list(sys.modules):
        if any(key.startswith(p) for p in prefixes):
            del sys.modules[key]
    sys.modules.update(snapshot)


_SPEC_KITTY_AUTH_STORAGE = "specify_cli.auth.secure_storage"
_SPEC_KITTY_PATHS = "specify_cli.paths"


def test_from_environment_windows_returns_windows_file_storage(monkeypatch, tmp_path):
    """On win32, from_environment() returns WindowsFileStorage without importing keychain."""
    # Snapshot the full auth secure_storage and paths module state before touching anything.
    prefixes = (_SPEC_KITTY_AUTH_STORAGE, _SPEC_KITTY_PATHS)
    snapshot = _snapshot_modules(*prefixes)

    monkeypatch.setattr(sys, "platform", "win32")

    # Remove keychain and abstract so they're re-evaluated with the patched platform.
    for name in list(sys.modules):
        if name.startswith("specify_cli.auth.secure_storage"):
            del sys.modules[name]

    # Reload abstract to pick up the patched sys.platform.
    import specify_cli.auth.secure_storage.abstract as abstract_mod

    importlib.reload(abstract_mod)

    # Patch paths.get_runtime_root so the Windows path resolves in a POSIX env.
    from specify_cli.paths.windows_paths import RuntimeRoot

    fake_root = RuntimeRoot(platform="win32", base=tmp_path)

    import specify_cli.auth.secure_storage.windows_storage as ws_mod

    monkeypatch.setattr(ws_mod, "get_runtime_root", lambda: fake_root, raising=False)

    # Also patch at the paths module level.
    import specify_cli.paths as paths_pkg

    monkeypatch.setattr(paths_pkg, "get_runtime_root", lambda: fake_root)

    try:
        storage = abstract_mod.SecureStorage.from_environment()

        from specify_cli.auth.secure_storage.windows_storage import WindowsFileStorage

        assert isinstance(storage, WindowsFileStorage), (
            f"Expected WindowsFileStorage on win32, got {type(storage).__name__}"
        )
        assert "specify_cli.auth.secure_storage.keychain" not in sys.modules, (
            "keychain module must NOT be imported when sys.platform == 'win32'"
        )
    finally:
        # Restore all modules to their pre-test state so later tests see
        # a clean sys.modules (avoids class identity breakage from reload).
        _restore_modules(snapshot, *prefixes)


def test_from_environment_posix_returns_keychain_or_file(monkeypatch):
    """On linux, from_environment() returns KeychainStorage or EncryptedFileStorage."""
    prefixes = (_SPEC_KITTY_AUTH_STORAGE,)
    snapshot = _snapshot_modules(*prefixes)

    monkeypatch.setattr(sys, "platform", "linux")

    for name in list(sys.modules):
        if name.startswith("specify_cli.auth.secure_storage"):
            del sys.modules[name]

    import specify_cli.auth.secure_storage.abstract as abstract_mod

    importlib.reload(abstract_mod)

    try:
        storage = abstract_mod.SecureStorage.from_environment()

        from specify_cli.auth.secure_storage.file_fallback import FileFallbackStorage

        # On POSIX the existing keychain-first-try-fallback behaviour is preserved;
        # we accept either backend since keyring may or may not have a real backend.
        try:
            from specify_cli.auth.secure_storage.keychain import KeychainStorage

            assert isinstance(storage, (KeychainStorage, FileFallbackStorage)), (
                f"Unexpected backend on linux: {type(storage).__name__}"
            )
        except ImportError:
            # keyring not installed — file fallback is the only valid result.
            assert isinstance(storage, FileFallbackStorage), (
                f"Expected FileFallbackStorage fallback, got {type(storage).__name__}"
            )
    finally:
        _restore_modules(snapshot, *prefixes)
