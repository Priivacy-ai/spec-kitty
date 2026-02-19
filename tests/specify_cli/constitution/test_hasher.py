"""Tests for constitution hasher module."""

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from specify_cli.constitution.hasher import hash_content, hash_constitution, is_stale


def test_hash_content_deterministic():
    """Hash function produces consistent output for same content."""
    content = "# My Constitution\n\nSome content here."

    hash1 = hash_content(content)
    hash2 = hash_content(content)

    assert hash1 == hash2
    assert hash1.startswith("sha256:")


def test_hash_content_whitespace_normalization():
    """Hash normalizes trailing whitespace but preserves internal formatting."""
    content1 = "# Constitution\n\nContent."
    content2 = "# Constitution\n\nContent.\n\n\n"  # Extra trailing newlines
    content3 = "# Constitution\n\nContent.\t  \n"  # Trailing tabs and spaces

    hash1 = hash_content(content1)
    hash2 = hash_content(content2)
    hash3 = hash_content(content3)

    # All should produce same hash after normalization
    assert hash1 == hash2 == hash3


def test_hash_content_internal_whitespace_preserved():
    """Hash preserves internal whitespace differences."""
    content1 = "# Constitution\nContent."
    content2 = "# Constitution\n\nContent."  # Extra newline

    hash1 = hash_content(content1)
    hash2 = hash_content(content2)

    # Should be different because internal whitespace differs
    assert hash1 != hash2


def test_hash_constitution_reads_file(tmp_path: Path):
    """hash_constitution reads file and hashes content."""
    constitution_file = tmp_path / "constitution.md"
    constitution_file.write_text("# Test Constitution\n\nRules here.", encoding="utf-8")

    result = hash_constitution(constitution_file)

    assert result.startswith("sha256:")
    # Should match hash_content of same text
    expected = hash_content("# Test Constitution\n\nRules here.")
    assert result == expected


def test_is_stale_no_metadata(tmp_path: Path):
    """is_stale returns True when metadata doesn't exist."""
    constitution_file = tmp_path / "constitution.md"
    constitution_file.write_text("# Constitution", encoding="utf-8")

    metadata_file = tmp_path / "metadata.yaml"

    stale, current_hash, stored_hash = is_stale(constitution_file, metadata_file)

    assert stale is True
    assert current_hash.startswith("sha256:")
    assert stored_hash == ""


def test_is_stale_matching_hash(tmp_path: Path):
    """is_stale returns False when hashes match."""
    constitution_file = tmp_path / "constitution.md"
    content = "# Constitution\n\nRules."
    constitution_file.write_text(content, encoding="utf-8")

    # Create metadata with matching hash
    metadata_file = tmp_path / "metadata.yaml"
    expected_hash = hash_content(content)

    yaml = YAML()
    metadata = {"constitution_hash": expected_hash}
    yaml.dump(metadata, metadata_file)

    stale, current_hash, stored_hash = is_stale(constitution_file, metadata_file)

    assert stale is False
    assert current_hash == expected_hash
    assert stored_hash == expected_hash


def test_is_stale_mismatched_hash(tmp_path: Path):
    """is_stale returns True when hashes don't match."""
    constitution_file = tmp_path / "constitution.md"
    constitution_file.write_text("# New Content", encoding="utf-8")

    # Create metadata with old hash
    metadata_file = tmp_path / "metadata.yaml"
    old_hash = hash_content("# Old Content")

    yaml = YAML()
    metadata = {"constitution_hash": old_hash}
    yaml.dump(metadata, metadata_file)

    stale, current_hash, stored_hash = is_stale(constitution_file, metadata_file)

    assert stale is True
    assert current_hash != old_hash
    assert stored_hash == old_hash


def test_is_stale_empty_metadata(tmp_path: Path):
    """is_stale handles empty metadata file."""
    constitution_file = tmp_path / "constitution.md"
    constitution_file.write_text("# Constitution", encoding="utf-8")

    # Create empty metadata file
    metadata_file = tmp_path / "metadata.yaml"
    metadata_file.write_text("", encoding="utf-8")

    stale, current_hash, stored_hash = is_stale(constitution_file, metadata_file)

    assert stale is True
    assert current_hash.startswith("sha256:")
    assert stored_hash == ""


def test_is_stale_missing_hash_field(tmp_path: Path):
    """is_stale handles metadata without constitution_hash field."""
    constitution_file = tmp_path / "constitution.md"
    constitution_file.write_text("# Constitution", encoding="utf-8")

    # Create metadata without constitution_hash field
    metadata_file = tmp_path / "metadata.yaml"
    yaml = YAML()
    metadata = {"timestamp_utc": "2026-01-01T00:00:00Z"}
    yaml.dump(metadata, metadata_file)

    stale, current_hash, stored_hash = is_stale(constitution_file, metadata_file)

    assert stale is True
    assert current_hash.startswith("sha256:")
    assert stored_hash == ""
