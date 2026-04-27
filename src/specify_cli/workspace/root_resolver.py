"""Single canonical-root resolver for spec-kitty (FR-013, WP03/T013).

This module exposes :func:`resolve_canonical_root`, the single source of
truth for the question "given some CWD (which may be a worktree), what is
the canonical mission repository root?".

Status emit, charter writes, and config writes all delegate to this helper
so that no command writes to a stale worktree-local copy of the mission
artifacts.

Resolution rules:

1. ``cwd`` is inside a regular git repo (``.git`` is a directory): return
   the directory that contains ``.git``.
2. ``cwd`` is inside a worktree (``.git`` is a *file* with a
   ``gitdir: <path>`` pointer at ``.git/worktrees/<name>``): read the
   ``commondir`` file under ``.git/worktrees/<name>/`` and return its
   parent (the main repo's working tree). When ``commondir`` holds a
   relative path, it is resolved relative to the worktree's gitdir.
3. ``cwd`` is not inside a git repo at all: raise
   :class:`WorkspaceRootNotFound`.

The result is cached per resolved ``cwd`` for the lifetime of the
process, since canonical-root resolution is idempotent and is hit by
every emit pipeline at least once. The cache is module-level state and
is implicitly reset between processes; tests that need to bypass it can
call :func:`_reset_cache`.
"""

from __future__ import annotations

from pathlib import Path
from threading import Lock

__all__ = [
    "WorkspaceRootNotFound",
    "canonicalize_feature_dir",
    "resolve_canonical_root",
]


class WorkspaceRootNotFound(Exception):
    """Raised when a canonical mission repo root cannot be resolved."""

    def __init__(self, cwd: Path | str) -> None:
        self.cwd = Path(cwd)
        super().__init__(f"No git repository found at or above {self.cwd}")


# Module-level cache: resolved cwd -> canonical root.
# Keys are absolute, resolved paths so two equivalent inputs share a hit.
_CACHE: dict[Path, Path] = {}
_CACHE_LOCK = Lock()


def _reset_cache() -> None:
    """Reset the module-level cache (test helper)."""
    with _CACHE_LOCK:
        _CACHE.clear()


def _read_worktree_pointer(git_file: Path) -> Path | None:
    """Return the gitdir referenced by a worktree ``.git`` file, or None.

    A worktree ``.git`` file contains a single line of the form
    ``gitdir: /abs/path/to/main/.git/worktrees/<name>``. The path may be
    absolute or relative (relative to the file's directory).
    """
    try:
        text = git_file.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    if not text.startswith("gitdir:"):
        return None
    raw = text.split(":", 1)[1].strip()
    if not raw:
        return None
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = (git_file.parent / candidate).resolve()
    return candidate


def _canonical_from_worktree_gitdir(gitdir: Path) -> Path | None:
    """Return the canonical main-repo working tree for a worktree gitdir.

    ``gitdir`` is expected to be ``<commondir>/worktrees/<name>``. We
    confirm topology, read the ``commondir`` file when present (it may be
    a relative path), and return the parent of the resolved commondir
    (the main repo's working tree).

    Returns None when the topology does not match a true worktree
    (covers submodules and separate-git-dir clones).
    """
    if gitdir.parent.name != "worktrees":
        return None
    if not gitdir.parent.parent.name.endswith(".git"):
        return None

    commondir_file = gitdir / "commondir"
    if commondir_file.exists():
        try:
            commondir_raw = commondir_file.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            commondir_raw = ""
        if commondir_raw:
            commondir = Path(commondir_raw)
            if not commondir.is_absolute():
                commondir = (gitdir / commondir).resolve()
            # commondir typically points at the main repo's `.git` dir.
            return commondir.parent

    # Fallback: derive from gitdir topology directly.
    return gitdir.parent.parent.parent


def resolve_canonical_root(cwd: Path | None = None) -> Path:
    """Return the canonical mission repo root for ``cwd``.

    See module docstring for resolution rules. Result is cached.

    Args:
        cwd: Starting directory. Defaults to :func:`Path.cwd`.

    Returns:
        Absolute, resolved path to the canonical repo root.

    Raises:
        WorkspaceRootNotFound: when ``cwd`` is not inside a git repo.
    """
    start = (cwd or Path.cwd()).resolve()

    with _CACHE_LOCK:
        cached = _CACHE.get(start)
    if cached is not None:
        return cached

    for candidate in [start, *start.parents]:
        git_path = candidate / ".git"

        if git_path.is_dir():
            # Regular repo (or main repo of a worktree set).
            resolved = candidate.resolve()
            with _CACHE_LOCK:
                _CACHE[start] = resolved
            return resolved

        if git_path.is_file():
            gitdir = _read_worktree_pointer(git_path)
            if gitdir is None:
                # Malformed pointer; keep walking so we still find the
                # enclosing repo if there is one.
                continue
            canonical = _canonical_from_worktree_gitdir(gitdir)
            if canonical is not None:
                resolved = canonical.resolve()
                with _CACHE_LOCK:
                    _CACHE[start] = resolved
                return resolved

    raise WorkspaceRootNotFound(start)


def canonicalize_feature_dir(feature_dir: Path) -> Path:
    """Return the canonical-root version of ``feature_dir`` when possible.

    Many emit callers construct ``feature_dir = repo_root / "kitty-specs" /
    <slug>`` from a *worktree* repo_root. When that happens, status emit,
    charter writes, and config writes would land inside the worktree's
    stale copy of the mission artifacts instead of the canonical repo.

    This helper rewrites such paths to point at the canonical repo's
    ``kitty-specs/<slug>`` directory. When ``feature_dir`` cannot be
    canonicalized (no enclosing git repo, unexpected layout, etc.) the
    original value is returned unchanged so callers degrade gracefully.

    Args:
        feature_dir: Path to a kitty-specs/<slug> directory (or anything
            else; non-conforming inputs are returned as-is).

    Returns:
        The canonical-root-rooted feature directory, or ``feature_dir``
        when canonicalization does not apply.
    """
    feature_dir = Path(feature_dir)
    parent = feature_dir.parent
    if parent.name != "kitty-specs":
        return feature_dir

    try:
        canonical_root = resolve_canonical_root(feature_dir)
    except WorkspaceRootNotFound:
        return feature_dir

    canonical_feature_dir = canonical_root / "kitty-specs" / feature_dir.name
    # Only redirect when the canonical path actually exists; this keeps
    # tests that build ad-hoc feature dirs outside a git repo working.
    if canonical_feature_dir.exists():
        return canonical_feature_dir
    return feature_dir
