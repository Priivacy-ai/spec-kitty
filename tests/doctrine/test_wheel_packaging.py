"""Wheel packaging smoke tests for doctrine distribution assets."""

from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path

import pytest

pytestmark = [pytest.mark.slow, pytest.mark.non_sandbox, pytest.mark.corpus]  # non_sandbox: builds and installs a wheel (>30s)
# These tests reuse the session-scoped build_artifacts and installed_wheel_venv
# fixtures from tests/cross_cutting/packaging/conftest.py.
# They are discovered via conftest.py fixture resolution because pytest
# collects fixtures from all conftest.py files in the test tree.
#
# If these fixtures are NOT found, it means this test file is being run
# in isolation. Use the fallback fixtures below.

REPO_ROOT = Path(__file__).resolve().parents[2]
# Pre-move built-in home: before mission relocate-builtin-doctrine-packs-01KYT87F the
# shipped pack content rode inside the ``doctrine`` package at
# ``doctrine/<kind>/built-in/``. The move relocated it to the top-level ``packs/``
# tree (wheel path ``packs/built-in/<kind>/``), so that old in-package home must now
# be ABSENT from the wheel — the inverse of the pre-move assertion, which required
# the built-in assets to ship under ``doctrine/``.
LEGACY_BUILTIN_DIR = "doctrine/" + "agent_profiles" + "/built-in/"


def _build_wheel_fallback(tmpdir: str) -> Path:
    """Fallback wheel builder for when conftest fixtures are not available."""
    result = subprocess.run(
        [__import__("sys").executable, "-m", "build", "--wheel", "--outdir", tmpdir],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"Wheel build failed: {result.stderr}")

    wheels = sorted(Path(tmpdir).glob("spec_kitty_cli-*.whl"))
    if not wheels:
        pytest.skip("No wheel generated")
    return wheels[-1]


@pytest.fixture
def wheel_path(build_artifacts: dict[str, Path]) -> Path:
    """Get wheel path from shared session fixture."""
    return build_artifacts["wheel"]


def test_wheel_contains_doctrine_package_data(wheel_path: Path) -> None:
    """Built wheel should include doctrine code and shipped YAML assets."""
    with zipfile.ZipFile(wheel_path, "r") as zf:
        names = set(zf.namelist())

    required_prefixes = [
        # Code + schemas stay inside the ``doctrine`` package.
        "doctrine/agent_profiles/profile.py",
        "doctrine/schemas/agent-profile.schema.yaml",
        "doctrine/schemas/directive.schema.yaml",
        # Relocated built-in pack content ships under the flattened top-level
        # ``packs/built-in/<kind>/`` tree (mission relocate-builtin-doctrine-packs-01KYT87F).
        # NOTE: the inner ``built-in`` segment of the pre-move layout is dropped.
        "packs/built-in/agent_profiles/implementer-ivan.agent.yaml",
        "packs/built-in/directives/003-decision-documentation-requirement.directive.yaml",
    ]
    missing = [path for path in required_prefixes if path not in names]
    assert not missing, f"Missing doctrine wheel assets: {missing}"
    legacy_paths = sorted(name for name in names if name.startswith(LEGACY_BUILTIN_DIR))
    assert legacy_paths == [], f"Pre-move {LEGACY_BUILTIN_DIR} wheel assets should be absent: {legacy_paths}"


def test_wheel_install_imports_doctrine_and_lists_profiles(
    installed_wheel_venv: dict[str, Path],
) -> None:
    """Installed wheel should expose doctrine imports and shipped profiles."""
    python = installed_wheel_venv["python"]

    check = subprocess.run(
        [
            str(python),
            "-c",
            (
                "from doctrine.agent_profiles import AgentProfileRepository; "
                "repo = AgentProfileRepository(project_dir=None); "
                "profiles = repo.list_all(); "
                "assert any(p.profile_id == 'implementer-ivan' for p in profiles); "
                "print(len(profiles))"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert check.returncode == 0, check.stderr
