"""Fixture wiring for ``tests/specify_cli/coordination/``.

Provides the simulated Windows CRT text-mode fixture (#4181) by pytest
fixture injection (parameter name) rather than a module-level import that
shadows the parameter (F811) — same rationale as
``tests/specify_cli/conftest.py``'s re-export of the flat-topology mission
fixture.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture
def windows_crt_textmode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate the Windows CRT newline translation that caused #4181.

    Strips the fd-relative capability surface (empty ``os.supports_dir_fd``,
    no ``O_DIRECTORY`` / ``O_NOFOLLOW`` — deleted only when present, so the
    fixture is itself Windows-safe) and additionally reproduces the *native*
    Windows behavior a capability strip alone cannot: a descriptor opened by
    ``os.open`` without ``O_BINARY`` is in CRT text mode, so every
    ``os.write`` to it turns ``b"\\n"`` into ``b"\\r\\n"`` — LF becomes CRLF
    and an existing CRLF becomes CRCRLF. ``os.O_BINARY`` is injected (POSIX
    has no such constant) so the production ``getattr(os, "O_BINARY", 0)``
    resolves to the simulated flag, and the injected bit is masked back out
    before the real ``os.open`` sees it.

    Only the confined write's own ``.spec-kitty-*.tmp`` creation opens are
    wrapped, so every other descriptor in the process (the lock file, the
    event log, pytest's own I/O) keeps byte-exact behavior.
    """
    monkeypatch.setattr(os, "supports_dir_fd", set())
    if hasattr(os, "O_DIRECTORY"):
        monkeypatch.delattr(os, "O_DIRECTORY")
    if hasattr(os, "O_NOFOLLOW"):
        monkeypatch.delattr(os, "O_NOFOLLOW")

    injected = not hasattr(os, "O_BINARY")
    binary_flag = 1 << 30 if injected else os.O_BINARY
    if injected:
        monkeypatch.setattr(os, "O_BINARY", binary_flag, raising=False)
    real_open, real_write, real_close = os.open, os.write, os.close
    textmode_fds: set[int] = set()

    def translating_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
        passthrough_flags = flags & ~binary_flag if injected else flags
        fd = real_open(path, passthrough_flags, *args, **kwargs)  # type: ignore[no-any-return]
        if flags & os.O_CREAT and not flags & binary_flag and isinstance(path, (str, os.PathLike)) and Path(path).name.startswith(".spec-kitty-"):
            textmode_fds.add(fd)
        return fd

    def translating_write(fd: int, data: object) -> int:
        if fd in textmode_fds:
            original = bytes(data)  # type: ignore[arg-type]
            translated = original.replace(b"\n", b"\r\n")
            view = memoryview(translated)
            offset = 0
            while offset < len(translated):
                offset += real_write(fd, view[offset:])
            # Report progress against the caller's original buffer so the
            # production partial-write loop stays consistent.
            return len(original)
        return real_write(fd, data)  # type: ignore[return-value, arg-type]

    def discarding_close(fd: int) -> None:
        textmode_fds.discard(fd)
        real_close(fd)

    monkeypatch.setattr(os, "open", translating_open)
    monkeypatch.setattr(os, "write", translating_write)
    monkeypatch.setattr(os, "close", discarding_close)
