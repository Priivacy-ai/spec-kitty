"""Wheel packaging smoke tests for doctrine distribution assets."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

import pytest
pytestmark = pytest.mark.slow



REPO_ROOT = Path(__file__).resolve().parents[2]


def _build_wheel(tmpdir: str) -> Path:
    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", tmpdir],
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


def _venv_paths(venv_dir: Path) -> tuple[Path, Path]:
    pip = venv_dir / "bin" / "pip"
    python = venv_dir / "bin" / "python"

    if not pip.exists() or not python.exists():
        pip = venv_dir / "Scripts" / "pip.exe"
        python = venv_dir / "Scripts" / "python.exe"

    if not pip.exists() or not python.exists():
        pytest.skip("Unable to locate venv pip/python executables")

    return pip, python


def test_wheel_contains_doctrine_package_data() -> None:
    """Built wheel should include doctrine code and shipped YAML assets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        wheel = _build_wheel(tmpdir)

        with zipfile.ZipFile(wheel, "r") as zf:
            names = set(zf.namelist())

        required_prefixes = [
            "doctrine/agent_profiles/profile.py",
            "doctrine/agent_profiles/shipped/implementer.agent.yaml",
            "doctrine/schemas/agent-profile.schema.yaml",
            "doctrine/schemas/directive.schema.yaml",
            "doctrine/directives/shipped/003-decision-documentation-requirement.directive.yaml",
        ]
        missing = [path for path in required_prefixes if path not in names]
        assert not missing, f"Missing doctrine wheel assets: {missing}"


def test_wheel_install_imports_doctrine_and_lists_profiles() -> None:
    """Installed wheel should expose doctrine imports and shipped profiles."""
    with tempfile.TemporaryDirectory() as tmpdir:
        wheel = _build_wheel(tmpdir)

        venv_dir = Path(tmpdir) / "venv"
        create = subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            capture_output=True,
            text=True,
            check=False,
        )
        if create.returncode != 0:
            pytest.skip(f"venv creation failed: {create.stderr}")

        pip, python = _venv_paths(venv_dir)

        install = subprocess.run(
            [str(pip), "install", str(wheel)],
            capture_output=True,
            text=True,
            check=False,
        )
        if install.returncode != 0:
            pytest.skip(f"wheel install failed: {install.stderr}")

        check = subprocess.run(
            [
                str(python),
                "-c",
                (
                    "from doctrine.agent_profiles import AgentProfileRepository; "
                    "repo = AgentProfileRepository(project_dir=None); "
                    "profiles = repo.list_all(); "
                    "assert any(p.profile_id == 'implementer' for p in profiles); "
                    "print(len(profiles))"
                ),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        assert check.returncode == 0, check.stderr
