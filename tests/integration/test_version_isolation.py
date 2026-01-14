"""Integration tests for version isolation in test environment.

These tests verify that the test infrastructure properly isolates tests
from host system's installed spec-kitty-cli package, preventing version
mismatch errors that can cause spurious test failures.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tests.test_isolation_helpers import (
    assert_test_isolation,
    get_installed_version,
    get_source_version,
)


def test_source_version_is_readable():
    """Verify we can read version from pyproject.toml."""
    version = get_source_version()
    assert version
    assert version != "unknown"
    # Should be semantic version format (at least X.Y)
    parts = version.split(".")
    assert len(parts) >= 2, f"Version {version} doesn't look like semantic versioning"
    # First part should be a number
    assert parts[0].isdigit(), f"Major version {parts[0]} is not a number"


def test_installed_version_matches_or_absent():
    """Verify installed version matches source or is absent.

    This test catches the common developer mistake of having an
    outdated pip-installed version that conflicts with source code.
    """
    source = get_source_version()
    installed = get_installed_version()

    if installed is not None:
        assert installed == source, (
            f"Installed version {installed} doesn't match source {source}. "
            f"This will cause test failures. Run: pip uninstall spec-kitty-cli -y"
        )


def test_cli_uses_source_version(run_cli, test_project):
    """Verify CLI reports source version, not installed version."""
    result = run_cli(test_project, "--version")

    assert result.returncode == 0, (
        f"--version command failed: {result.stderr}"
    )

    output = result.stdout.strip()
    source_version = get_source_version()

    assert source_version in output, (
        f"CLI reported '{output}' but source version is {source_version}"
    )


def test_version_checker_respects_test_mode(test_project, isolated_env):
    """Verify version checker respects SPEC_KITTY_TEST_MODE.

    This test simulates what happens when CLI checks version internally,
    ensuring test mode enforcement works correctly.
    """
    from tests.test_isolation_helpers import get_venv_python

    # Script that imports and calls get_cli_version()
    script = """
import os
import sys

# Add source to path (simulating test environment)
sys.path.insert(0, os.environ.get('PYTHONPATH'))

from specify_cli.core.version_checker import get_cli_version

version = get_cli_version()
print(version)
"""

    result = subprocess.run(
        [str(get_venv_python()), "-c", script],
        capture_output=True,
        text=True,
        env=isolated_env,
    )

    assert result.returncode == 0, (
        f"Version checker failed in test mode: {result.stderr}"
    )

    reported_version = result.stdout.strip()
    expected_version = isolated_env["SPEC_KITTY_CLI_VERSION"]

    assert reported_version == expected_version, (
        f"Version checker returned {reported_version} "
        f"but expected {expected_version} from environment"
    )


def test_test_mode_requires_version_override(test_project):
    """Verify test mode fails if SPEC_KITTY_CLI_VERSION is not set.

    This ensures test mode enforcement works - it should raise an error
    if the fixture setup is broken.
    """
    import os
    from tests.test_isolation_helpers import get_venv_python, REPO_ROOT

    env = os.environ.copy()
    env["SPEC_KITTY_TEST_MODE"] = "1"
    # Deliberately don't set SPEC_KITTY_CLI_VERSION
    # Set PYTHONPATH to source so it can import
    env["PYTHONPATH"] = str(REPO_ROOT / "src")

    script = """
import os
import sys
sys.path.insert(0, os.environ.get('PYTHONPATH', ''))

from specify_cli.core.version_checker import get_cli_version

try:
    version = get_cli_version()
    print(f"UNEXPECTED_SUCCESS:{version}")
except RuntimeError as e:
    print(f"EXPECTED_ERROR:{e}")
