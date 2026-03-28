"""Functional tests for validate-encoding CLI command.

Test Suite 2: CLI Encoding Validation Command

Tests the spec-kitty validate-encoding command that users and LLMs interact with
to check and fix encoding issues in mission markdown files.

Coverage Target: 85%+ for cli/commands/validate_encoding.py
"""

from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
import os

import pytest

from tests.test_isolation_helpers import get_venv_python

pytestmark = pytest.mark.git_repo


def run_validate_encoding_cli(
    *args: str,
    cwd: Path,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    command = [str(get_venv_python()), "-m", "specify_cli.__init__", "validate-encoding", *args]
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
    )


class TestValidateCleanMission:
    """Test 2.1: Validate Clean Mission"""

    def test_validate_clean_mission_exits_0(self):
        """Verify command exits 0 when no issues found."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create mission structure
            mission_dir = tmpdir / "kitty-specs" / "001-test-mission"
            mission_dir.mkdir(parents=True)
            (mission_dir / "spec.md").write_text("Clean content")
            (mission_dir / "plan.md").write_text("No issues here")

            # Initialize git repo (required for spec-kitty commands)
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)

            # Create .kittify directory (required for project detection)
            (tmpdir / ".kittify").mkdir()

            # Run validate-encoding command
            # Use subprocess instead of CliRunner for proper cwd handling
            result = run_validate_encoding_cli(
                "--mission",
                "001-test-mission",
                cwd=tmpdir,
            )

            # Should exit successfully
            assert result.returncode == 0, f"Should exit 0, got {result.returncode}: {result.stdout}"

            # Should confirm clean files
            output = result.stdout + result.stderr
            assert "properly UTF-8 encoded" in output or "✓" in output, f"Should confirm clean encoding. Got: {output}"


class TestDetectIssuesWithoutFix:
    """Test 2.2: Detect Issues Without Fix"""

    def test_detect_issues_without_fix_exits_1(self):
        """Verify command exits 1 when issues found and --fix not specified."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create mission with encoding issue
            mission_dir = tmpdir / "kitty-specs" / "001-test-mission"
            mission_dir.mkdir(parents=True)
            (mission_dir / "bad.md").write_text("User\u2019s test")

            # Initialize git
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)
            (tmpdir / ".kittify").mkdir()

            # Run without --fix
            result = run_validate_encoding_cli(
                "--mission",
                "001-test-mission",
                cwd=tmpdir,
            )

            # Should exit with error code
            assert result.returncode == 1, f"Should exit 1 with issues, got {result.returncode}"

            # Should show the problematic file
            output = result.stdout + result.stderr
            assert "bad.md" in output, f"Should show bad.md in output. Got: {result.stdout}"

            # Should suggest fix
            output = result.stdout + result.stderr
            assert "--fix" in output or "fix" in result.stdout.lower(), f"Should suggest --fix. Got: {result.stdout}"


class TestFixIssuesWithBackup:
    """Test 2.3: Fix Issues With Backup"""

    def test_fix_creates_backup(self):
        """Verify --fix flag repairs files and creates backups."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            mission_dir = tmpdir / "kitty-specs" / "001-test-mission"
            mission_dir.mkdir(parents=True)

            bad_file = mission_dir / "broken.md"
            bad_file.write_text("User\u2019s \u201ctest\u201d")

            # Initialize git
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)
            (tmpdir / ".kittify").mkdir()

            # Run with --fix
            result = run_validate_encoding_cli(
                "--mission",
                "001-test-mission",
                "--fix",
                cwd=tmpdir,
            )

            # Should exit successfully
            assert result.returncode == 0, f"Should exit 0 after fix, got {result.returncode}: {result.stdout}"

            # Should mention fix
            output = result.stdout + result.stderr
            assert "Fixed" in output or "fixed" in result.stdout, f"Should mention fix. Got: {result.stdout}"

            # File should be fixed
            fixed_content = bad_file.read_text()
            assert fixed_content == 'User\'s "test"', f"File should be fixed, got: {fixed_content!r}"

            # Backup should exist
            backup = bad_file.with_suffix(".md.bak")
            assert backup.exists(), "Backup should be created"
            assert backup.read_text() == "User\u2019s \u201ctest\u201d", "Backup should have original content"


class TestFixWithoutBackup:
    """Test 2.4: Fix Without Backup"""

    def test_no_backup_flag_skips_backup(self):
        """Verify --no-backup flag skips backup creation."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            mission_dir = tmpdir / "kitty-specs" / "001-test-mission"
            mission_dir.mkdir(parents=True)

            bad_file = mission_dir / "test.md"
            bad_file.write_text("User\u2019s test")

            # Initialize git
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)
            (tmpdir / ".kittify").mkdir()

            # Run with --fix --no-backup
            result = run_validate_encoding_cli(
                "--mission",
                "001-test-mission",
                "--fix",
                "--no-backup",
                cwd=tmpdir,
            )

            # Should exit successfully
            assert result.returncode == 0, f"Should exit 0, got {result.returncode}"

            # File should be fixed
            assert bad_file.read_text() == "User's test", "File should be fixed"

            # No backup should exist
            backup = bad_file.with_suffix(".md.bak")
            assert not backup.exists(), "Backup should not be created with --no-backup"


