"""Shared build utilities for Spec Kitty plugin bundle projectors.

Provides :class:`BuildError` and helper functions used by both the Claude Code
and Codex bundle projectors.  All helpers are pure (no network / install / publish
side-effects).

**Scope guard (FR-016, C-006):** Nothing in this module installs, registers,
enables, or publishes a bundle.  All filesystem writes are confined to the
staging ``output_dir`` supplied by the caller.
"""

from __future__ import annotations

import importlib.metadata
import json
import re
from pathlib import Path

# Minimum number of canonical command skills required in a complete bundle.
MIN_SKILL_COUNT = 15

# Semver pattern: MAJOR.MINOR.PATCH (patch may include pre-release suffix).
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+")

# Package name registered on PyPI / importlib.metadata.
_PACKAGE_NAME = "spec-kitty-cli"

# Fallback version emitted when the package metadata is unavailable (e.g.
# during editable / source-tree installs).
_VERSION_FALLBACK = "0.0.0+dev"


def get_cli_version() -> str:
    """Return the installed version of the ``spec-kitty-cli`` package.

    Falls back to :data:`_VERSION_FALLBACK` when the package metadata cannot
    be found (e.g. editable installs that have not been re-registered).  The
    caller is responsible for emitting a warning when the fallback is used.
    """
    try:
        return importlib.metadata.version(_PACKAGE_NAME)
    except importlib.metadata.PackageNotFoundError:
        return _VERSION_FALLBACK


def is_semver(version: str) -> bool:
    """Return ``True`` when *version* matches ``MAJOR.MINOR.PATCH`` (loose)."""
    return bool(_SEMVER_RE.match(version))


def write_json(path: Path, payload: dict[str, object]) -> None:
    """Write *payload* as pretty-printed JSON to *path* (creates parents)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


class BuildError(Exception):
    """Raised when a plugin bundle build step fails with a clear user message."""
