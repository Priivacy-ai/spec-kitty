"""Enhanced path resolution for spec-kitty CLI with worktree detection."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .constants import KITTIFY_DIR, WORKTREES_DIR


def _is_worktree_gitdir(gitdir: Path) -> bool:
    """Check if a gitdir path has the .git/worktrees/<name> topology.

    True git worktrees point to ``<main>/.git/worktrees/<wt-name>``.
    Bare-repo worktrees point to ``<repo>.git/worktrees/<wt-name>``.
    Submodules point to ``../.git/modules/<mod>`` and separate-git-dir
    clones point to an arbitrary directory.  Only the first two cases
    are worktrees.
    """
    # gitdir = …/.git/worktrees/<name>        (non-bare)
    # gitdir = …/<repo>.git/worktrees/<name>  (bare)
    #   gitdir.parent.name  == "worktrees"
    #   gitdir.parent.parent.name endswith ".git"
    return gitdir.parent.name == "worktrees" and gitdir.parent.parent.name.endswith(".git")


def locate_project_root(start: Path | None = None) -> Path | None:
    """
    Locate the MAIN spec-kitty project root directory, even from within worktrees.

    This function correctly handles git worktrees by detecting when .git is a
    file (worktree pointer) vs a directory (main repo), and following the
    pointer back to the main repository.

    Resolution order:
    1. SPECIFY_REPO_ROOT environment variable (highest priority)
    2. Walk up directory tree, detecting worktree .git files and following to main repo
    3. Fall back to .kittify/ marker search

    Args:
        start: Starting directory for search (defaults to current working directory)

    Returns:
        Path to MAIN project root (not worktree), or None if not found

    Examples:
        >>> # From main repo
        >>> root = locate_project_root()
        >>> assert (root / ".kittify").exists()

        >>> # From worktree - returns MAIN repo, not worktree
        >>> root = locate_project_root(Path(".worktrees/my-feature"))
        >>> assert ".worktrees" not in str(root)
    """
    # Tier 1: Check environment variable (allows override for CI/CD)
    if env_root := os.getenv("SPECIFY_REPO_ROOT"):
        env_path = Path(env_root).resolve()
        if env_path.exists() and (env_path / KITTIFY_DIR).is_dir():
            return env_path
        # Invalid env var - fall through to other methods

    # Tier 2: Walk up directory tree, handling worktree .git files
    current = (start or Path.cwd()).resolve()

    for candidate in [current, *current.parents]:
        git_path = candidate / ".git"

        if git_path.is_file():
            # .git files with gitdir: pointers appear in worktrees,
            # submodules, and separate-git-dir clones.  Only follow the
            # pointer when it has the .git/worktrees/<name> topology.
            try:
                content = git_path.read_text(encoding="utf-8", errors="replace").strip()
                if content.startswith("gitdir:"):
                    gitdir = Path(content.split(":", 1)[1].strip())
                    if _is_worktree_gitdir(gitdir):
                        # Navigate: .git/worktrees/name -> .git -> main repo root
                        main_git_dir = gitdir.parent.parent
                        main_repo = main_git_dir.parent
                        if main_repo.exists() and (main_repo / KITTIFY_DIR).is_dir():
                            return main_repo
            except (OSError, ValueError):
                # If we can't read or parse the .git file, continue searching
                pass

        elif git_path.is_dir():  # noqa: SIM102
            # This is the main repo (or a regular git repo)
            if (candidate / KITTIFY_DIR).is_dir():
                return candidate

        # Also check for .kittify marker (fallback for non-git scenarios)
        kittify_path = candidate / KITTIFY_DIR
        if kittify_path.is_symlink() and not kittify_path.exists():
            # Broken symlink - skip this candidate
            continue
        if kittify_path.is_dir():
            return candidate

    return None


def is_worktree_context(path: Path) -> bool:
    """
    Detect if the given path is within a git worktree directory.

    Checks two conditions:
    1. '.worktrees' appears in the path hierarchy (spec-kitty managed worktrees)
    2. The nearest .git entry is a file with a gitdir: pointer (generic git worktree)

    Args:
        path: Path to check (typically current working directory)

    Returns:
        True if path is within any git worktree, False otherwise

    Examples:
        >>> is_worktree_context(Path("/repo/.worktrees/feature-001"))
        True
        >>> is_worktree_context(Path("/repo/kitty-specs"))
        False
        >>> # Also detects external worktrees (e.g. under /tmp)
        >>> is_worktree_context(Path("/tmp/my-worktree"))  # if .git is a gitdir pointer
        True
    """
    # Fast path: spec-kitty managed worktrees
    if WORKTREES_DIR in path.parts:
        return True

    # Generic detection: walk up to find .git file with gitdir pointer
    # Only recognise true worktrees (.git/worktrees/<name> topology),
    # NOT submodules (.git/modules/<mod>) or separate-git-dir clones.
    resolved = path.resolve()
    for candidate in [resolved, *resolved.parents]:
        git_path = candidate / ".git"
        if git_path.is_file():
            try:
                content = git_path.read_text(encoding="utf-8", errors="replace").strip()
                if content.startswith("gitdir:"):
                    gitdir = Path(content.split(":", 1)[1].strip())
                    if _is_worktree_gitdir(gitdir):
                        return True
            except OSError:
                pass
            break
        elif git_path.is_dir():
            # Main repo .git directory — not a worktree
            break

    return False


def resolve_with_context(start: Path | None = None) -> tuple[Path | None, bool]:
    """
    Resolve project root and detect worktree context in one call.

    Args:
        start: Starting directory for search (defaults to current working directory)

    Returns:
        Tuple of (project_root, is_worktree)
        - project_root: Path to repo root or None if not found
        - is_worktree: True if executing from within .worktrees/

    Examples:
        >>> # From main repo
        >>> root, in_worktree = resolve_with_context()
        >>> assert in_worktree is False

        >>> # From worktree
        >>> root, in_worktree = resolve_with_context(Path(".worktrees/my-feature"))
        >>> assert in_worktree is True
    """
    current = (start or Path.cwd()).resolve()
    root = locate_project_root(current)
    in_worktree = is_worktree_context(current)
    return root, in_worktree


def check_broken_symlink(path: Path) -> bool:
    """
    Check if a path is a broken symlink (symlink pointing to non-existent target).

    This helper is useful for graceful error handling when dealing with
    worktree symlinks that may become invalid.

    Args:
        path: Path to check

    Returns:
        True if path is a broken symlink, False otherwise

    Note:
        A broken symlink returns True for is_symlink() but False for exists().
        Always check is_symlink() before exists() to detect this condition.
    """
    return path.is_symlink() and not path.exists()


def get_main_repo_root(current_path: Path) -> Path:
    """
    Get the main repository root, even if called from a worktree.

    When in a worktree, .git is a file pointing to the main repo's .git directory.
    This function follows that pointer to find the main repo root.

    Args:
        current_path: Current repo root (may be worktree or main repo)

    Returns:
        Path to the main repository root (resolves worktree pointers)

    Examples:
        >>> # From main repo - returns same path
        >>> get_main_repo_root(Path("/repo"))
        Path('/repo')

        >>> # From worktree - returns main repo
        >>> get_main_repo_root(Path("/repo/.worktrees/feature-001"))
        Path('/repo')
    """
    git_file = current_path / ".git"

    if git_file.is_file():
        try:
            git_content = git_file.read_text(encoding="utf-8", errors="replace").strip()
            if git_content.startswith("gitdir:"):
                gitdir_str = git_content.split(":", 1)[1].strip()
                # Validate the gitdir path is not empty (bug discovered via mutation testing)
                if gitdir_str:
                    gitdir = Path(gitdir_str)
                    # Navigate: .git/worktrees/name -> .git -> main repo root
                    main_git_dir = gitdir.parent.parent
                    main_repo_root = main_git_dir.parent
                    return main_repo_root
        except (OSError, ValueError):
            pass

    # Not a worktree - return the resolved current path
    return current_path.resolve()


def get_feature_target_branch(repo_root: Path, mission_slug: str) -> str:
    """Get target branch for a feature by reading meta.json directly.

    Reads the ``target_branch`` field from ``kitty-specs/<slug>/meta.json``.
    Falls back to the primary branch (usually ``main``) if the file is missing
    or malformed.

    Args:
        repo_root: Repository root path (may be worktree — resolved to main).
        mission_slug: Feature slug (e.g., "025-cli-event-log-integration").

    Returns:
        Target branch name (e.g., ``"main"`` or ``"2.x"``).
    """
    from specify_cli.core.git_ops import resolve_primary_branch

    main_root = get_main_repo_root(repo_root)
    meta_file = main_root / "kitty-specs" / mission_slug / "meta.json"
    fallback = resolve_primary_branch(main_root)

    if not meta_file.exists():
        return fallback

    try:
        data = json.loads(meta_file.read_text(encoding="utf-8"))
        return str(data.get("target_branch", fallback))
    except (json.JSONDecodeError, KeyError, OSError):
        return fallback


def require_explicit_feature(feature: str | None, *, command_hint: str = "") -> str:
    """Require an explicit feature slug; raise if not provided.

    Replaces heuristic detection.  Every CLI command that needs a feature slug
    must receive it via ``--mission`` (or equivalent).  No scanning, no env
    var magic, no git branch guessing.

    When the feature is missing, scans ``kitty-specs/`` for available features
    and includes them in the error message so agents can self-correct.

    Args:
        feature: The feature slug provided by the user (may be None).
        command_hint: Name of the CLI flag to mention in the error message.

    Returns:
        The feature slug (guaranteed non-empty string).

    Raises:
        ValueError: If ``feature`` is None or empty.
    """
    if feature and feature.strip():
        return feature.strip()

    flag = command_hint or "--mission <slug>"

    # Scan for available features to include in the error message
    available = ""
    try:
        root = locate_project_root()
        if root is None:
            raise RuntimeError("project root not found")
        kitty_specs = root / "kitty-specs"
        if kitty_specs.is_dir():
            slugs = sorted(
                d.name for d in kitty_specs.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            )
            if slugs:
                listing = "\n".join(f"  - {s}" for s in slugs[:15])
                if len(slugs) > 15:
                    listing += f"\n  ... and {len(slugs) - 15} more"
                available = f"\nAvailable missions:\n{listing}\n"
    except Exception:
        pass

    example_slug = "057-canonical-context-architecture-cleanup"
    if available:
        # Use the first real slug as the example
        try:
            root = locate_project_root()
            if root is None:
                raise RuntimeError("project root not found")
            first = sorted(
                d.name for d in (root / "kitty-specs").iterdir()
                if d.is_dir() and not d.name.startswith(".")
            )[0]
            example_slug = first
        except Exception:
            pass

    flag_name = flag.split()[0]  # e.g., "--mission"
    msg = (
        f"Mission slug is required. Provide it explicitly: {flag}\n"
        "No auto-detection is performed (branch scanning / env vars removed).\n"
        f"{available}"
        f"Example:\n"
        f"  spec-kitty agent context resolve --action tasks {flag_name} {example_slug} --json\n"
        f"  spec-kitty agent mission finalize-tasks {flag_name} {example_slug} --json"
    )
    raise ValueError(msg)


__all__ = [
    "locate_project_root",
    "is_worktree_context",
    "resolve_with_context",
    "check_broken_symlink",
    "get_main_repo_root",
    "get_feature_target_branch",
    "require_explicit_feature",
]
