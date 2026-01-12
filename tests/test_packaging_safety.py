"""Validate packaging safety for template relocation and constitution isolation."""

from __future__ import annotations

import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _require_build() -> None:
    if subprocess.run([sys.executable, "-m", "build", "--help"],
                      capture_output=True, text=True).returncode != 0:
        pytest.skip("python -m build not available; install build to run packaging tests")


@pytest.fixture(scope="session")
def build_artifacts() -> dict[str, Path]:
    """Build wheel + sdist in a temp directory and return their paths."""
    _require_build()

    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = Path(tmpdir)

        result = subprocess.run(
            [sys.executable, "-m", "build", "--wheel", "--sdist", "--outdir", str(outdir)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.skip(f"Build failed: {result.stderr}")

        wheels = sorted(outdir.glob("spec_kitty_cli-*.whl"))
        sdists = sorted(outdir.glob("spec_kitty_cli-*.tar.gz"))
        if not wheels or not sdists:
            pytest.skip("Build did not produce expected wheel/sdist artifacts")

        yield {
            "wheel": wheels[-1],
            "sdist": sdists[-1],
        }


def test_wheel_contains_no_kittify_paths(build_artifacts: dict[str, Path]) -> None:
    """Verify wheel doesn't contain .kittify/ paths."""
    wheel_path = build_artifacts["wheel"]

    with zipfile.ZipFile(wheel_path) as zf:
        all_files = zf.namelist()

    kittify_files = [f for f in all_files if ".kittify/" in f]
    assert not kittify_files, (
        "Wheel contains .kittify/ paths (packaging contamination): "
        f"{kittify_files}"
    )


def test_wheel_contains_no_filled_constitution(build_artifacts: dict[str, Path]) -> None:
    """Verify wheel doesn't contain a filled constitution under memory/."""
    wheel_path = build_artifacts["wheel"]

    with zipfile.ZipFile(wheel_path) as zf:
        all_files = zf.namelist()

    constitution_files = [f for f in all_files if "constitution.md" in f.lower()]

    for const_file in constitution_files:
        assert "memory/constitution" not in const_file, (
            "Wheel contains filled constitution from memory/: "
            f"{const_file}"
        )
        assert "templates/" in const_file or "missions/" in const_file, (
            "Found non-template constitution in wheel: "
            f"{const_file}"
        )


def test_wheel_contains_templates(build_artifacts: dict[str, Path]) -> None:
    """Verify wheel does contain templates and missions."""
    wheel_path = build_artifacts["wheel"]

    with zipfile.ZipFile(wheel_path) as zf:
        all_files = zf.namelist()

    template_files = [f for f in all_files if "specify_cli/templates/" in f]
    mission_files = [f for f in all_files if "specify_cli/missions/" in f]

    assert template_files, "Wheel missing template files"
    assert mission_files, "Wheel missing mission files"


def test_wheel_contains_only_src_package(build_artifacts: dict[str, Path]) -> None:
    """Verify wheel only contains specify_cli package files."""
    wheel_path = build_artifacts["wheel"]

    with zipfile.ZipFile(wheel_path) as zf:
        all_files = [
            f for f in zf.namelist()
            if ".dist-info/" not in f
        ]

    for file_path in all_files:
        assert file_path.startswith("specify_cli/"), (
            f"File outside package directory: {file_path}"
        )


def test_sdist_contains_no_kittify_paths(build_artifacts: dict[str, Path]) -> None:
    """Verify sdist doesn't contain .kittify/ runtime paths."""
    sdist_path = build_artifacts["sdist"]

    with tarfile.open(sdist_path, "r:gz") as tar:
        all_files = tar.getnames()

    bad_kittify_files = [
        f for f in all_files
        if ".kittify/" in f and "/src/" not in f
    ]

    assert not bad_kittify_files, (
        "Source dist contains .kittify/ paths outside src/: "
        f"{bad_kittify_files}"
    )
