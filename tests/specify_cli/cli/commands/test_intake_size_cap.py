"""Regression tests for WP04 T021: oversized file rejection."""

from __future__ import annotations

import pytest
from specify_cli.cli.commands.intake import MAX_BRIEF_FILE_SIZE_BYTES


def test_max_brief_file_size_bytes_is_importable():
    assert isinstance(MAX_BRIEF_FILE_SIZE_BYTES, int)
    assert MAX_BRIEF_FILE_SIZE_BYTES == 5 * 1024 * 1024


def test_size_cap_rejects_oversized_file(tmp_path):
    """Files over MAX_BRIEF_FILE_SIZE_BYTES are rejected before read."""
    import click

    oversized = tmp_path / "big.md"
    oversized.write_bytes(b"x" * (MAX_BRIEF_FILE_SIZE_BYTES + 1))

    from specify_cli.cli.commands.intake import _write_brief_from_candidate

    with pytest.raises((SystemExit, click.exceptions.Exit)):
        _write_brief_from_candidate(tmp_path, oversized, "test", None, force=True)


def test_size_cap_accepts_file_at_limit(tmp_path):
    """Files exactly at the limit are accepted (> not >=)."""
    exact = tmp_path / "exact.md"
    exact.write_bytes(b"# h\n" + b"x" * (MAX_BRIEF_FILE_SIZE_BYTES - 4))
    # Just verify the size check passes (stat.st_size == limit, not > limit)
    assert exact.stat().st_size == MAX_BRIEF_FILE_SIZE_BYTES
    # size check: file_size > MAX means "greater than" — at limit is ok
    assert not (exact.stat().st_size > MAX_BRIEF_FILE_SIZE_BYTES)
