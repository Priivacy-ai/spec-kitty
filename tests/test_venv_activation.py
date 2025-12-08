"""Tests for virtual environment activation functionality."""

import os
import subprocess
import tempfile
from pathlib import Path
import pytest


class TestBashVenvActivation:
    """Test venv activation in bash scripts."""

    def test_venv_activation_function_exists(self):
        """Verify the activate_repo_venv function exists in common.sh."""
        bash_common = Path("scripts/bash/common.sh")
        assert bash_common.exists(), "scripts/bash/common.sh not found"

        content = bash_common.read_text()
        assert "activate_repo_venv()" in content, "activate_repo_venv function not found"
        assert "VIRTUAL_ENV" in content, "VIRTUAL_ENV check not found"

    def test_bash_venv_activation_handles_worktree(self):
        """Test that bash venv activation handles .worktrees paths."""
        bash_common = Path("scripts/bash/common.sh")
        content = bash_common.read_text()

        # Check for worktree path handling
        assert ".worktrees" in content, "Worktree handling not found"
        assert ".venv" in content, ".venv path not found"

    def test_bash_venv_activation_with_existing_venv(self):
        """Test venv activation with actual .venv directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            venv_dir = repo_root / ".venv"
            venv_dir.mkdir()

            # Create mock activate script
            bin_dir = venv_dir / "bin"
            bin_dir.mkdir()
            activate_script = bin_dir / "activate"
            activate_script.write_text("# Mock activate script\n")

            # Source common.sh and test activation
            bash_script = f"""
            source scripts/bash/common.sh

            # Mock get_repo_root to return our temp directory
            get_repo_root() {{ echo "{repo_root}"; }}

            # Unset VIRTUAL_ENV to test activation
            unset VIRTUAL_ENV

            # Call activation function
            activate_repo_venv

            # Check if VIRTUAL_ENV was set
            if [[ -n "$VIRTUAL_ENV" ]]; then
                echo "SUCCESS: VIRTUAL_ENV set"
            else
                echo "FAIL: VIRTUAL_ENV not set"
            fi
            """

            result = subprocess.run(
                ["bash", "-c", bash_script],
                cwd=Path.cwd(),
                capture_output=True,
                text=True
            )

            assert "SUCCESS" in result.stdout or "Activating" in result.stdout, \
                f"venv activation failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"

    def test_bash_venv_activation_skips_if_already_active(self):
        """Test that venv activation skips if already in a virtual environment."""
        bash_script = """
        source scripts/bash/common.sh

        # Mock get_repo_root
        get_repo_root() { echo "/fake/repo"; }

        # Set VIRTUAL_ENV to simulate already being in a venv
        export VIRTUAL_ENV=/fake/venv

        # Call activation function
        activate_repo_venv

        # Verify VIRTUAL_ENV unchanged
        echo "$VIRTUAL_ENV"
        """

        result = subprocess.run(
            ["bash", "-c", bash_script],
            cwd=Path.cwd(),
            capture_output=True,
            text=True
        )

        assert "/fake/venv" in result.stdout, "VIRTUAL_ENV was modified when already set"


class TestPowerShellVenvActivation:
    """Test venv activation in PowerShell scripts."""

    def test_powershell_venv_activation_function_exists(self):
        """Verify the Activate-RepoVenv function exists in common.ps1."""
        ps_common = Path("scripts/powershell/common.ps1")
        assert ps_common.exists(), "scripts/powershell/common.ps1 not found"

        content = ps_common.read_text()
        assert "Activate-RepoVenv" in content, "Activate-RepoVenv function not found"
        assert "$env:VIRTUAL_ENV" in content, "VIRTUAL_ENV check not found"

    def test_powershell_venv_function_has_documentation(self):
        """Verify PowerShell function has proper documentation."""
        ps_common = Path("scripts/powershell/common.ps1")
        content = ps_common.read_text()

        # Check for PowerShell help syntax
        assert "#" in content, "Comments not found"
        assert ".SYNOPSIS" in content, "SYNOPSIS not found"
        assert ".DESCRIPTION" in content, "DESCRIPTION not found"

    def test_powershell_venv_activation_no_auto_call(self):
        """Verify venv activation is not auto-called at module level."""
        ps_common = Path("scripts/powershell/common.ps1")
        content = ps_common.read_text()

        # Should not have auto-call at bottom
        lines = content.strip().split('\n')
        last_line = lines[-1].strip() if lines else ""

        assert "Activate-RepoVenv" not in last_line, \
            "Auto-call to Activate-RepoVenv found - should be explicit"
        assert "}" in last_line or not last_line, \
            "Last line should be end of function or empty"

    def test_powershell_venv_handles_worktree(self):
        """Test that PowerShell venv activation handles .worktrees paths."""
        ps_common = Path("scripts/powershell/common.ps1")
        content = ps_common.read_text()

        # Check for worktree path handling
        assert ".worktrees" in content, "Worktree handling not found"
        assert "IndexOf" in content, "Path manipulation not found"


class TestVenvActivationIntegration:
    """Integration tests for venv activation."""

    def test_venv_activation_functions_parity(self):
        """Verify bash and PowerShell venv functions have feature parity."""
        bash_common = Path("scripts/bash/common.sh")
        ps_common = Path("scripts/powershell/common.ps1")

        bash_content = bash_common.read_text()
        ps_content = ps_common.read_text()

        # Check that both handle the same scenarios
        for script, content, name in [
            (bash_common, bash_content, "bash"),
            (ps_common, ps_content, "PowerShell")
        ]:
            assert "VIRTUAL_ENV" in content, f"{name}: VIRTUAL_ENV check missing"
            assert ".venv" in content, f"{name}: .venv path missing"
            assert ".worktrees" in content, f"{name}: worktree handling missing"

    def test_repo_structure_has_venv_support(self):
        """Verify repo can support virtual environment activation."""
        # Check that scripts directory exists
        assert Path("scripts/bash/common.sh").exists()
        assert Path("scripts/powershell/common.ps1").exists()

        # Check that functions are properly defined
        bash_content = Path("scripts/bash/common.sh").read_text()
        ps_content = Path("scripts/powershell/common.ps1").read_text()

        assert "activate_repo_venv" in bash_content
        assert "Activate-RepoVenv" in ps_content
