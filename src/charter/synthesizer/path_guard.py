"""PathGuard — the sole write seam for all synthesizer filesystem mutations.

Every file write inside the synthesizer package MUST go through PathGuard
methods. Any attempted write outside the configured allowlist raises
PathGuardViolation BEFORE the filesystem is touched (FR-016, US-7).

The default allowlist covers:
- .kittify/doctrine/   (synthesized content)
- .kittify/charter/    (synthesis bookkeeping + staging)

A lint-style test (tests/charter/synthesizer/test_path_guard.py) greps
src/charter/synthesizer/ for direct write primitives to catch regressions (R-10).

Changes to this module — especially the allowlist or the bypass check logic —
require an explicit code review; see ADR-2026-04-17-2 §path-guard.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from collections.abc import Sequence

from .errors import PathGuardViolation


# Default allowed path prefixes (relative to repo_root, resolved to absolute).
_DEFAULT_ALLOWLIST: tuple[str, ...] = (
    ".kittify/doctrine",
    ".kittify/charter",
)


class PathGuard:
    """Enforces write boundaries for all synthesizer filesystem mutations.

    Constructor parameters
    ----------------------
    repo_root:
        Absolute path to the repository root. All relative allowlist prefixes
        are resolved against this.
    extra_allowed_prefixes:
        Additional allowed path prefixes (absolute or relative to repo_root).
        Used in tests to allow writes into tmp_path.
    """

    def __init__(
        self,
        repo_root: Path,
        extra_allowed_prefixes: Sequence[str | Path] = (),
    ) -> None:
        self._repo_root = repo_root.resolve()
        self._allowed: tuple[Path, ...] = tuple(
            self._resolve_prefix(p)
            for p in (*_DEFAULT_ALLOWLIST, *extra_allowed_prefixes)
        )

    def _resolve_prefix(self, prefix: str | Path) -> Path:
        p = Path(prefix)
        if p.is_absolute():
            return p.resolve()
        return (self._repo_root / p).resolve()

    def _assert_allowed(self, target: Path, caller: str) -> None:
        """Raise PathGuardViolation if target is not under any allowed prefix."""
        resolved = target.resolve()
        for allowed in self._allowed:
            try:
                resolved.relative_to(allowed)
                return  # target is under this allowed prefix — OK
            except ValueError:
                continue
        raise PathGuardViolation(
            attempted_path=str(resolved),
            caller=caller,
        )

    # -----------------------------------------------------------------------
    # Write methods — all filesystem mutations go through here
    # -----------------------------------------------------------------------

    def write_text(
        self,
        path: Path,
        text: str,
        encoding: str = "utf-8",
        caller: str = "write_text",
    ) -> None:
        """Write text to path, raising PathGuardViolation if path is not allowed."""
        self._assert_allowed(path, caller)
        path.write_text(text, encoding=encoding)

    def write_bytes(
        self,
        path: Path,
        data: bytes,
        caller: str = "write_bytes",
    ) -> None:
        """Write bytes to path, raising PathGuardViolation if path is not allowed."""
        self._assert_allowed(path, caller)
        path.write_bytes(data)

    def replace(
        self,
        src: Path,
        dst: Path,
        caller: str = "replace",
    ) -> None:
        """Atomically replace dst with src (os.replace semantics).

        Both src and dst must be under the allowlist. src is the staging
        location (also allowed); dst is the final live location.
        """
        self._assert_allowed(src, f"{caller}[src]")
        self._assert_allowed(dst, f"{caller}[dst]")
        os.replace(src, dst)

    def mkdir(
        self,
        path: Path,
        parents: bool = True,
        exist_ok: bool = True,
        caller: str = "mkdir",
    ) -> None:
        """Create directory (and parents), raising PathGuardViolation if not allowed."""
        self._assert_allowed(path, caller)
        path.mkdir(parents=parents, exist_ok=exist_ok)

    def rmtree(
        self,
        path: Path,
        caller: str = "rmtree",
    ) -> None:
        """Remove a directory tree, raising PathGuardViolation if not allowed.

        Used to clean up successful staging dirs after promote.
        """
        self._assert_allowed(path, caller)
        shutil.rmtree(path, ignore_errors=True)

    def rename(
        self,
        src: Path,
        dst: Path,
        caller: str = "rename",
    ) -> None:
        """Rename src to dst, raising PathGuardViolation if either is not allowed."""
        self._assert_allowed(src, f"{caller}[src]")
        self._assert_allowed(dst, f"{caller}[dst]")
        src.rename(dst)
