"""Dogfood acceptance tests for T7.5 from WP07 mission 079-post-555-release-hardening.

These tests exercise the core spec-kitty CLI commands against the real repo.
They are gated behind SPEC_KITTY_DOGFOOD_TEST=1 to avoid running in normal CI
(they require the installed CLI and the full repo checkout).

To run:
    SPEC_KITTY_DOGFOOD_TEST=1 pytest tests/release/test_dogfood_command_set.py -v
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]

_DOGFOOD_ENABLED = os.environ.get("SPEC_KITTY_DOGFOOD_TEST") == "1"

pytestmark = pytest.mark.skipif(
    not _DOGFOOD_ENABLED,
    reason="Dogfood tests run only when SPEC_KITTY_DOGFOOD_TEST=1",
)


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )


def test_spec_kitty_version_exits_zero() -> None:
    """spec-kitty --version must exit 0."""
    result = _run(["spec-kitty", "--version"])
    assert result.returncode == 0, f"spec-kitty --version failed:\n{result.stdout}\n{result.stderr}"


def test_spec_kitty_version_no_mismatch_warning() -> None:
    """spec-kitty --version must not emit version skew warnings."""
    result = _run(["spec-kitty", "--version"])
    combined = (result.stdout + result.stderr).lower()
    assert "mismatch" not in combined, f"Version skew detected:\n{result.stderr}"


def test_agent_tasks_status_exits_zero() -> None:
    """spec-kitty agent tasks status --mission 079-... must exit 0."""
    result = _run(
        [
            "spec-kitty",
            "agent",
            "tasks",
            "status",
            "--mission",
            "079-post-555-release-hardening",
        ]
    )
    assert result.returncode == 0, f"agent tasks status failed:\n{result.stdout}\n{result.stderr}"


def test_validate_release_exits_zero() -> None:
    """validate_release.py must exit 0 on the working repo with synced versions."""
    import sys

    result = subprocess.run(
        [sys.executable, "scripts/release/validate_release.py"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"validate_release.py failed:\n{result.stdout}\n{result.stderr}"


def test_version_coherence() -> None:
    """pyproject.toml and .kittify/metadata.yaml must report the same version."""
    import tomllib
    import yaml  # type: ignore[import-untyped]

    with (_REPO_ROOT / "pyproject.toml").open("rb") as fh:
        pyproject_version = tomllib.load(fh)["project"]["version"]

    metadata = yaml.safe_load((_REPO_ROOT / ".kittify" / "metadata.yaml").read_text(encoding="utf-8"))
    metadata_version = metadata["spec_kitty"]["version"]

    assert pyproject_version == metadata_version, f"Version mismatch: pyproject.toml={pyproject_version!r} vs .kittify/metadata.yaml={metadata_version!r}"
