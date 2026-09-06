"""Hatch build hook that pins source provenance into distribution artifacts."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

_REVISION_PATTERN = re.compile(r"^[0-9a-fA-F]{7,40}$")
_BUILD_INFO_RELATIVE_PATH = Path("src/specify_cli/_build_info.py")


def _normalize_revision(value: str | None) -> str | None:
    if value is None or not _REVISION_PATTERN.fullmatch(value):
        return None
    return value[:12].lower()


def _git_revision(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return _normalize_revision(result.stdout.strip())


def _existing_revision(path: Path) -> str | None:
    if not path.is_file():
        return None
    match = re.search(r'^BUILD_REVISION = "([0-9a-f]{7,40})"$', path.read_text(encoding="utf-8"), re.MULTILINE)
    return _normalize_revision(match.group(1)) if match else None


def resolve_build_revision(root: Path) -> str:
    """Resolve env, Git, or sdist-carried provenance in that order."""
    target = root / _BUILD_INFO_RELATIVE_PATH
    revision = _normalize_revision(os.environ.get("SPEC_KITTY_BUILD_REVISION"))
    revision = revision or _git_revision(root) or _existing_revision(target)
    if revision:
        return revision
    if os.environ.get("GITHUB_REF_TYPE") == "tag" or os.environ.get("RELEASE_TAG"):
        raise RuntimeError("release build has no valid source revision")
    return "unknown"


class CustomBuildHook(BuildHookInterface):
    """Generate build information just long enough for Hatch to package it."""

    def initialize(self, version: str, build_data: dict[str, object]) -> None:
        del version, build_data
        target = Path(self.root) / _BUILD_INFO_RELATIVE_PATH
        target.write_text(
            '"""Generated build provenance; do not edit."""\n\n'
            f'BUILD_REVISION = "{resolve_build_revision(Path(self.root))}"\n',
            encoding="utf-8",
        )

    def finalize(self, version: str, build_data: dict[str, object], artifact_path: str) -> None:
        del version, build_data, artifact_path
        (Path(self.root) / _BUILD_INFO_RELATIVE_PATH).unlink(missing_ok=True)
