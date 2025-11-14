"""Tests for version detection and reporting.

Validates that spec-kitty version is read dynamically from package metadata
instead of being hardcoded, ensuring --version always shows correct version.

Problem: In v0.5.0, __version__ was hardcoded to "0.4.13" in __init__.py,
causing spec-kitty --version to report incorrect version even though package
metadata showed 0.5.0.

Solution: Use importlib.metadata.version() to read from package metadata.

These tests detect this problem and validate the fix.
"""

import pytest
import subprocess
import sys
from pathlib import Path


class TestVersionReading:
    """Test that version is read from package metadata, not hardcoded."""

    def test_version_matches_package_metadata(self):
        """Verify __version__ matches package metadata version."""
        # Import the version from the module
        from specify_cli import __version__

        # Get version from package metadata
        try:
            from importlib.metadata import version as get_version
            metadata_version = get_version("spec-kitty-cli")
        except Exception as exc:
            pytest.skip(f"Could not read package metadata: {exc}")

        # Versions should match
        assert __version__ == metadata_version, \
            f"Module __version__ ({__version__}) should match package metadata ({metadata_version})"

    def test_cli_version_matches_package_metadata(self):
        """Verify spec-kitty --version command shows package metadata version."""
        # Get version from package metadata
        try:
            from importlib.metadata import version as get_version
            metadata_version = get_version("spec-kitty-cli")
        except Exception as exc:
            pytest.skip(f"Could not read package metadata: {exc}")

        # Run CLI command
        result = subprocess.run(
            ["spec-kitty", "--version"],
            capture_output=True,
            text=True,
            check=True
        )

        output = result.stdout + result.stderr

        # Should show the package metadata version
        assert metadata_version in output, \
            f"CLI should show version {metadata_version}, got: {output}"

    def test_no_hardcoded_version_in_init(self):
        """Verify __init__.py doesn't have hardcoded version string."""
        # Find the __init__.py file
        try:
            import specify_cli
            init_file = Path(specify_cli.__file__)
        except Exception as exc:
            pytest.skip(f"Could not locate __init__.py: {exc}")

        init_content = init_file.read_text()

        # Should NOT have hardcoded version like __version__ = "0.4.13"
        # Should use importlib.metadata or similar
        assert 'importlib.metadata' in init_content or 'importlib_metadata' in init_content, \
            "__init__.py should use importlib.metadata to read version dynamically"

        # Should not have pattern like __version__ = "0.x.x"
        import re
        hardcoded_pattern = re.compile(r'__version__\s*=\s*["\']0\.\d+\.\d+["\']')
        match = hardcoded_pattern.search(init_content)
        assert match is None, \
            f"Found hardcoded version in __init__.py: {match.group(0) if match else 'N/A'}"

    def test_version_format(self):
        """Verify version follows semantic versioning format."""
        from specify_cli import __version__

        # Should match semantic versioning pattern: X.Y.Z or X.Y.Z-suffix
        import re
        semver_pattern = re.compile(r'^\d+\.\d+\.\d+(-\w+)?$')
        assert semver_pattern.match(__version__), \
            f"Version '{__version__}' should follow semantic versioning (X.Y.Z)"


