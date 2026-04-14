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
from pathlib import Path


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

        return Path(user_data_dir("spec-kitty", appauthor=False, roaming=False))

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
    # CI/testing override
    if env_root := os.environ.get("SPEC_KITTY_TEMPLATE_ROOT"):
        root = Path(env_root)
        if root.is_dir():
            return root
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
        return "~/" + str(rel).replace("\\", "/")
    except ValueError:
        return str(abs_path)


__all__ = ["get_kittify_home", "get_package_asset_root", "render_runtime_path"]
