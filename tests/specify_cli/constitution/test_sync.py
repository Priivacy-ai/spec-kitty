"""Tests for constitution sync orchestrator."""

from pathlib import Path

from ruamel.yaml import YAML

from specify_cli.constitution.hasher import hash_content
from specify_cli.constitution.sync import sync


# Sample constitution content for testing
SAMPLE_CONSTITUTION = """# Testing Standards

## Coverage Requirements
- Minimum 80% code coverage
- All critical paths must be tested

## Quality Gates
- Must pass all linters
- Must pass type checking

## Performance Benchmarks
- API response time < 200ms
- Page load time < 1s

## Branch Strategy
- main: production-ready code
- develop: integration branch

## Agent Configuration
| agent | role | model |
|-------|------|-------|
| claude | implementer | claude-sonnet-4 |
| copilot | reviewer | gpt-4 |

## Project Directives
1. Never commit secrets to repository
2. Always write tests for new features
3. Document all public APIs
"""


def test_sync_fresh_constitution(tmp_path: Path):
    """Sync with a fresh constitution (no prior extraction)."""
    constitution_file = tmp_path / "constitution.md"
    constitution_file.write_text(SAMPLE_CONSTITUTION, encoding="utf-8")

    result = sync(constitution_file, tmp_path)

    assert result.synced is True
    assert result.stale_before is True
    assert result.error is None
    assert result.extraction_mode in ["deterministic", "hybrid"]
    assert set(result.files_written) == {
        "governance.yaml",
        "directives.yaml",
        "metadata.yaml",
    }

    # Verify files were created
    for filename in result.files_written:
        assert (tmp_path / filename).exists()


def test_sync_unchanged_constitution(tmp_path: Path):
    """Sync with unchanged constitution should skip extraction."""
    constitution_file = tmp_path / "constitution.md"
    constitution_file.write_text(SAMPLE_CONSTITUTION, encoding="utf-8")

    # First sync
    result1 = sync(constitution_file, tmp_path)
    assert result1.synced is True

    # Second sync (unchanged)
    result2 = sync(constitution_file, tmp_path)

    assert result2.synced is False
    assert result2.stale_before is False
    assert result2.files_written == []
    assert result2.error is None


def test_sync_with_force_flag(tmp_path: Path):
    """Sync with --force should extract even if unchanged."""
    constitution_file = tmp_path / "constitution.md"
    constitution_file.write_text(SAMPLE_CONSTITUTION, encoding="utf-8")

    # First sync
    result1 = sync(constitution_file, tmp_path)
    assert result1.synced is True

    # Second sync with force=True
    result2 = sync(constitution_file, tmp_path, force=True)

    assert result2.synced is True
    assert result2.stale_before is False  # Was not stale
    assert len(result2.files_written) == 3


def test_sync_modified_constitution(tmp_path: Path):
    """Sync with modified constitution should extract."""
    constitution_file = tmp_path / "constitution.md"
    constitution_file.write_text(SAMPLE_CONSTITUTION, encoding="utf-8")

    # First sync
    result1 = sync(constitution_file, tmp_path)
    assert result1.synced is True

    # Modify constitution
    modified_content = SAMPLE_CONSTITUTION + "\n4. New directive\n"
    constitution_file.write_text(modified_content, encoding="utf-8")

    # Second sync (modified)
    result2 = sync(constitution_file, tmp_path)

    assert result2.synced is True
    assert result2.stale_before is True
    assert len(result2.files_written) == 3


def test_sync_idempotency(tmp_path: Path):
    """Running sync twice with same content produces identical output."""
    constitution_file = tmp_path / "constitution.md"
    constitution_file.write_text(SAMPLE_CONSTITUTION, encoding="utf-8")

    # First sync
    result1 = sync(constitution_file, tmp_path, force=True)
    assert result1.synced is True

    # Read generated files
    yaml = YAML()
    files1 = {}
    for filename in result1.files_written:
        file_path = tmp_path / filename
        if filename == "metadata.yaml":
            # For metadata, compare structure but not timestamp
            metadata = yaml.load(file_path)
            files1[filename] = {
                "schema_version": metadata.get("schema_version"),
                "constitution_hash": metadata.get("constitution_hash"),
                "extraction_mode": metadata.get("extraction_mode"),
                "sections_parsed": metadata.get("sections_parsed"),
            }
        else:
            files1[filename] = file_path.read_text()

    # Second sync with force
    result2 = sync(constitution_file, tmp_path, force=True)
    assert result2.synced is True

    # Read generated files again
    files2 = {}
    for filename in result2.files_written:
        file_path = tmp_path / filename
        if filename == "metadata.yaml":
            metadata = yaml.load(file_path)
            files2[filename] = {
                "schema_version": metadata.get("schema_version"),
                "constitution_hash": metadata.get("constitution_hash"),
                "extraction_mode": metadata.get("extraction_mode"),
                "sections_parsed": metadata.get("sections_parsed"),
            }
        else:
            files2[filename] = file_path.read_text()

    # Files should be identical (excluding timestamps)
    assert files1.keys() == files2.keys()
    for filename in files1:
        assert files1[filename] == files2[filename], f"{filename} differs"


def test_sync_updates_metadata_hash(tmp_path: Path):
    """Sync updates the metadata with current constitution hash."""
    constitution_file = tmp_path / "constitution.md"
    constitution_file.write_text(SAMPLE_CONSTITUTION, encoding="utf-8")

    result = sync(constitution_file, tmp_path)
    assert result.synced is True

    # Read metadata
    metadata_file = tmp_path / "metadata.yaml"
    assert metadata_file.exists()

    yaml = YAML()
    metadata = yaml.load(metadata_file)

    assert "constitution_hash" in metadata
    expected_hash = hash_content(SAMPLE_CONSTITUTION)
    assert metadata["constitution_hash"] == expected_hash


def test_sync_custom_output_dir(tmp_path: Path):
    """Sync can write to custom output directory."""
    constitution_file = tmp_path / "constitution.md"
    constitution_file.write_text(SAMPLE_CONSTITUTION, encoding="utf-8")

    output_dir = tmp_path / "custom_output"

    result = sync(constitution_file, output_dir)

    assert result.synced is True
    for filename in result.files_written:
        assert (output_dir / filename).exists()


def test_sync_creates_output_dir(tmp_path: Path):
    """Sync creates output directory if it doesn't exist."""
    constitution_file = tmp_path / "constitution.md"
    constitution_file.write_text(SAMPLE_CONSTITUTION, encoding="utf-8")

    output_dir = tmp_path / "nested" / "output"
    assert not output_dir.exists()

    result = sync(constitution_file, output_dir)

    assert result.synced is True
    assert output_dir.exists()


def test_sync_with_invalid_constitution(tmp_path: Path):
    """Sync handles invalid constitution gracefully."""
    constitution_file = tmp_path / "constitution.md"
    # Write empty content
    constitution_file.write_text("", encoding="utf-8")

    result = sync(constitution_file, tmp_path)

    # Should complete but may have minimal content
    # (Parser is fault-tolerant, won't raise exception)
    assert result.synced is True
    assert result.error is None


def test_sync_missing_constitution_file(tmp_path: Path):
    """Sync returns error when constitution file doesn't exist."""
    constitution_file = tmp_path / "nonexistent.md"

    result = sync(constitution_file, tmp_path)

    assert result.synced is False
    assert result.error is not None
    assert "No such file" in result.error or "does not exist" in result.error.lower()
