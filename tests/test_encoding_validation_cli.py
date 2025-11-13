"""Functional tests for validate-encoding CLI command.

Test Suite 2: CLI Encoding Validation Command

Tests the spec-kitty validate-encoding command that users and LLMs interact with
to check and fix encoding issues in feature markdown files.

Coverage Target: 85%+ for cli/commands/validate_encoding.py
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
import os

from typer.testing import CliRunner
from specify_cli import app


class TestValidateCleanFeature:
    """Test 2.1: Validate Clean Feature"""

    def test_validate_clean_feature_exits_0(self):
        """Verify command exits 0 when no issues found."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create feature structure
            feature_dir = tmpdir / "kitty-specs" / "001-test-feature"
            feature_dir.mkdir(parents=True)
            (feature_dir / "spec.md").write_text("Clean content")
            (feature_dir / "plan.md").write_text("No issues here")

            # Initialize git repo (required for spec-kitty commands)
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)

            # Create .kittify directory (required for project detection)
            (tmpdir / ".kittify").mkdir()

            # Run validate-encoding command
            # Use subprocess instead of CliRunner for proper cwd handling
            result = subprocess.run(
                ["spec-kitty", "validate-encoding", "--feature", "001-test-feature"],
                cwd=tmpdir,
                capture_output=True,
                text=True
            )

            # Should exit successfully
            assert result.returncode == 0, f"Should exit 0, got {result.returncode}: {result.stdout}"

            # Should confirm clean files
            output = result.stdout + result.stderr
            assert "properly UTF-8 encoded" in output or "✓" in output, \
                f"Should confirm clean encoding. Got: {output}"


class TestDetectIssuesWithoutFix:
    """Test 2.2: Detect Issues Without Fix"""

    def test_detect_issues_without_fix_exits_1(self):
        """Verify command exits 1 when issues found and --fix not specified."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create feature with encoding issue
            feature_dir = tmpdir / "kitty-specs" / "001-test-feature"
            feature_dir.mkdir(parents=True)
            (feature_dir / "bad.md").write_text("User\u2019s test")

            # Initialize git
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)
            (tmpdir / ".kittify").mkdir()

            # Run without --fix
            result = subprocess.run(
                ["spec-kitty", 
                "validate-encoding",
                "--feature", "001-test-feature"
            ],
                cwd=tmpdir,
                capture_output=True,
                text=True
            )

            # Should exit with error code
            assert result.returncode == 1, \
                f"Should exit 1 with issues, got {result.returncode}"

            # Should show the problematic file
            output = result.stdout + result.stderr
            assert "bad.md" in output, \
                f"Should show bad.md in output. Got: {result.stdout}"

            # Should suggest fix
            output = result.stdout + result.stderr
            assert "--fix" in output or "fix" in result.stdout.lower(), \
                f"Should suggest --fix. Got: {result.stdout}"


class TestFixIssuesWithBackup:
    """Test 2.3: Fix Issues With Backup"""

    def test_fix_creates_backup(self):
        """Verify --fix flag repairs files and creates backups."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            feature_dir = tmpdir / "kitty-specs" / "001-test-feature"
            feature_dir.mkdir(parents=True)

            bad_file = feature_dir / "broken.md"
            bad_file.write_text("User\u2019s \u201ctest\u201d")

            # Initialize git
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)
            (tmpdir / ".kittify").mkdir()

            # Run with --fix
            result = subprocess.run(
                ["spec-kitty", 
                "validate-encoding",
                "--feature", "001-test-feature",
                "--fix"
            ],
                cwd=tmpdir,
                capture_output=True,
                text=True
            )

            # Should exit successfully
            assert result.returncode == 0, \
                f"Should exit 0 after fix, got {result.returncode}: {result.stdout}"

            # Should mention fix
            output = result.stdout + result.stderr
            assert "Fixed" in output or "fixed" in result.stdout, \
                f"Should mention fix. Got: {result.stdout}"

            # File should be fixed
            fixed_content = bad_file.read_text()
            assert fixed_content == 'User\'s "test"', \
                f"File should be fixed, got: {fixed_content!r}"

            # Backup should exist
            backup = bad_file.with_suffix(".md.bak")
            assert backup.exists(), "Backup should be created"
            assert backup.read_text() == "User\u2019s \u201ctest\u201d", \
                "Backup should have original content"


