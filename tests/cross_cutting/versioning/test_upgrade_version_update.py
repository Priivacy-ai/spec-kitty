"""Integration test for upgrade version update behavior."""

import subprocess
from datetime import datetime
from pathlib import Path

import yaml

from specify_cli.migration.schema_version import REQUIRED_SCHEMA_VERSION
from specify_cli.upgrade.metadata import ProjectMetadata
from specify_cli.upgrade.runner import MigrationRunner


def _init_git_repo(root):
    """Initialize a git repo so upgrade migrations can resolve canonical roots."""
    subprocess.run(
        ["git", "init", "--initial-branch=main"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "--allow-empty", "-m", "init"],
        cwd=root,
        check=True,
        capture_output=True,
    )


def test_upgrade_updates_metadata_to_correct_version(tmp_path):
    """Verify upgrade updates metadata.yaml to actual CLI version, not fallback."""
    from specify_cli import __version__

    _init_git_repo(tmp_path)

    # Create mock project structure
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()

    # Create initial metadata with old version
    metadata = ProjectMetadata(version="0.12.0", initialized_at=datetime.fromisoformat("2026-01-01T00:00:00"))
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
    assert updated.version == __version__, f"Metadata should update to {__version__}, got {updated.version}"

    assert updated.version != "0.5.0-dev", "Should not use old fallback"
    assert updated.version != "0.0.0-dev", "Should not use new fallback"

    # Version should be valid semver
    import re

    assert re.match(r"^\d+\.\d+\.\d+", updated.version), f"Invalid version in metadata: {updated.version}"


def test_upgrade_dry_run_does_not_update_version(tmp_path):
    """Verify dry-run mode doesn't update metadata.yaml."""
    from specify_cli import __version__

    _init_git_repo(tmp_path)

    # Create mock project
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()

    metadata = ProjectMetadata(version="0.12.0", initialized_at=datetime.now())
    metadata.save(kittify_dir)

    # Run upgrade in dry-run mode
    runner = MigrationRunner(tmp_path)
    runner.upgrade(__version__, dry_run=True, include_worktrees=False)

    # Load metadata
    after_dry_run = ProjectMetadata.load(kittify_dir)

    # Version should NOT have changed
    assert after_dry_run.version == "0.12.0", "Dry run should not update version"


def test_upgrade_persists_schema_version(tmp_path: Path) -> None:
    """Regression: spec-kitty upgrade must leave schema_version stamped in metadata.yaml.

    Before the FR-002 / #705 fix, ``MigrationRunner.upgrade()`` ran
    ``_stamp_schema_version`` BEFORE ``ProjectMetadata.save()``. ``save()``
    reconstructs the YAML from a fixed three-key dict and does not preserve
    unknown keys, so the stamped ``schema_version`` was wiped out one line
    later. That left projects in PROJECT_MIGRATION_NEEDED state right after a
    "successful" upgrade. This test pins the post-condition: after a
    non-dry-run upgrade, ``spec_kitty.schema_version`` must equal
    ``REQUIRED_SCHEMA_VERSION``.
    """
    from specify_cli import __version__

    _init_git_repo(tmp_path)

    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()

    # Pre-fix-era metadata: spec_kitty.version present but no schema_version.
    metadata = ProjectMetadata(
        version="0.12.0",
        initialized_at=datetime.fromisoformat("2026-01-01T00:00:00"),
    )
    metadata.save(kittify_dir)

    # Sanity: starting state has no schema_version.
    pre = yaml.safe_load((kittify_dir / "metadata.yaml").read_text(encoding="utf-8"))
    assert "schema_version" not in pre.get("spec_kitty", {}), "Test setup invariant violated: schema_version should be absent before upgrade"

    runner = MigrationRunner(tmp_path)
    result = runner.upgrade(__version__, dry_run=False, include_worktrees=False)

    assert result.success is True, f"Upgrade failed: errors={result.errors}"

    # The post-condition the FR-002 fix guarantees:
    post = yaml.safe_load((kittify_dir / "metadata.yaml").read_text(encoding="utf-8"))
    assert REQUIRED_SCHEMA_VERSION is not None, (
        "REQUIRED_SCHEMA_VERSION is None; this test is meaningful only when the "
        "schema-version gate is active. If the gate is intentionally disabled, "
        "remove this assertion."
    )
    assert post["spec_kitty"]["schema_version"] == REQUIRED_SCHEMA_VERSION, (
        f"schema_version was clobbered by metadata.save(). "
        f"Expected {REQUIRED_SCHEMA_VERSION}, got "
        f"{post.get('spec_kitty', {}).get('schema_version')!r}. "
        "Regression of FR-002 / #705."
    )


def test_cli_version_is_not_fallback():
    """Verify that CLI __version__ is not using the fallback values."""
    from specify_cli import __version__

    # Should NOT be any fallback value
    assert __version__ != "0.5.0-dev", "CLI is using old hardcoded fallback - upgrade will write wrong version"
    assert __version__ != "0.0.0-dev", "CLI is using new fallback - version detection failed"

    # Should be valid semver
    import re

    assert re.match(r"^\d+\.\d+\.\d+", __version__), f"Invalid __version__ format: {__version__}"
