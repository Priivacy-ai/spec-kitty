"""Clean-install deferral state for the temporary #828 publication window."""

from __future__ import annotations

import tomllib
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_LOCK_FILE = _ROOT / "uv.lock"
_SHARED_PACKAGES = {"spec-kitty-events", "spec-kitty-tracker"}


def clean_install_acceptance_deferred() -> bool:
    lock = tomllib.loads(_LOCK_FILE.read_text(encoding="utf-8"))
    return any(package.get("name") in _SHARED_PACKAGES and "git" in package.get("source", {}) for package in lock.get("package", []))
