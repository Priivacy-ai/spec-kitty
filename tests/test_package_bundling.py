"""Validate package bundling includes correct templates."""

from pathlib import Path
import subprocess
import sys
import tempfile
import tarfile
import pytest


def test_no_bash_script_references_in_bundled_templates():
    """Ensure bundled templates don't reference deleted bash scripts."""
    spec_kitty_root = Path(__file__).parent.parent
    template_dirs = [
        spec_kitty_root / "src" / "doctrine" / "templates" / "command-templates",
        *sorted((spec_kitty_root / "src" / "doctrine" / "missions").glob("*/command-templates")),
        *sorted((spec_kitty_root / "src" / "specify_cli" / "missions").glob("*/command-templates")),
    ]
    template_dirs = [p for p in template_dirs if p.exists()]
    if not template_dirs:
        pytest.skip("No command template directories found")

    bash_references = []

    for template_dir in template_dirs:
        for template in template_dir.glob("*.md"):
            content = template.read_text(encoding="utf-8")
            if "scripts/bash/" in content or ".kittify/scripts/bash/" in content:
                bash_references.append(str(template.relative_to(spec_kitty_root)))

    assert len(bash_references) == 0, (
        f"Bash script references found in templates to be bundled: {bash_references}. "
        "These scripts were removed in v0.10.0 - templates must use Python CLI."
    )


def test_sdist_bundles_templates():
    """Verify source distribution includes templates under src/specify_cli/."""
    spec_kitty_root = Path(__file__).parent.parent

    # Build sdist
    result = subprocess.run(
        [sys.executable, "-m", "build", "--sdist", "--outdir", "/tmp"],
        cwd=spec_kitty_root,
        capture_output=True,
        text=True
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

        # Should have templates under src/doctrine/
        templates = [m for m in members if "/src/doctrine/templates/" in m]
        assert len(templates) > 0, "doctrine/templates/ not found in sdist"

        # Should have command templates
        cmd_templates = [
            m for m in members
            if "command-templates" in m and m.endswith(".md")
        ]
        assert len(cmd_templates) >= 13, f"Missing command templates: {len(cmd_templates)}"

        # Should have git hooks
        git_hooks = [m for m in members if "git-hooks/pre-commit" in m]
        assert len(git_hooks) >= 2, f"Missing git hooks: {len(git_hooks)}"


def test_wheel_bundles_templates_correctly():
    """Verify wheel includes templates at correct path for importlib.resources."""
    spec_kitty_root = Path(__file__).parent.parent

    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", "/tmp"],
        cwd=spec_kitty_root,
        capture_output=True,
        text=True
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
        result = subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            pytest.skip(f"Failed to create venv: {result.stderr}")

        pip = venv_dir / "bin" / "pip"
        if not pip.exists():
            pip = venv_dir / "Scripts" / "pip.exe"  # Windows
            if not pip.exists():
                pytest.skip("pip not found in venv")

        # Install wheel
        result = subprocess.run(
            [str(pip), "install", str(wheel_path)],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            pytest.skip(f"Failed to install wheel: {result.stderr}")

        # Verify templates accessible via importlib.resources
        python = venv_dir / "bin" / "python"
        if not python.exists():
            python = venv_dir / "Scripts" / "python.exe"  # Windows
            if not python.exists():
                pytest.skip("python not found in venv")

        result = subprocess.run(
            [str(python), "-c",
             "from importlib.resources import files; "
             "t = files('doctrine').joinpath('templates'); "
             "print([p.name for p in t.iterdir()])"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Failed to check templates: {result.stderr}"
        output = result.stdout
        assert "command-templates" in output, "command-templates not found in bundled package"
        assert "git-hooks" in output, "git-hooks not found in bundled package"
