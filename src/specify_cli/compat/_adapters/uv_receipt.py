"""Single authoritative uv-receipt.toml parser (FR-007).

Public surface
--------------
UvReceiptResult  -- Frozen dataclass: all fields extractable from a uv receipt.
UvReceiptReader  -- Static-method parser; never raises (NFR-003).

This module is the strangler step 2 for the three independent receipt-parsing
implementations:
  Set A: cli/commands/review/__init__.py
  Set B: readiness/upgrade_ux.py
  Set C: compat/_detect/install_method.py  (detection-only probe)

WP04 and WP05 will migrate the call sites to this reader. Until then, the
duplicate parsers continue to operate unchanged (backward-compatible extraction).

NFR-003 / CHK032: Every probe is wrapped in try/except Exception so the reader
never raises, even on malformed/missing receipts.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

# Safe top-level import: compat._detect.runtime only imports back to this module
# inside deferred function bodies (not at module load time), so there is no
# circular import at import time.
from specify_cli.compat._detect.runtime import PackageSource, UvRequirement

# Receipt requirement keys the domain models. An entry carrying any key
# outside this set is flagged ``is_supported=False`` so the remediation
# planner refuses to reconstruct a (lossy) command from it — preserving
# provenance instead of clobbering the user's real source (issue #1358).
_SUPPORTED_REQUIREMENT_KEYS = frozenset(
    {"name", "specifier", "directory", "editable", "path", "git", "url"}
)


# ---------------------------------------------------------------------------
# UvReceiptResult frozen dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UvReceiptResult:
    """All fields extractable from a uv-receipt.toml for a given executable.

    NFR-003: Any filesystem error, TOML parse error, or schema mismatch
    results in None for the affected field, never a raise.

    All fields may be None/empty when the receipt is unavailable or malformed.
    """

    receipt_path: Path | None
    tool_dir: Path | None
    bin_dir: Path | None
    is_default_tool_dir: bool | None
    is_default_bin_dir: bool | None
    python: str | None
    requirements: tuple[UvRequirement, ...]
    package_source: PackageSource


# ---------------------------------------------------------------------------
# Empty result sentinel
# ---------------------------------------------------------------------------


def _empty_result() -> UvReceiptResult:
    """Return an all-None/empty UvReceiptResult for error paths."""
    return UvReceiptResult(
        receipt_path=None,
        tool_dir=None,
        bin_dir=None,
        is_default_tool_dir=None,
        is_default_bin_dir=None,
        python=None,
        requirements=(),
        package_source=PackageSource.UNKNOWN,
    )


# ---------------------------------------------------------------------------
# Helper: find the uv-receipt.toml path for an executable
# ---------------------------------------------------------------------------

_PACKAGE_NAME = "spec-kitty-cli"


def _receipt_path_for_executable(executable: str) -> Path | None:
    """Return the receipt path for *executable*, or None.

    Looks for uv-receipt.toml in the tool-env directory that contains the
    executable's bin/scripts directory.  Returns None if not found.
    """
    exe_path = Path(executable)
    executable_parent = exe_path.parent
    if executable_parent.name.lower() not in {"bin", "scripts"}:
        return None
    tool_env = executable_parent.parent
    receipt_path = tool_env / "uv-receipt.toml"
    if receipt_path.exists():
        return receipt_path
    return None


def _default_uv_tool_dir() -> Path:
    """Return the default uv tool directory for the current platform."""
    try:
        from platformdirs import user_data_dir  # type: ignore[import-not-found]

        return Path(user_data_dir("uv")) / "tools"
    except ImportError:
        pass
    # Manual fallback: uv default on Linux/macOS is ~/.local/share/uv/tools
    return Path.home() / ".local" / "share" / "uv" / "tools"


def _default_uv_bin_dir() -> Path:
    """Return the default uv tool bin directory for the current platform."""
    try:
        from platformdirs import user_data_dir  # noqa: PLC0415  (same import, ignore comment omitted)

        return Path(user_data_dir("uv")) / "bin"
    except ImportError:
        pass
    return Path.home() / ".local" / "share" / "uv" / "bin"


def _resolve_tool_dir(receipt_path: Path) -> Path:
    """Return the uv tool directory from env var or path derivation."""
    uv_tool_dir = os.environ.get("UV_TOOL_DIR", "")
    if uv_tool_dir:
        return Path(uv_tool_dir)
    # tool_env is the directory that contains uv-receipt.toml;
    # its parent is the tool directory.
    return receipt_path.parent.parent


def _derive_package_source(requirements: list[object]) -> PackageSource:
    """Derive package source from the spec-kitty-cli requirement entry."""
    for req in requirements:
        if not isinstance(req, dict):
            continue
        if req.get("name") != _PACKAGE_NAME:
            continue
        if req.get("git") is not None:
            return PackageSource.GIT
        if req.get("url") is not None:
            return PackageSource.URL
        if req.get("directory") is not None:
            return PackageSource.DIRECTORY
        if req.get("editable") is not None:
            return PackageSource.EDITABLE
        if req.get("path") is not None:
            return PackageSource.PATH
        if req.get("specifier") is not None:
            return PackageSource.PYPI_SPECIFIER
        # name present but no source discriminator → treat as PYPI_SPECIFIER
        return PackageSource.PYPI_SPECIFIER
    return PackageSource.UNKNOWN


def _parse_requirements(raw: object) -> tuple[UvRequirement, ...]:
    """Parse requirements list from TOML into a tuple of UvRequirement."""
    if not isinstance(raw, list):
        return ()
    result = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            continue
        specifier = entry.get("specifier")
        directory = entry.get("directory")
        editable = entry.get("editable")
        path = entry.get("path")
        git = entry.get("git")
        url = entry.get("url")
        result.append(
            UvRequirement(
                name=name,
                specifier=specifier if isinstance(specifier, str) else None,
                directory=directory if isinstance(directory, str) else None,
                editable=editable if isinstance(editable, str) else None,
                path=path if isinstance(path, str) else None,
                git=git if isinstance(git, str) else None,
                url=url if isinstance(url, str) else None,
                is_supported=set(entry.keys()).issubset(_SUPPORTED_REQUIREMENT_KEYS),
            )
        )
    return tuple(result)


def _parse_bin_dir(receipt: dict[str, object]) -> Path | None:
    """Extract bin_dir from receipt entrypoints, falling back to tool.bin_dir."""
    tool = receipt.get("tool")
    if not isinstance(tool, dict):
        return None

    # Prefer explicit bin_dir field in tool section if present
    bin_dir_raw = tool.get("bin_dir")
    if isinstance(bin_dir_raw, str) and bin_dir_raw:
        return Path(bin_dir_raw)

    # Derive from the spec-kitty entrypoint install-path
    entrypoints = tool.get("entrypoints", [])
    if isinstance(entrypoints, list):
        for ep in entrypoints:
            if not isinstance(ep, dict) or ep.get("name") != "spec-kitty":
                continue
            install_path = ep.get("install-path")
            if isinstance(install_path, str) and install_path:
                return Path(install_path).parent

    return None


# ---------------------------------------------------------------------------
# UvReceiptReader
# ---------------------------------------------------------------------------


class UvReceiptReader:
    """Single authoritative uv-receipt.toml parser.

    Replaces the three independent implementations in:
    - cli/commands/review/__init__.py (Set A)
    - readiness/upgrade_ux.py (Set B)
    - compat/_detect/install_method.py (detection-only probe, Set C)

    NFR-003: all methods never raise.
    """

    @staticmethod
    def read_for_executable(executable: str) -> UvReceiptResult:
        """Read and parse the uv receipt for the running executable.

        Never raises (NFR-003 / CHK032). Returns a result with all fields
        None/empty on any error.
        """
        try:  # noqa: BLE001
            receipt_path = _receipt_path_for_executable(executable)
            if receipt_path is None:
                return _empty_result()

            try:
                content = receipt_path.read_text(encoding="utf-8")
                receipt = tomllib.loads(content)
            except Exception:  # noqa: BLE001
                return _empty_result()

            if not isinstance(receipt, dict):
                return _empty_result()

            tool = receipt.get("tool")
            tool_dict: dict[str, object] = tool if isinstance(tool, dict) else {}

            tool_dir = _resolve_tool_dir(receipt_path)
            default_tool_dir = _default_uv_tool_dir()
            try:
                is_default_tool_dir: bool | None = tool_dir.resolve() == default_tool_dir.resolve()
            except Exception:  # noqa: BLE001
                is_default_tool_dir = tool_dir == default_tool_dir

            bin_dir = _parse_bin_dir(receipt)
            if bin_dir is not None:
                default_bin_dir = _default_uv_bin_dir()
                try:
                    is_default_bin_dir: bool | None = bin_dir.resolve() == default_bin_dir.resolve()
                except Exception:  # noqa: BLE001
                    is_default_bin_dir = bin_dir == default_bin_dir
            else:
                is_default_bin_dir = None

            python_raw = tool_dict.get("python")
            python = python_raw if isinstance(python_raw, str) and python_raw else None

            requirements_raw = tool_dict.get("requirements", [])
            requirements = _parse_requirements(requirements_raw)

            package_source = _derive_package_source(
                requirements_raw if isinstance(requirements_raw, list) else []
            )

            return UvReceiptResult(
                receipt_path=receipt_path,
                tool_dir=tool_dir,
                bin_dir=bin_dir,
                is_default_tool_dir=is_default_tool_dir,
                is_default_bin_dir=is_default_bin_dir,
                python=python,
                requirements=requirements,
                package_source=package_source,
            )
        except Exception:  # noqa: BLE001
            return _empty_result()

    @staticmethod
    def exists_for(exe_path: Path) -> bool:
        """Return True if a valid uv receipt exists for this executable.

        Used by the detect_runtime() detection chain as a light probe
        (does not parse the full receipt). Never raises (CHK032).
        """
        try:  # noqa: BLE001
            executable_parent = exe_path.parent
            if executable_parent.name.lower() not in {"bin", "scripts"}:
                return False
            tool_env = executable_parent.parent
            receipt_path = tool_env / "uv-receipt.toml"
            if not receipt_path.exists():
                return False
            # Light validation: check that spec-kitty-cli appears in requirements
            content = receipt_path.read_text(encoding="utf-8")
            receipt = tomllib.loads(content)
            requirements = receipt.get("tool", {}).get("requirements", [])
            if isinstance(requirements, list):
                for req in requirements:
                    if isinstance(req, dict) and req.get("name") == _PACKAGE_NAME:
                        return True
            return False
        except Exception:  # noqa: BLE001
            return False