class TestVersionConsistency:
    """Test version consistency across different access methods."""

    def test_version_via_module_import(self):
        """Test version accessible via module import."""
        from specify_cli import __version__
        assert __version__, "Should have __version__ attribute"
        assert isinstance(__version__, str), "__version__ should be string"

    def test_version_via_metadata(self):
        """Test version accessible via package metadata."""
        try:
            from importlib.metadata import version as get_version
            pkg_version = get_version("spec-kitty-cli")
            assert pkg_version, "Should get version from metadata"
            assert isinstance(pkg_version, str), "Metadata version should be string"
        except Exception as exc:
            pytest.skip(f"Package metadata not available: {exc}")

    def test_version_via_cli_command(self):
        """Test version accessible via CLI --version flag."""
        result = subprocess.run(
            ["spec-kitty", "--version"],
            capture_output=True,
            text=True,
            check=True
        )

        output = result.stdout + result.stderr
        assert "version" in output.lower(), "Output should mention version"

        # Should have a version number
        import re
        version_pattern = re.compile(r'\d+\.\d+\.\d+')
        assert version_pattern.search(output), \
            f"Output should contain version number, got: {output}"

    def test_all_version_methods_agree(self):
        """Verify all version access methods return the same value."""
        # Method 1: Module import
        from specify_cli import __version__ as module_version

        # Method 2: Package metadata
        try:
            from importlib.metadata import version as get_version
            metadata_version = get_version("spec-kitty-cli")
        except Exception:
            pytest.skip("Package metadata not available")

        # Method 3: CLI command
        result = subprocess.run(
            ["spec-kitty", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        cli_output = result.stdout + result.stderr

        # All should agree
        assert module_version == metadata_version, \
            f"Module version ({module_version}) should match metadata ({metadata_version})"

        assert metadata_version in cli_output, \
            f"CLI should show metadata version ({metadata_version}), got: {cli_output}"


class TestEdgeCases:
    """Test edge cases for version detection."""

    def test_version_in_development_install(self):
        """Verify version works in development/editable installs."""
        # This test validates that even in -e installs, we get a version
        from specify_cli import __version__

        # In dev install, might show "X.Y.Z-dev" as fallback
        assert __version__, "Should have version even in dev install"
        assert len(__version__) > 0, "Version should not be empty"

        # Should not be "unknown" or similar
        assert __version__.lower() != "unknown", "Version should not be 'unknown'"

    def test_version_does_not_crash_on_import(self):
        """Verify importing specify_cli doesn't crash when getting version."""
        try:
            import specify_cli
            version = specify_cli.__version__
            assert version is not None, "Version should be available"
        except Exception as exc:
            pytest.fail(f"Importing version should not crash: {exc}")

    def test_cli_version_flag_exists(self):
        """Verify --version flag exists and works."""
        result = subprocess.run(
            ["spec-kitty", "--version"],
            capture_output=True,
            text=True
        )

        # Should not crash
        assert result.returncode == 0, \
            f"--version should not crash, got exit code {result.returncode}"

        # Should produce output
        output = result.stdout + result.stderr
        assert len(output) > 0, "--version should produce output"


class TestVersionUpdateWorkflow:
    """Test that version updates work correctly."""

    def test_pyproject_toml_version_readable(self):
        """Verify pyproject.toml version can be read (for reference)."""
        # Find pyproject.toml
        try:
            import specify_cli
            package_root = Path(specify_cli.__file__).parent.parent.parent
            pyproject = package_root / "pyproject.toml"
        except Exception:
            pytest.skip("Could not locate pyproject.toml")

        if not pyproject.exists():
            pytest.skip("pyproject.toml not found")

        content = pyproject.read_text()

        # Should have version field
        import re
        version_pattern = re.compile(r'version\s*=\s*"(\d+\.\d+\.\d+)"')
        match = version_pattern.search(content)

        if match:
            pyproject_version = match.group(1)
            # Just verify it's parseable - may or may not match runtime version
            assert re.match(r'\d+\.\d+\.\d+', pyproject_version), \
                "pyproject.toml version should be valid semver"

    def test_version_not_imported_from_pyproject(self):
        """Verify version is NOT read directly from pyproject.toml at runtime."""
        # Reading from pyproject.toml at runtime is bad practice
        # Should use package metadata instead
        from specify_cli import __version__

        # The version should come from importlib.metadata, not file parsing
        # We validate this by checking __init__.py uses importlib.metadata
        import specify_cli
        init_file = Path(specify_cli.__file__)
        init_content = init_file.read_text()

        # Should use importlib.metadata
        assert 'importlib.metadata' in init_content or 'importlib_metadata' in init_content, \
            "Should use importlib.metadata to get version"

        # Should NOT parse pyproject.toml
        assert 'pyproject.toml' not in init_content, \
            "Should not parse pyproject.toml at runtime"


class TestRegressionPrevention:
    """Tests to prevent version regression bugs."""

    def test_version_mismatch_regression(self):
        """Detect if version becomes hardcoded again (regression)."""
        from specify_cli import __version__ as module_version

        try:
            from importlib.metadata import version as get_version
            metadata_version = get_version("spec-kitty-cli")
        except Exception:
            pytest.skip("Package metadata not available")

        # This is the regression test - if someone hardcodes the version again,
        # this test will fail because module version won't match metadata
        mismatch = module_version != metadata_version

        if mismatch:
            pytest.fail(
                f"VERSION MISMATCH DETECTED - Possible hardcoded version regression!\n"
                f"Module __version__: {module_version}\n"
                f"Package metadata: {metadata_version}\n"
                f"The version should be read from package metadata, not hardcoded.\n"
                f"Check src/specify_cli/__init__.py for hardcoded version string."
            )

    def test_cli_reports_current_version_not_old(self):
        """Detect if CLI reports old version (like 0.4.13 when package is 0.5.0)."""
        try:
            from importlib.metadata import version as get_version
            metadata_version = get_version("spec-kitty-cli")
        except Exception:
            pytest.skip("Package metadata not available")

        result = subprocess.run(
            ["spec-kitty", "--version"],
            capture_output=True,
            text=True,
            check=True
        )

        output = result.stdout + result.stderr

        # CLI should show current version, not old version
        assert metadata_version in output, \
            f"CLI should show current version {metadata_version}, got: {output}"

        # Specifically check it doesn't show old versions
        old_versions = ["0.4.13", "0.4.12", "0.4.11"]
        for old_ver in old_versions:
            if metadata_version != old_ver:  # Only check if we're not actually that version
                assert old_ver not in output, \
                    f"CLI should not show old version {old_ver}, got: {output}"


class TestPackageMetadataIntegrity:
    """Test package metadata is correct."""

    def test_package_metadata_accessible(self):
        """Verify package metadata can be accessed."""
        try:
            from importlib.metadata import version, metadata
            pkg_version = version("spec-kitty-cli")
            pkg_metadata = metadata("spec-kitty-cli")

            assert pkg_version, "Should have version in metadata"
            assert pkg_metadata, "Should have metadata"
        except Exception as exc:
            pytest.fail(f"Package metadata should be accessible: {exc}")

    def test_package_name_is_spec_kitty_cli(self):
        """Verify package is installed as spec-kitty-cli."""
        try:
            from importlib.metadata import version
            # This should not raise - package should be named spec-kitty-cli
            version("spec-kitty-cli")
        except Exception as exc:
            pytest.fail(f"Package should be named 'spec-kitty-cli': {exc}")

    def test_version_is_valid_semver(self):
        """Verify version follows semantic versioning."""
        try:
            from importlib.metadata import version as get_version
            pkg_version = get_version("spec-kitty-cli")
        except Exception:
            pytest.skip("Package metadata not available")

        import re
        # Match X.Y.Z or X.Y.Z-suffix (like 0.5.0-dev)
        semver_pattern = re.compile(r'^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$')
        assert semver_pattern.match(pkg_version), \
            f"Version '{pkg_version}' should follow semantic versioning"
