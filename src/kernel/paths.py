"""Cross-platform path resolution for the spec-kitty runtime.

Provides the canonical functions for locating:
- The user-global ~/.kittify/ directory (cross-platform)
- The package-bundled mission assets (for ensure_runtime to copy from)

These functions have no spec-kitty-specific dependencies and are consumed
by multiple packages in the stack (specify_cli, charter).  They live
in kernel so that neither package needs to import from the other.
"""

from __future__ import annotations

import importlib.resources
import os
from pathlib import Path, PurePath, PurePosixPath


def _is_windows() -> bool:
    """Return True when running on Windows."""
    return os.name == "nt"


def get_kittify_home() -> Path:
    """Return the path to the user-global ~/.kittify/ directory.

    Resolution order:
    1. SPEC_KITTY_HOME environment variable (all platforms)
    2. ~/.kittify/ on macOS/Linux (Path.home() / ".kittify")
    3. %LOCALAPPDATA%\\spec-kitty\\ on Windows (via platformdirs, app name "spec-kitty")

    On Windows the app name used is ``"spec-kitty"`` so that ``kernel.paths``
    resolves to the same root as ``specify_cli.paths.get_runtime_root().base``
    (FR-005 / C-002: unified Windows root, no long-term dual root).
    The ``roaming=False`` flag matches ``get_runtime_root()`` exactly so that
    both resolve to ``%LOCALAPPDATA%\\spec-kitty``.

    On POSIX the behaviour is unchanged: ``~/.kittify/``.

    Returns:
        Path: Absolute path to the global runtime directory.

    Raises:
        RuntimeError: If the home directory cannot be determined.
    """
    if env_home := os.environ.get("SPEC_KITTY_HOME"):
        return Path(env_home)

    if _is_windows():
        # platformdirs is the only sanctioned third-party import in kernel/.
        # Use app name "spec-kitty" (not "kittify") so this matches
        # specify_cli.paths.get_runtime_root().base — the two resolutions must
        # agree to satisfy the single-root invariant (FR-005 / C-002).
        # kernel/ must not import specify_cli (architectural layer rule), so we
        # call platformdirs directly with the same arguments.
        from platformdirs import user_data_dir  # noqa: PLC0415

        return Path(str(user_data_dir("spec-kitty", appauthor=False, roaming=False)))

    return Path.home() / ".kittify"


def get_package_asset_root() -> Path:
    """Return the path to the package's bundled mission assets.

    Resolution order:
    1. SPEC_KITTY_TEMPLATE_ROOT environment variable (CI/testing)
    2. importlib.resources.files("doctrine") / "missions" (canonical location)

    Returns:
        Path: Absolute path to the missions directory in the doctrine package.

    Raises:
        FileNotFoundError: If no valid asset root can be found.
    """
    def _looks_like_missions_root(path: Path) -> bool:
        for mission_name in ("software-dev", "documentation", "research", "plan"):
            mission_dir = path / mission_name
            has_content_templates = any((mission_dir / "templates").glob("*.md"))
            has_legacy_commands = any((mission_dir / "command-templates").glob("*.md"))
            has_step_prompts = any((path / "mission-steps" / mission_name).glob("*/prompt.md"))
            if has_content_templates or has_legacy_commands or has_step_prompts:
                return True
        return False

    def _resolve_env_root(root: Path) -> Path:
        candidates = (
            root / "missions",
            root / "src" / "doctrine" / "missions",
            root.parent.parent / "doctrine" / "missions",
            root,
            root / "src" / "specify_cli" / "missions",
        )
        for candidate in candidates:
            if candidate.is_dir() and _looks_like_missions_root(candidate):
                return candidate
        raise FileNotFoundError(
            "SPEC_KITTY_TEMPLATE_ROOT does not contain mission assets: "
            f"{root}. Expected a missions directory or a Spec Kitty checkout root."
        )

    # CI/testing override
    if env_root := os.environ.get("SPEC_KITTY_TEMPLATE_ROOT"):
        root = Path(env_root)
        if root.is_dir():
            return _resolve_env_root(root)
        raise FileNotFoundError(f"SPEC_KITTY_TEMPLATE_ROOT path does not exist: {env_root}")

    # Canonical location: doctrine.missions
    try:
        doctrine_missions = Path(str(importlib.resources.files("doctrine") / "missions"))
        if doctrine_missions.is_dir():
            return doctrine_missions
    except (TypeError, ModuleNotFoundError):
        pass

    raise FileNotFoundError("Cannot locate package mission assets. Set SPEC_KITTY_TEMPLATE_ROOT or reinstall spec-kitty-cli.")


