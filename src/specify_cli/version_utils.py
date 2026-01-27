"""Version detection utilities for spec-kitty CLI."""

from pathlib import Path
from typing import Optional
import re


def read_version_from_pyproject() -> Optional[str]:
    """Read version from pyproject.toml as fallback.

    Returns:
        Version string if found, None otherwise
    """
    try:
        # Find pyproject.toml relative to this file
        package_root = Path(__file__).parent.parent.parent
        pyproject_path = package_root / "pyproject.toml"

        if not pyproject_path.exists():
            return None

        content = pyproject_path.read_text()

        # Match: version = "X.Y.Z"
        pattern = re.compile(r'^\s*version\s*=\s*"(\d+\.\d+\.\d+[^"]*)"', re.MULTILINE)
        match = pattern.search(content)

        if match:
            return match.group(1)

        return None
    except Exception:
        # Any error reading file -> return None
        return None


def get_version() -> str:
    """Get spec-kitty version with smart fallback strategy.

    Priority:
    1. importlib.metadata (standard for installed packages)
    2. pyproject.toml (fallback for editable installs)
    3. "0.0.0-dev" (last resort if both fail)

    Returns:
        Version string
    """
    # Try importlib.metadata first (best practice)
    try:
        from importlib.metadata import version as get_metadata_version
        return get_metadata_version("spec-kitty-cli")
    except Exception:
        pass

    # Try reading from pyproject.toml (editable installs)
    pyproject_version = read_version_from_pyproject()
    if pyproject_version:
        return pyproject_version

    # Last resort fallback
    return "0.0.0-dev"