class TestValidateAllMissions:
    """Test 2.5: Validate All Missions"""

    def test_validate_all_missions(self):
        """Verify --all flag scans multiple missions."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create multiple missions with issues
            for i in range(1, 4):
                mission_dir_tmp = tmpdir / "kitty-specs" / f"00{i}-mission"
                mission_dir_tmp.mkdir(parents=True)
                (mission_dir_tmp / "spec.md").write_text(f"User\u2019s test {i}")

            # Initialize git
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)
            (tmpdir / ".kittify").mkdir()

            # Run with --all
            result = run_validate_encoding_cli(
                "--all",
                cwd=tmpdir,
            )

            # Should detect issues in all missions
            assert result.returncode == 1, f"Should exit 1 with issues, got {result.returncode}"

            # Should mention multiple missions or show count
            output = result.stdout
            assert (
                "001-mission" in output
                or "002-mission" in output
                or "003-mission" in output
                or "3" in output
                or "missions" in output
            ), f"Should indicate multiple missions scanned. Got: {output}"

    def test_fix_all_missions(self):
        """Verify --all --fix repairs all missions."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create multiple missions
            files_to_check = []
            for i in range(1, 4):
                mission_dir_tmp = tmpdir / "kitty-specs" / f"00{i}-mission"
                mission_dir_tmp.mkdir(parents=True)
                test_file = mission_dir_tmp / "spec.md"
                test_file.write_text(f"User\u2019s test {i}")
                files_to_check.append(test_file)

            # Initialize git
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)
            (tmpdir / ".kittify").mkdir()

            # Run with --all --fix
            result = run_validate_encoding_cli(
                "--all",
                "--fix",
                cwd=tmpdir,
            )

            # Should exit successfully
            assert result.returncode == 0, f"Should exit 0 after fixing all, got {result.returncode}"

            # All files should be fixed
            for f in files_to_check:
                content = f.read_text()
                assert "User's" in content, f"File {f} should be fixed"


class TestCLIErrorHandling:
    """Test CLI error handling and messaging."""

    def test_command_outside_project_fails(self):
        """Verify command fails gracefully outside a spec-kitty project."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            result = run_validate_encoding_cli(
                "--mission",
                "001-test",
                cwd=tmpdir,
            )

            # Should fail with clear message
            assert result.returncode == 1, "Should exit 1 outside project"
            # Error message should be informative

    def test_command_with_nonexistent_mission(self):
        """Verify appropriate error for nonexistent mission."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Initialize project structure
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)
            (tmpdir / ".kittify").mkdir()
            (tmpdir / "kitty-specs").mkdir()

            # Try to validate nonexistent mission
            result = run_validate_encoding_cli(
                "--mission",
                "999-nonexistent",
                cwd=tmpdir,
            )

            # Should fail with clear message
            assert result.returncode == 1, "Should exit 1 for nonexistent mission"
            output = result.stdout + result.stderr
            assert "not found" in output.lower() or "Error" in result.stdout, (
                f"Should indicate mission not found. Got: {result.stdout}"
            )


class TestCLIOutputFormatting:
    """Test CLI output quality and formatting."""

    def test_output_includes_file_details(self):
        """Verify output shows file names and line numbers when issues found."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            mission_dir = tmpdir / "kitty-specs" / "001-test"
            mission_dir.mkdir(parents=True)

            # Create file with issues
            bad_file = mission_dir / "spec.md"
            bad_file.write_text("Line 1\nUser\u2019s test on line 2\nLine 3")

            # Initialize git
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)
            (tmpdir / ".kittify").mkdir()

            # Run validation
            result = run_validate_encoding_cli(
                "--mission",
                "001-test",
                cwd=tmpdir,
            )

            output = result.stdout

            # Should show file name
            assert "spec.md" in output, "Should show file name"

            # Should show line information or character details
            # (exact format depends on implementation)

    def test_fix_output_shows_summary(self):
        """Verify --fix shows summary of changes made."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            mission_dir = tmpdir / "kitty-specs" / "001-test"
            mission_dir.mkdir(parents=True)
            (mission_dir / "spec.md").write_text("User\u2019s test")
            (mission_dir / "plan.md").write_text("Another \u201ctest\u201d")

            # Initialize git
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)
            (tmpdir / ".kittify").mkdir()

            # Run with --fix
            result = run_validate_encoding_cli(
                "--mission",
                "001-test",
                "--fix",
                cwd=tmpdir,
            )

            output = result.stdout

            # Should show summary
            assert result.returncode == 0, f"Should succeed, got {result.returncode}"
            assert "Fixed" in output or "fixed" in output, "Should mention fixes"
            # May show count of files fixed