"""

    result = subprocess.run(
        [str(get_venv_python()), "-c", script],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(test_project),
    )

    # Should have an error message about missing SPEC_KITTY_CLI_VERSION
    assert "EXPECTED_ERROR" in result.stdout, (
        f"Test mode should fail without SPEC_KITTY_CLI_VERSION, "
        f"but got: {result.stdout}"
    )
    assert "SPEC_KITTY_CLI_VERSION" in result.stdout


def test_subprocess_inherits_isolation(run_cli, test_project):
    """Verify subprocesses spawned by CLI inherit isolation.

    Tests that environment variables propagate through to child
    processes, maintaining isolation throughout the call chain.
    """
    # Run a command that triggers version checking
    # 'mission list' should check version unless it's a skip command
    result = run_cli(test_project, "mission", "list")

    # Should not fail with version mismatch error
    assert "Version Mismatch" not in result.stdout
    assert "Version Mismatch" not in result.stderr

    # Should succeed (missions should be available in test_project)
    assert result.returncode == 0, (
        f"mission list failed: {result.stderr}"
    )


def test_isolated_env_has_required_variables(isolated_env):
    """Verify isolated_env fixture sets all required environment variables."""
    required_vars = {
        "PYTHONPATH",
        "SPEC_KITTY_CLI_VERSION",
        "SPEC_KITTY_TEST_MODE",
        "SPEC_KITTY_TEMPLATE_ROOT",
    }

    for var in required_vars:
        assert var in isolated_env, (
            f"isolated_env fixture missing required variable: {var}"
        )
        assert isolated_env[var], (
            f"isolated_env fixture has empty value for: {var}"
        )

    # Verify TEST_MODE is set to "1"
    assert isolated_env["SPEC_KITTY_TEST_MODE"] == "1"

    # Verify CLI version matches source
    source_version = get_source_version()
    assert isolated_env["SPEC_KITTY_CLI_VERSION"] == source_version


@pytest.mark.parametrize("command", [
    ["init", "--help"],
    ["upgrade", "--help"],
    ["specify", "--help"],
    ["mission", "list"],
])
def test_commands_work_with_isolation(run_cli, test_project, command):
    """Verify various commands work with isolated environment.

    This is a regression test - commands should work correctly
    when test isolation is in place.
    """
    result = run_cli(test_project, *command)

    # Should not crash with version errors
    assert "Version Mismatch" not in result.stdout
    assert "Version Mismatch" not in result.stderr
    assert "SPEC_KITTY_TEST_MODE" not in result.stdout  # Internal detail
    assert "SPEC_KITTY_TEST_MODE" not in result.stderr


def test_parallel_test_execution_isolated(tmp_path):
    """Verify multiple concurrent test runs don't interfere.

    This simulates pytest-xdist or multiple test runners running
    simultaneously. Each should maintain independent isolation.
    """
    from tests.test_isolation_helpers import REPO_ROOT, get_venv_python

    script = f"""
import sys
import os
from pathlib import Path

# Simulate test setup
repo_root = Path("{REPO_ROOT}")
sys.path.insert(0, str(repo_root / "src"))

# Set test mode with fake version
os.environ["SPEC_KITTY_TEST_MODE"] = "1"
os.environ["SPEC_KITTY_CLI_VERSION"] = "99.99.99"  # Fake test version

from specify_cli.core.version_checker import get_cli_version

version = get_cli_version()
assert version == "99.99.99", f"Expected 99.99.99, got {{version}}"
print("PASS")
"""

    script_path = tmp_path / "test_parallel.py"
    script_path.write_text(script, encoding="utf-8")

    # Run multiple instances in parallel
    processes = []
    for i in range(3):
        p = subprocess.Popen(
            [str(get_venv_python()), str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        processes.append((i, p))

    # Wait for all to complete
    for i, p in processes:
        stdout, stderr = p.communicate()
        assert p.returncode == 0, (
            f"Process {i} failed with: {stderr}"
        )
        assert "PASS" in stdout, (
            f"Process {i} didn't output PASS: {stdout}"
        )


def test_version_mismatch_detection_in_regular_mode():
    """Verify version mismatch is properly detected outside test mode.

    This test verifies the normal version checking logic still works
    when NOT in test mode.
    """
    from specify_cli.core.version_checker import compare_versions

    # Test various comparison scenarios
    result, mismatch_type = compare_versions("0.10.0", "0.9.0")
    assert result == 1  # CLI newer
    assert mismatch_type == "cli_newer"

    result, mismatch_type = compare_versions("0.9.0", "0.10.0")
    assert result == -1  # CLI older
    assert mismatch_type == "project_newer"

    result, mismatch_type = compare_versions("0.10.0", "0.10.0")
    assert result == 0  # Match
    assert mismatch_type == "match"


def test_test_isolation_helper_function():
    """Verify assert_test_isolation() helper works correctly."""
    # This should pass if isolation is correct
    # (either no installed version, or installed matches source)
    try:
        assert_test_isolation()
    except pytest.fail.Exception as e:
        # If this fails, it means developer has mismatched installation
        pytest.fail(
            f"Test isolation check failed: {e}\n"
            f"This indicates a problem with your local environment. "
            f"Run: pip uninstall spec-kitty-cli -y"
        )
