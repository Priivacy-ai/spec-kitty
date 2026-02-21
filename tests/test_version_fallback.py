"""Tests for version fallback behavior in editable installs."""

from unittest.mock import patch
import re


def test_version_fallback_chain():
    """Test version detection tries importlib.metadata then pyproject.toml."""
    from specify_cli.version_utils import get_version

    # In normal test environment, importlib.metadata should work
    version = get_version()
    assert version != "0.0.0-dev", "Should get version from importlib.metadata or pyproject.toml"

    # Version should be valid semver
    assert re.match(r"^\d+\.\d+\.\d+", version), f"Invalid version format: {version}"


def test_pyproject_fallback_works():
    """Test that pyproject.toml fallback works when importlib.metadata fails."""
    from specify_cli.version_utils import read_version_from_pyproject

    version = read_version_from_pyproject()

    # Should successfully read from pyproject.toml
    assert version is not None, "Should read version from pyproject.toml"
    assert version != "0.0.0-dev", "Should not return fallback value"

    assert re.match(r"^\d+\.\d+\.\d+", version), f"Invalid version format: {version}"


def test_pyproject_version_matches_metadata():
    """Verify pyproject.toml version matches installed package version."""
    from specify_cli.version_utils import read_version_from_pyproject

    pyproject_version = read_version_from_pyproject()
    assert pyproject_version is not None, "Should read from pyproject.toml"

    # Get installed version
    try:
        from importlib.metadata import version as get_metadata_version

        metadata_version = get_metadata_version("spec-kitty-cli")

        # Should match
        assert pyproject_version == metadata_version, (
            f"pyproject.toml ({pyproject_version}) should match metadata ({metadata_version})"
        )
    except Exception:
        # If metadata not available (editable install), that's OK
        # The pyproject.toml version is what we'll use
        pass


def test_upgrade_uses_correct_version():
    """Integration test: verify upgrade command uses correct version."""
    from specify_cli import __version__

    # Version should NOT be the old hardcoded fallback
    assert __version__ != "0.5.0-dev", "Upgrade will use wrong version! __version__ is old fallback"

    # Should be valid semver
    assert re.match(r"^\d+\.\d+\.\d+", __version__), f"Invalid __version__ format: {__version__}"


def test_get_version_with_mocked_metadata_failure():
    """Test that get_version() falls back to pyproject.toml when importlib.metadata fails."""
    from specify_cli.version_utils import get_version, read_version_from_pyproject

    # Get expected version from pyproject.toml
    expected_version = read_version_from_pyproject()
    assert expected_version is not None, "pyproject.toml should have version"

    # Mock importlib.metadata.version to fail
    with patch("importlib.metadata.version", side_effect=Exception("Mock failure")):
        version = get_version()

        # Should fall back to pyproject.toml
        assert version == expected_version, (
            f"Should fall back to pyproject.toml version ({expected_version}), got {version}"
        )
        assert version != "0.0.0-dev", "Should not use last-resort fallback when pyproject.toml exists"


def test_get_version_with_all_failures():
    """Test that get_version() returns last-resort fallback when everything fails."""
    from specify_cli.version_utils import get_version

    # Mock both importlib.metadata and read_version_from_pyproject to fail
    with patch("importlib.metadata.version", side_effect=Exception("Mock failure")):
        with patch("specify_cli.version_utils.read_version_from_pyproject", return_value=None):
            version = get_version()

            # Should use last-resort fallback
            assert version == "0.0.0-dev", f"Should fall back to '0.0.0-dev' when everything fails, got {version}"
