"""Integration test for upgrade version update behavior."""

from datetime import datetime

from specify_cli.upgrade.metadata import ProjectMetadata
from specify_cli.upgrade.runner import MigrationRunner


def test_upgrade_updates_metadata_to_correct_version(tmp_path):
    """Verify upgrade updates metadata.yaml to actual CLI version, not fallback."""
    from specify_cli import __version__

    # Create mock project structure
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()

    # Create initial metadata with old version
    metadata = ProjectMetadata(
        version="0.12.0",
        initialized_at=datetime.fromisoformat("2026-01-01T00:00:00")
    )
    metadata.save(kittify_dir)

    # Verify initial state
    initial = ProjectMetadata.load(kittify_dir)
    assert initial.version == "0.12.0", "Initial version should be 0.12.0"

    # Run upgrade to current version
    runner = MigrationRunner(tmp_path)
    runner.upgrade(__version__, dry_run=False, include_worktrees=False)

    # Load updated metadata
    updated = ProjectMetadata.load(kittify_dir)

    # Should have updated to ACTUAL version, not "0.5.0-dev" or "0.0.0-dev"
    assert updated.version == __version__, \
        f"Metadata should update to {__version__}, got {updated.version}"

    assert updated.version != "0.5.0-dev", "Should not use old fallback"
    assert updated.version != "0.0.0-dev", "Should not use new fallback"

    # Version should be valid semver
    import re
    assert re.match(r'^\d+\.\d+\.\d+', updated.version), \
        f"Invalid version in metadata: {updated.version}"


def test_upgrade_dry_run_does_not_update_version(tmp_path):
    """Verify dry-run mode doesn't update metadata.yaml."""
    from specify_cli import __version__

    # Create mock project
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()

    metadata = ProjectMetadata(
        version="0.12.0",
        initialized_at=datetime.now()
    )
    metadata.save(kittify_dir)

    # Run upgrade in dry-run mode
    runner = MigrationRunner(tmp_path)
    runner.upgrade(__version__, dry_run=True, include_worktrees=False)

    # Load metadata
    after_dry_run = ProjectMetadata.load(kittify_dir)

    # Version should NOT have changed
    assert after_dry_run.version == "0.12.0", \
        "Dry run should not update version"


def test_cli_version_is_not_fallback():
    """Verify that CLI __version__ is not using the fallback values."""
    from specify_cli import __version__

    # Should NOT be any fallback value
    assert __version__ != "0.5.0-dev", \
        "CLI is using old hardcoded fallback - upgrade will write wrong version"
    assert __version__ != "0.0.0-dev", \
        "CLI is using new fallback - version detection failed"

    # Should be valid semver
    import re
    assert re.match(r'^\d+\.\d+\.\d+', __version__), \
        f"Invalid __version__ format: {__version__}"
