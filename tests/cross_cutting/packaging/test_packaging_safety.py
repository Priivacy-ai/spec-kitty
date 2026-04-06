"""Validate packaging safety for template relocation and charter isolation."""

from __future__ import annotations

import tarfile
import zipfile
from pathlib import Path

import pytest


# build_artifacts fixture comes from conftest.py (session-scoped, shared)


@pytest.mark.slow
def test_wheel_contains_no_kittify_paths(build_artifacts: dict[str, Path]) -> None:
    """Verify wheel doesn't contain .kittify/ paths."""
    wheel_path = build_artifacts["wheel"]

    with zipfile.ZipFile(wheel_path) as zf:
        all_files = zf.namelist()

    kittify_files = [f for f in all_files if ".kittify/" in f]
    assert not kittify_files, f"Wheel contains .kittify/ paths (packaging contamination): {kittify_files}"


@pytest.mark.slow
def test_wheel_contains_no_filled_charter(build_artifacts: dict[str, Path]) -> None:
    """Verify wheel doesn't contain a filled charter under memory/."""
    wheel_path = build_artifacts["wheel"]

    with zipfile.ZipFile(wheel_path) as zf:
        all_files = zf.namelist()

    charter_files = [f for f in all_files if "charter.md" in f.lower()]

    for const_file in charter_files:
        assert "memory/charter" not in const_file, f"Wheel contains filled charter from memory/: {const_file}"
        assert "templates/" in const_file or "missions/" in const_file, (
            f"Found non-template charter in wheel: {const_file}"
        )


@pytest.mark.slow
def test_wheel_contains_templates(build_artifacts: dict[str, Path]) -> None:
    """Verify wheel does contain templates and missions."""
    wheel_path = build_artifacts["wheel"]

    with zipfile.ZipFile(wheel_path) as zf:
        all_files = zf.namelist()

    template_files = [f for f in all_files if "specify_cli/templates/" in f]
    mission_files = [f for f in all_files if "specify_cli/missions/" in f]

    assert template_files, "Wheel missing template files"
    assert mission_files, "Wheel missing mission files"


@pytest.mark.slow
def test_wheel_contains_only_known_packages(build_artifacts: dict[str, Path]) -> None:
    """Verify wheel only contains known package directories."""
    wheel_path = build_artifacts["wheel"]

    known_prefixes = ("specify_cli/", "doctrine/", "charter/", "kernel/")

    with zipfile.ZipFile(wheel_path) as zf:
        all_files = [f for f in zf.namelist() if ".dist-info/" not in f]

    for file_path in all_files:
        assert any(file_path.startswith(p) for p in known_prefixes), (
            f"File outside known package directories: {file_path}"
        )


@pytest.mark.slow
def test_sdist_contains_no_kittify_paths(build_artifacts: dict[str, Path]) -> None:
    """Verify sdist doesn't contain .kittify/ runtime paths."""
    sdist_path = build_artifacts["sdist"]

    with tarfile.open(sdist_path, "r:gz") as tar:
        all_files = tar.getnames()

    bad_kittify_files = [f for f in all_files if ".kittify/" in f and "/src/" not in f]

    assert not bad_kittify_files, f"Source dist contains .kittify/ paths outside src/: {bad_kittify_files}"
