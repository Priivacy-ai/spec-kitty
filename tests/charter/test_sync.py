"""Tests for charter sync orchestrator."""

import pytest
from pathlib import Path

from ruamel.yaml import YAML

from charter.hasher import hash_content
from charter.sync import sync

pytestmark = pytest.mark.fast
# Sample charter content for testing
SAMPLE_CHARTER = """# Testing Standards

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
2. Always write tests for new missions
3. Document all public APIs
"""


def test_sync_fresh_charter(tmp_path: Path):
    """Sync with a fresh charter (no prior extraction)."""
    charter_file = tmp_path / "charter.md"
    charter_file.write_text(SAMPLE_CHARTER, encoding="utf-8")

    result = sync(charter_file, tmp_path)

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


def test_sync_unchanged_charter(tmp_path: Path):
    """Sync with unchanged charter should skip extraction."""
    charter_file = tmp_path / "charter.md"
    charter_file.write_text(SAMPLE_CHARTER, encoding="utf-8")

    # First sync
    result1 = sync(charter_file, tmp_path)
    assert result1.synced is True

    # Second sync (unchanged)
    result2 = sync(charter_file, tmp_path)

    assert result2.synced is False
    assert result2.stale_before is False
    assert result2.files_written == []
    assert result2.error is None


def test_sync_with_force_flag(tmp_path: Path):
    """Sync with --force should extract even if unchanged."""
    charter_file = tmp_path / "charter.md"
    charter_file.write_text(SAMPLE_CHARTER, encoding="utf-8")

    # First sync
    result1 = sync(charter_file, tmp_path)
    assert result1.synced is True

    # Second sync with force=True
    result2 = sync(charter_file, tmp_path, force=True)

    assert result2.synced is True
    assert result2.stale_before is False  # Was not stale
    assert len(result2.files_written) == 3


def test_sync_modified_charter(tmp_path: Path):
    """Sync with modified charter should extract."""
    charter_file = tmp_path / "charter.md"
    charter_file.write_text(SAMPLE_CHARTER, encoding="utf-8")

    # First sync
    result1 = sync(charter_file, tmp_path)
    assert result1.synced is True

    # Modify charter
    modified_content = SAMPLE_CHARTER + "\n4. New directive\n"
    charter_file.write_text(modified_content, encoding="utf-8")

    # Second sync (modified)
    result2 = sync(charter_file, tmp_path)

    assert result2.synced is True
    assert result2.stale_before is True
    assert len(result2.files_written) == 3


def test_sync_idempotency(tmp_path: Path):
    """Running sync twice with same content produces identical output."""
    charter_file = tmp_path / "charter.md"
    charter_file.write_text(SAMPLE_CHARTER, encoding="utf-8")

    # First sync
    result1 = sync(charter_file, tmp_path, force=True)
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
                "charter_hash": metadata.get("charter_hash"),
                "extraction_mode": metadata.get("extraction_mode"),
                "sections_parsed": metadata.get("sections_parsed"),
            }
        else:
            files1[filename] = file_path.read_text()

    # Second sync with force
    result2 = sync(charter_file, tmp_path, force=True)
    assert result2.synced is True

    # Read generated files again
    files2 = {}
    for filename in result2.files_written:
        file_path = tmp_path / filename
        if filename == "metadata.yaml":
            metadata = yaml.load(file_path)
            files2[filename] = {
                "schema_version": metadata.get("schema_version"),
                "charter_hash": metadata.get("charter_hash"),
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
    """Sync updates the metadata with current charter hash."""
    charter_file = tmp_path / "charter.md"
    charter_file.write_text(SAMPLE_CHARTER, encoding="utf-8")

    result = sync(charter_file, tmp_path)
    assert result.synced is True

    # Read metadata
    metadata_file = tmp_path / "metadata.yaml"
    assert metadata_file.exists()

    yaml = YAML()
    metadata = yaml.load(metadata_file)

    assert "charter_hash" in metadata
    expected_hash = hash_content(SAMPLE_CHARTER)
    assert metadata["charter_hash"] == expected_hash


def test_sync_custom_output_dir(tmp_path: Path):
    """Sync can write to custom output directory."""
    charter_file = tmp_path / "charter.md"
    charter_file.write_text(SAMPLE_CHARTER, encoding="utf-8")

    output_dir = tmp_path / "custom_output"

    result = sync(charter_file, output_dir)

    assert result.synced is True
    for filename in result.files_written:
        assert (output_dir / filename).exists()


def test_sync_creates_output_dir(tmp_path: Path):
    """Sync creates output directory if it doesn't exist."""
    charter_file = tmp_path / "charter.md"
    charter_file.write_text(SAMPLE_CHARTER, encoding="utf-8")

    output_dir = tmp_path / "nested" / "output"
    assert not output_dir.exists()

    result = sync(charter_file, output_dir)

    assert result.synced is True
    assert output_dir.exists()


def test_sync_with_invalid_charter(tmp_path: Path):
    """Sync handles invalid charter gracefully."""
    charter_file = tmp_path / "charter.md"
    # Write empty content
    charter_file.write_text("", encoding="utf-8")

    result = sync(charter_file, tmp_path)

    # Should complete but may have minimal content
    # (Parser is fault-tolerant, won't raise exception)
    assert result.synced is True
    assert result.error is None


def test_sync_missing_charter_file(tmp_path: Path):
    """Sync returns error when charter file doesn't exist."""
    charter_file = tmp_path / "nonexistent.md"

    result = sync(charter_file, tmp_path)

    assert result.synced is False
    assert result.error is not None
    assert "No such file" in result.error or "does not exist" in result.error.lower()