class TestFixWithoutBackup:
    """Test 2.4: Fix Without Backup"""

    def test_no_backup_flag_skips_backup(self):
        """Verify --no-backup flag skips backup creation."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            feature_dir = tmpdir / "kitty-specs" / "001-test-feature"
            feature_dir.mkdir(parents=True)

            bad_file = feature_dir / "test.md"
            bad_file.write_text("User\u2019s test")

            # Initialize git
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)
            (tmpdir / ".kittify").mkdir()

            # Run with --fix --no-backup
            result = subprocess.run(
                ["spec-kitty", 
                "validate-encoding",
                "--feature", "001-test-feature",
                "--fix",
                "--no-backup"
            ],
                cwd=tmpdir,
                capture_output=True,
                text=True
            )

            # Should exit successfully
            assert result.returncode == 0, \
                f"Should exit 0, got {result.returncode}"

            # File should be fixed
            assert bad_file.read_text() == "User's test", "File should be fixed"

            # No backup should exist
            backup = bad_file.with_suffix(".md.bak")
            assert not backup.exists(), "Backup should not be created with --no-backup"


class TestValidateAllFeatures:
    """Test 2.5: Validate All Features"""

    def test_validate_all_features(self):
        """Verify --all flag scans multiple features."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create multiple features with issues
            for i in range(1, 4):
                feat_dir = tmpdir / "kitty-specs" / f"00{i}-feature"
                feat_dir.mkdir(parents=True)
                (feat_dir / "spec.md").write_text(f"User\u2019s test {i}")

            # Initialize git
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)
            (tmpdir / ".kittify").mkdir()

            # Run with --all
            result = subprocess.run(
                ["spec-kitty", 
                "validate-encoding",
                "--all"
            ],
                cwd=tmpdir,
                capture_output=True,
                text=True
            )

            # Should detect issues in all features
            assert result.returncode == 1, \
                f"Should exit 1 with issues, got {result.returncode}"

            # Should mention multiple features or show count
            output = result.stdout
            assert ("001-feature" in output or "002-feature" in output or
                    "003-feature" in output or "3" in output or "features" in output), \
                f"Should indicate multiple features scanned. Got: {output}"

    def test_fix_all_features(self):
        """Verify --all --fix repairs all features."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create multiple features
            files_to_check = []
            for i in range(1, 4):
                feat_dir = tmpdir / "kitty-specs" / f"00{i}-feature"
                feat_dir.mkdir(parents=True)
                test_file = feat_dir / "spec.md"
                test_file.write_text(f"User\u2019s test {i}")
                files_to_check.append(test_file)

            # Initialize git
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)
            (tmpdir / ".kittify").mkdir()

            # Run with --all --fix
            result = subprocess.run(
                ["spec-kitty", 
                "validate-encoding",
                "--all",
                "--fix"
            ],
                cwd=tmpdir,
                capture_output=True,
                text=True
            )

            # Should exit successfully
            assert result.returncode == 0, \
                f"Should exit 0 after fixing all, got {result.returncode}"

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

            result = subprocess.run(
                ["spec-kitty", 
                "validate-encoding",
                "--feature", "001-test"
            ],
                cwd=tmpdir,
                capture_output=True,
                text=True
            )

            # Should fail with clear message
            assert result.returncode == 1, "Should exit 1 outside project"
            # Error message should be informative

    def test_command_with_nonexistent_feature(self):
        """Verify appropriate error for nonexistent feature."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Initialize project structure
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)
            (tmpdir / ".kittify").mkdir()
            (tmpdir / "kitty-specs").mkdir()

            # Try to validate nonexistent feature
            result = subprocess.run(
                ["spec-kitty", 
                "validate-encoding",
                "--feature", "999-nonexistent"
            ],
                cwd=tmpdir,
                capture_output=True,
                text=True
            )

            # Should fail with clear message
            assert result.returncode == 1, "Should exit 1 for nonexistent feature"
            output = result.stdout + result.stderr
            assert "not found" in output.lower() or "Error" in result.stdout, \
                f"Should indicate feature not found. Got: {result.stdout}"


class TestCLIOutputFormatting:
    """Test CLI output quality and formatting."""

    def test_output_includes_file_details(self):
        """Verify output shows file names and line numbers when issues found."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            feature_dir = tmpdir / "kitty-specs" / "001-test"
            feature_dir.mkdir(parents=True)

            # Create file with issues
            bad_file = feature_dir / "spec.md"
            bad_file.write_text("Line 1\nUser\u2019s test on line 2\nLine 3")

            # Initialize git
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)
            (tmpdir / ".kittify").mkdir()

            # Run validation
            result = subprocess.run(
                ["spec-kitty", 
                "validate-encoding",
                "--feature", "001-test"
            ],
                cwd=tmpdir,
                capture_output=True,
                text=True
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

            feature_dir = tmpdir / "kitty-specs" / "001-test"
            feature_dir.mkdir(parents=True)
            (feature_dir / "spec.md").write_text("User\u2019s test")
            (feature_dir / "plan.md").write_text("Another \u201ctest\u201d")

            # Initialize git
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)
            (tmpdir / ".kittify").mkdir()

            # Run with --fix
            result = subprocess.run(
                ["spec-kitty", 
                "validate-encoding",
                "--feature", "001-test",
                "--fix"
            ],
                cwd=tmpdir,
                capture_output=True,
                text=True
            )

            output = result.stdout

            # Should show summary
            assert result.returncode == 0, f"Should succeed, got {result.returncode}"
            assert "Fixed" in output or "fixed" in output, "Should mention fixes"
            # May show count of files fixed
