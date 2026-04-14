"""Canonical repo root resolution via ``git rev-parse --git-common-dir``.

Contract: ``kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/contracts/canonical-root-resolver.contract.md``

Key invariant: ``git rev-parse --git-common-dir`` stdout is CWD-relative in
the common case (e.g. ``.git`` or ``../../.git``). It is absolute only for
linked worktrees. Callers MUST resolve the returned path against ``cwd``.

This module is the sole canonical-root authority for the unified charter
bundle chokepoint (FR-003, FR-006, NFR-003). It raises loudly per C-001 — no
fallback handlers, no silent degradation.
"""
from __future__ import annotations

import subprocess
from functools import lru_cache
from pathlib import Path


class NotInsideRepositoryError(RuntimeError):
    """Raised when ``resolve_canonical_repo_root`` is called outside any git repo.

    Also raised when the input path resolves to a location inside a ``.git/``
    directory itself, which the resolver treats as "not a valid project root".
    """

    def __init__(self, path: Path):
        self.path = path
        super().__init__(
            f"Path {path!r} is not inside a git repository. "
            f"Charter resolution requires a git-tracked project root."
        )


class GitCommonDirUnavailableError(RuntimeError):
    """Raised when ``git rev-parse --git-common-dir`` cannot be invoked.

    Covers binary-missing (``FileNotFoundError`` from ``subprocess.run``) and
    non-"not a git repository" failures (corrupt ``.git``, permission denied,
    etc.). Per C-001, neither failure has a fallback handler.
    """

    def __init__(self, path: Path, detail: str):
        self.path = path
        self.detail = detail
        super().__init__(
            f"git rev-parse --git-common-dir failed for {path!r}: {detail}. "
            f"Install a supported git binary and retry."
        )


@lru_cache(maxsize=256)
def _resolve_cached(abs_path_str: str) -> str:
    """Cache-amortized implementation of the six-step resolver algorithm.

    The cache key is the stringified absolute path to keep ``functools.lru_cache``
    hashable. The public ``resolve_canonical_repo_root`` resolves the input
    ``Path`` to its absolute form before stringifying.
    """
    path = Path(abs_path_str)

    # Step 1: normalize file input to parent directory.
    cwd = path.parent if path.is_file() else path

    # Step 2: invoke git exactly once.
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GitCommonDirUnavailableError(path, "git binary not found on PATH") from exc

    # Step 3: classify exit code.
    if result.returncode != 0:
        stderr = (result.stderr or "").lower()
        if "not a git repository" in stderr:
            raise NotInsideRepositoryError(path)
        raise GitCommonDirUnavailableError(path, (result.stderr or "").strip())

    # Step 4: parse stdout; resolve relative-to-cwd when not absolute.
    raw = result.stdout.strip()
    common_dir = Path(raw)
    if not common_dir.is_absolute():
        common_dir = (cwd / common_dir).resolve()
    else:
        common_dir = common_dir.resolve()

    # Step 5: explicit ``.git/``-interior detection.
    if path == common_dir or common_dir in path.parents:
        raise NotInsideRepositoryError(path)

    # Step 6: canonical root is the parent of the common dir.
    return str(common_dir.parent)


def resolve_canonical_repo_root(path: Path) -> Path:
    """Resolve ``path`` to the canonical (main-checkout) project root.

    See ``contracts/canonical-root-resolver.contract.md`` for the full
    behavioral matrix and error surface. The function performs at most one
    ``git rev-parse --git-common-dir`` invocation per cold call and zero on
    warm (LRU-cached) calls.

    Args:
        path: Any path (file or directory). May be absolute or relative. File
            inputs are normalized to their parent directory before invocation.

    Returns:
        Absolute path to the canonical project root (the main checkout).

    Raises:
        NotInsideRepositoryError: ``path`` is not inside any git repo, or is
            inside a ``.git/`` directory.
        GitCommonDirUnavailableError: ``git`` binary missing or
            ``git rev-parse --git-common-dir`` failed for any other reason.
    """
    abs_path = path.resolve()
    return Path(_resolve_cached(str(abs_path)))


# Expose ``cache_clear`` on the public surface so tests that mutate the
# filesystem layout mid-run can reset the LRU cache without reaching into
# the private helper.
resolve_canonical_repo_root.cache_clear = _resolve_cached.cache_clear  # type: ignore[attr-defined]


__all__ = [
    "GitCommonDirUnavailableError",
    "NotInsideRepositoryError",
    "resolve_canonical_repo_root",
]
