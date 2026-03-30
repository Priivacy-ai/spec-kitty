"""Validate package bundling includes correct templates."""

from pathlib import Path
import subprocess
import sys
import tempfile
import tarfile
import pytest


def test_command_templates_not_bundled():
    """WP10: command-templates directories must not exist in src/specify_cli or src/doctrine.

    Shim generation (spec-kitty agent shim) replaces rendered template files.
    No command-templates should remain to be bundled into the distribution.

    Exception: src/specify_cli/missions/software-dev/command-templates/ is
    intentionally retained as the canonical source for prompt-driven commands
    (restored in feature 058).
    """
    spec_kitty_root = Path(__file__).parent.parent.parent.parent
    missions_dir = spec_kitty_root / "src" / "specify_cli" / "missions"

    # software-dev/command-templates/ is the canonical source for prompt-driven
    # commands and is intentionally kept (feature 058).
    allowed = {
        str((missions_dir / "software-dev" / "command-templates").relative_to(spec_kitty_root)),
    }

    found = []
    for base in [
        spec_kitty_root / "src" / "specify_cli",
        spec_kitty_root / "src" / "doctrine",
    ]:
        if base.exists():
            for d in base.rglob("command-templates"):
                if d.is_dir():
                    rel = str(d.relative_to(spec_kitty_root))
                    if rel not in allowed:
                        found.append(rel)

    assert len(found) == 0, (
        f"command-templates directories still present (WP10 deletion incomplete): {found}"
    )


def test_sdist_bundles_templates():
    """Verify source distribution includes templates under src/specify_cli/."""
    spec_kitty_root = Path(__file__).parent.parent.parent.parent

    # Build sdist
    result = subprocess.run(
        [sys.executable, "-m", "build", "--sdist", "--outdir", "/tmp"],
        cwd=spec_kitty_root,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        pytest.skip(f"Build failed (build module may not be installed): {result.stderr}")

    # Find the tarball
    dist_dir = Path("/tmp")
    tarballs = list(dist_dir.glob("spec-kitty-cli-*.tar.gz"))

    if len(tarballs) == 0:
        pytest.skip("No sdist tarball found")

    latest = max(tarballs, key=lambda p: p.stat().st_mtime)

    # Extract and check contents
    with tarfile.open(latest, "r:gz") as tar:
        members = tar.getnames()

        # Should have templates under src/specify_cli/
        templates = [m for m in members if "/src/specify_cli/templates/" in m]
        assert len(templates) > 0, "specify_cli/templates/ not found in sdist"

        # WP10: command-templates must NOT be in sdist (deleted in favour of shims)
        cmd_templates = [m for m in members if "command-templates" in m and m.endswith(".md")]
        assert len(cmd_templates) == 0, (
            f"command-templates found in sdist (WP10 deletion incomplete): {cmd_templates[:5]}"
        )

        # Git hooks are intentionally not bundled in 2.x
        git_hooks = [m for m in members if "git-hooks/" in m]
        assert len(git_hooks) == 0, f"Unexpected git hook assets bundled: {git_hooks}"


def test_wheel_bundles_templates_correctly():
    """Verify wheel includes templates and doctrine skills for importlib.resources."""
    spec_kitty_root = Path(__file__).parent.parent.parent.parent

    result = subprocess.run(
        [sys.executable, "-m", "build", "--outdir", "/tmp"],
        cwd=spec_kitty_root,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        pytest.skip(f"Build failed (build module may not be installed): {result.stderr}")

    # Find the wheel
    wheel_files = list(Path("/tmp").glob("spec_kitty_cli-*.whl"))
    if len(wheel_files) == 0:
        pytest.skip("No wheel file found")

    wheel_path = max(wheel_files, key=lambda p: p.stat().st_mtime)

    # Install wheel to temp venv and verify
    with tempfile.TemporaryDirectory() as tmpdir:
        venv_dir = Path(tmpdir) / "venv"

        # Create venv
        result = subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], capture_output=True, text=True)
        if result.returncode != 0:
            pytest.skip(f"Failed to create venv: {result.stderr}")

        pip = venv_dir / "bin" / "pip"
        if not pip.exists():
            pip = venv_dir / "Scripts" / "pip.exe"  # Windows
            if not pip.exists():
                pytest.skip("pip not found in venv")

        # Install wheel
        result = subprocess.run([str(pip), "install", str(wheel_path)], capture_output=True, text=True)
        if result.returncode != 0:
            pytest.skip(f"Failed to install wheel: {result.stderr}")

        # Verify templates accessible via importlib.resources
        python = venv_dir / "bin" / "python"
        if not python.exists():
            python = venv_dir / "Scripts" / "python.exe"  # Windows
            if not python.exists():
                pytest.skip("python not found in venv")

        result = subprocess.run(
            [
                str(python),
                "-c",
                "from importlib.resources import files; "
                "t = files('specify_cli').joinpath('templates'); "
                "print(list(t.iterdir()))",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Failed to check templates: {result.stderr}"
        output = result.stdout
        # WP10: command-templates were deleted — shims replace them
        assert "command-templates" not in output, (
            "command-templates should NOT be in bundled package (deleted in WP10)"
        )
        assert "git-hooks" not in output, "git-hooks should not be bundled in 2.x"

        result = subprocess.run(
            [
                str(python),
                "-c",
                "from importlib.resources import files; "
                "skill = files('doctrine').joinpath('skills', 'spec-kitty-setup-doctor', 'SKILL.md'); "
                "print(skill.is_file())",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Failed to check bundled doctrine skills: {result.stderr}"
        assert result.stdout.strip() == "True", "Bundled canonical skill missing from wheel"

        result = subprocess.run(
            [
                str(python),
                "-c",
                "from importlib.resources import files; "
                "fixture = files('doctrine').joinpath('curation', 'imports', 'example-zombies', 'manifest.yaml'); "
                "print(fixture.is_file())",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Failed to check bundled doctrine import fixtures: {result.stderr}"
        assert result.stdout.strip() == "True", "Bundled doctrine import fixture missing from wheel"
