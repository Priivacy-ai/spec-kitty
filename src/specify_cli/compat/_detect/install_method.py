"""Install-method detection for the upgrade-nag planner.

Public surface
--------------
InstallMethod  -- str enum with seven members.
detect_install_method  -- pure detection function; NEVER raises.

Detection chain (first match wins, per research §R-03):
  1. SOURCE        -- package __file__ under cwd AND pyproject.toml present.
  2. PIPX          -- executable under */pipx/venvs/spec-kitty* or ~/.local/pipx/venvs/.
  3. BREW          -- executable under a Homebrew prefix.
  4. SYSTEM_PACKAGE -- /usr/bin/python* executable AND system-manager INSTALLER.
  5. PIP_USER      -- pip INSTALLER AND distribution under user site-packages.
  6. PIP_SYSTEM    -- pip INSTALLER, not under user site-packages.
  7. UNKNOWN       -- fallback.

Security / reliability properties
-----------------------------------
CHK032  Every branch is wrapped in try/except; the function MUST NOT raise.
        Any unexpected exception silently falls through to the next branch.
        subprocess.run calls have a hard 1 s timeout.
"""

from __future__ import annotations

import importlib.metadata
import site
import subprocess
import sys
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path


# ---------------------------------------------------------------------------
# InstallMethod enum
# ---------------------------------------------------------------------------


class InstallMethod(StrEnum):
    """How the running ``spec-kitty-cli`` was installed.

    Values are stable JSON tokens (data-model §1.7).
    """

    PIPX = "pipx"
    PIP_USER = "pip-user"
    PIP_SYSTEM = "pip-system"
    BREW = "brew"
    SYSTEM_PACKAGE = "system-package"
    SOURCE = "source"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Detection helpers (private)
# ---------------------------------------------------------------------------

_PACKAGE_NAME = "spec-kitty-cli"


def _is_source_install() -> bool:
    """Return True if the package is running from a source / editable checkout."""
    try:
        import specify_cli as _pkg  # type: ignore[import-untyped,unused-ignore]

        pkg_file = Path(_pkg.__file__)
        cwd = Path.cwd()
        # Walk up the parents to find the package root (directory containing __file__).
        for parent in pkg_file.parents:
            if (parent / "pyproject.toml").exists():
                # Check that the package root is under cwd.
                try:
                    parent.relative_to(cwd)
                    return True
                except ValueError:
                    pass
                break
    except Exception:  # noqa: BLE001
        pass
    return False


def _is_pipx_install(executable: str) -> bool:
    """Return True if *executable* looks like a pipx-managed venv."""
    try:
        exe_path = Path(executable)
        exe_str = str(exe_path)
        # Match */pipx/venvs/spec-kitty*
        if "pipx" in exe_str and "venvs" in exe_str and "spec-kitty" in exe_str:
            return True
        # Match under ~/.local/pipx/venvs/ or /usr/local/pipx/venvs/
        pipx_roots = [
            Path.home() / ".local" / "pipx" / "venvs",
            Path("/usr/local/pipx/venvs"),
        ]
        for root in pipx_roots:
            try:
                exe_path.relative_to(root)
                return True
            except ValueError:
                pass
    except Exception:  # noqa: BLE001
        pass
    return False


