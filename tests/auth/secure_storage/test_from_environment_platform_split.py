"""Unit tests for the file-only ``SecureStorage.from_environment()`` dispatch."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


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


def test_from_environment_windows_returns_windows_file_storage(monkeypatch):
    """On win32, from_environment() returns the Windows file-storage alias only."""
    prefixes = (_SPEC_KITTY_AUTH_STORAGE,)
    snapshot = _snapshot_modules(*prefixes)

    monkeypatch.setattr(sys, "platform", "win32")
    for name in list(sys.modules):
        if name.startswith(_SPEC_KITTY_AUTH_STORAGE):
            del sys.modules[name]

    import specify_cli.auth.secure_storage.abstract as abstract_mod

    importlib.reload(abstract_mod)

    try:
        storage = abstract_mod.SecureStorage.from_environment()

        from specify_cli.auth.secure_storage.windows_storage import WindowsFileStorage

        assert isinstance(storage, WindowsFileStorage), f"Expected WindowsFileStorage on win32, got {type(storage).__name__}"
        assert storage.store_path == Path.home() / ".spec-kitty" / "auth"
        assert "specify_cli.auth.secure_storage.keychain" not in sys.modules, "keychain module must never be imported in the file-only storage model"
    finally:
        _restore_modules(snapshot, *prefixes)


def test_from_environment_posix_returns_encrypted_file_storage(monkeypatch):
    """On linux, from_environment() returns the encrypted file backend."""
    prefixes = (_SPEC_KITTY_AUTH_STORAGE,)
    snapshot = _snapshot_modules(*prefixes)

    monkeypatch.setattr(sys, "platform", "linux")
    for name in list(sys.modules):
        if name.startswith(_SPEC_KITTY_AUTH_STORAGE):
            del sys.modules[name]

    import specify_cli.auth.secure_storage.abstract as abstract_mod

    importlib.reload(abstract_mod)

    try:
        storage = abstract_mod.SecureStorage.from_environment()

        from specify_cli.auth.secure_storage.file_fallback import FileFallbackStorage

        assert isinstance(storage, FileFallbackStorage), f"Expected FileFallbackStorage on linux, got {type(storage).__name__}"
        assert "specify_cli.auth.secure_storage.keychain" not in sys.modules, "keychain module must never be imported in the file-only storage model"
    finally:
        _restore_modules(snapshot, *prefixes)