def render_runtime_path(path: Path, *, for_user: bool = True) -> str:
    """Render a runtime-state path for user-facing output.

    - On Windows: returns the real absolute path string (no tilde substitution).
    - On POSIX: if ``for_user=True`` and ``path`` is under ``$HOME``, returns
      ``~/<relpath>`` form; otherwise returns the absolute path.

    This helper exists in ``kernel`` so that every layer can render runtime
    paths without reintroducing POSIX-tilde literals in user-facing output
    on Windows (SC-002 of the Windows Compatibility Hardening mission).
    Mirrors :func:`specify_cli.paths.render_runtime_path` with identical
    semantics; kept here to preserve the kernel<-doctrine<-charter<-specify_cli
    dependency direction.
    """
    abs_path = Path(path).resolve(strict=False)
    if not for_user:
        return str(abs_path)
    if _is_windows():
        return str(abs_path)
    try:
        home = Path.home().resolve(strict=False)
        rel = abs_path.relative_to(home)
        return "~/" + to_posix(rel)
    except ValueError:
        return str(abs_path)


def to_posix(path: Path | str) -> str:
    """Normalize a path (or path-like string) to a forward-slashed string.

    The single separator-normalization seam. For a ``PurePath`` it returns
    ``.as_posix()``; for a ``str`` (git stdout, a glob pattern, user input) it
    swaps ``\\`` for ``/``. Git object/pathspec syntax and cross-platform path
    comparison require forward slashes (#2836); scattering
    ``str(x).replace(...)`` across the tree re-invited the exact per-site Windows
    drift #2836 fixed, so every such normalization routes here. Only the
    separator is touched — surrounding concerns (``.strip()``, ``.rstrip("/")``,
    splitting) stay at the call site.
    """
    if isinstance(path, PurePath):
        return path.as_posix()
    return path.replace("\\", "/")


def posix_tree_path(parts: tuple[str, ...]) -> str:
    """Join path ``parts`` into a git tree path (always forward-slashed).

    Git's ``HEAD:<path>`` object syntax and ``ls-files`` pathspec require
    forward slashes. Rendering with ``str(Path(*parts))`` uses ``os.sep`` — a
    backslash on Windows — which git rejects, making committed specs misreport
    as uncommitted (#2836). ``PurePosixPath`` renders with ``/`` on every host,
    closing the defect by construction: the string is built from the
    separator-agnostic ``parts`` tuple, never re-parsed through a host-native
    ``Path``.

    This lives in ``kernel`` as the single behaviour-agnostic tree-path seam so
    consumers in different layers (``specify_cli.missions._substantive`` and
    ``cli.commands.agent.mission_finalize``) render tree paths identically
    without importing from one another. It is the seam the #2836 regression is
    witnessed against: because the bug is a POSIX/Windows *rendering* difference
    it cannot be caught by a black-box input test on POSIX, so the guard
    substitutes ``PureWindowsPath`` for the module ``Path`` symbol to prove a
    reverted ``str(Path(*parts))`` form would reintroduce backslashes.
    """
    return PurePosixPath(*parts).as_posix() if parts else ""


def repo_tree_path(file_path: Path, repo_root: Path) -> tuple[Path, str]:
    """Return ``(git_cwd, tree_path)`` for a repo file; tree path forward-slashed.

    ``git_cwd`` is the linked-worktree root when ``file_path`` lives under
    ``.worktrees/<name>/`` — branch tree paths start at that worktree root, so a
    file at ``.worktrees/<name>/kitty-specs/<slug>/spec.md`` is addressed as
    ``kitty-specs/<slug>/spec.md`` — else the primary repo root. The tree path is
    always forward-slashed via :func:`posix_tree_path` (#2836).

    Canonical worktree-aware tree-path seam: both the committedness check
    (``specify_cli.missions._substantive._git_commit_check_context``) and
    finalize's branch-artifact reporting
    (``cli.commands.agent.mission_finalize._branch_tree_relative_path``) route
    through here, so the worktree-strip logic lives in exactly one place. Raises
    ``ValueError`` when ``file_path`` is not under ``repo_root``.
    """
    repo_abs = repo_root.resolve()
    rel = file_path.resolve().relative_to(repo_abs)
    parts = rel.parts
    if len(parts) > 2 and parts[0] == ".worktrees":
        worktree_root = repo_abs / parts[0] / parts[1]
        if worktree_root.is_dir():
            return worktree_root, posix_tree_path(parts[2:])
    return repo_abs, posix_tree_path(parts)


__all__ = [
    "get_kittify_home",
    "get_package_asset_root",
    "render_runtime_path",
    "repo_tree_path",
    "to_posix",
]
# ``posix_tree_path`` is intentionally NOT exported: it is the internal
# forward-slash-join primitive behind ``repo_tree_path`` (the public seam other
# layers consume). It stays a module-level function so the #2836 regression
# witness can substitute ``Path`` and call it directly, but it is not part of the
# public API — keeping it out of ``__all__`` satisfies the dead-symbol gate.