def _brew_prefix() -> str | None:
    """Return the Homebrew prefix by running ``brew --prefix``, or None on failure."""
    try:
        result = subprocess.run(
            ["brew", "--prefix"],
            capture_output=True,
            timeout=1.0,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.decode("utf-8", errors="replace").strip()
    except Exception:  # noqa: BLE001
        pass
    return None


def _is_brew_install(executable: str) -> bool:
    """Return True if *executable* lives under a Homebrew prefix."""
    try:
        exe_path = Path(executable)
        exe_str = str(exe_path)

        # Static heuristics (no subprocess needed for common cases).
        static_prefixes = [
            "/opt/homebrew/",
            "/usr/local/Cellar/",
            "/usr/local/opt/",
        ]
        for prefix in static_prefixes:
            if exe_str.startswith(prefix):
                return True

        # Try to get the dynamic prefix from brew --prefix.
        brew_prefix = _brew_prefix()
        if brew_prefix:
            cellar = str(Path(brew_prefix) / "Cellar")
            opt_path = str(Path(brew_prefix) / "opt")
            if exe_str.startswith(cellar) or exe_str.startswith(opt_path):
                return True
    except Exception:  # noqa: BLE001
        pass
    return False


def _get_installer(distribution_loader: Callable[[str], importlib.metadata.Distribution]) -> str | None:
    """Return the INSTALLER text for spec-kitty-cli, or None on failure."""
    try:
        dist = distribution_loader(_PACKAGE_NAME)
        installer_raw = dist.read_text("INSTALLER")
        if installer_raw is not None:
            return installer_raw.strip()
    except Exception:  # noqa: BLE001
        pass
    return None


def _get_distribution_location(
    distribution_loader: Callable[[str], importlib.metadata.Distribution],
) -> str | None:
    """Return the location string for the spec-kitty-cli distribution, or None."""
    try:
        dist = distribution_loader(_PACKAGE_NAME)
        # importlib.metadata distributions expose their location via `_path` or
        # the first element of `files` parent walking, but the most portable
        # approach is to use the metadata_path attribute when available.
        # The standard location is available via `dist._path` or its parent.
        meta_path = getattr(dist, "_path", None)
        if meta_path is not None:
            # The dist-info dir is inside the site-packages directory.
            return str(Path(meta_path).parent)
        # Fallback: walk the first file entry up to site-packages level.
        files = dist.files
        if files:
            # Most packages have at least one top-level file; go up enough levels.
            # locate_file returns a SimplePath; str() it before Path() to avoid
            # type-checker complaints (importlib.metadata.SimplePath is not
            # a PathLike[str]).
            first = str(dist.locate_file(files[0]))
            # site-packages is typically 1–2 levels above the first file.
            return str(Path(first).parent.parent)
    except Exception:  # noqa: BLE001
        pass
    return None


def _is_user_site(
    distribution_loader: Callable[[str], importlib.metadata.Distribution],
) -> bool:
    """Return True if the spec-kitty-cli distribution lives under user site-packages."""
    try:
        user_site = site.getusersitepackages()
        loc = _get_distribution_location(distribution_loader)
        if loc is not None:
            return loc.startswith(user_site)
    except Exception:  # noqa: BLE001
        pass
    return False


# ---------------------------------------------------------------------------
# Public detection function
# ---------------------------------------------------------------------------

_SYSTEM_PACKAGE_INSTALLERS = frozenset({"apt", "dnf", "pacman", "yum", "zypper"})


def detect_install_method(
    *,
    executable: str | None = None,
    distribution_loader: Callable[[str], importlib.metadata.Distribution] | None = None,
) -> InstallMethod:
    """Detect how ``spec-kitty-cli`` was installed.

    This function MUST NEVER raise.  Every branch is guarded by a try/except
    that falls through silently to the next branch (CHK032).

    Detection chain (first match wins, per research §R-03):

    1. **SOURCE** -- the package's ``__file__`` is under ``cwd`` and a
       ``pyproject.toml`` exists at the package root.
    2. **PIPX** -- ``executable`` matches ``*/pipx/venvs/spec-kitty*`` or lives
       under ``~/.local/pipx/venvs/``.
    3. **BREW** -- ``executable`` lives under a Homebrew prefix directory.
    4. **SYSTEM_PACKAGE** -- ``executable`` starts with ``/usr/bin/python`` AND
       the distribution INSTALLER is a system package manager.
    5. **PIP_USER** -- INSTALLER is ``pip`` AND the distribution is under the
       user site-packages directory.
    6. **PIP_SYSTEM** -- INSTALLER is ``pip`` (not under user site-packages).
    7. **UNKNOWN** -- no branch matched.

    Args:
        executable: Path to the Python interpreter to inspect.  Defaults to
            ``sys.executable``.
        distribution_loader: Callable matching ``importlib.metadata.distribution``'s
            signature.  Injectable for testing; defaults to
            ``importlib.metadata.distribution``.

    Returns:
        The detected :class:`InstallMethod`.  Never raises.
    """
    if executable is None:
        executable = sys.executable
    if distribution_loader is None:
        distribution_loader = importlib.metadata.distribution

    # 1. Source / dev install.
    try:
        if _is_source_install():
            return InstallMethod.SOURCE
    except Exception:  # noqa: BLE001
        pass

    # 2. pipx.
    try:
        if _is_pipx_install(executable):
            return InstallMethod.PIPX
    except Exception:  # noqa: BLE001
        pass

    # 3. Homebrew.
    try:
        if _is_brew_install(executable):
            return InstallMethod.BREW
    except Exception:  # noqa: BLE001
        pass

    # 4. System package manager.
    try:
        if executable.startswith("/usr/bin/python"):
            installer = _get_installer(distribution_loader)
            if installer in _SYSTEM_PACKAGE_INSTALLERS:
                return InstallMethod.SYSTEM_PACKAGE
    except Exception:  # noqa: BLE001
        pass

    # 5 & 6. pip (user vs system).
    try:
        installer = _get_installer(distribution_loader)
        if installer == "pip":
            if _is_user_site(distribution_loader):
                return InstallMethod.PIP_USER
            return InstallMethod.PIP_SYSTEM
    except Exception:  # noqa: BLE001
        pass

    # 7. Fallback.
    return InstallMethod.UNKNOWN
