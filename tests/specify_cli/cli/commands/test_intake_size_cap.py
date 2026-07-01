"""Regression tests for WP04 T021: oversized file rejection."""
from __future__ import annotations

import pytest
from pathlib import Path
from specify_cli.cli.commands.intake import MAX_BRIEF_FILE_SIZE_BYTES


pytestmark = [pytest.mark.unit, pytest.mark.fast]

def test_max_brief_file_size_bytes_is_importable():
    assert isinstance(MAX_BRIEF_FILE_SIZE_BYTES, int)
    assert MAX_BRIEF_FILE_SIZE_BYTES == 5 * 1024 * 1024


def test_size_cap_rejects_oversized_file(tmp_path):
    """Files over MAX_BRIEF_FILE_SIZE_BYTES are rejected before read."""
    import typer
    oversized = tmp_path / "big.md"
    oversized.write_bytes(b"x" * (MAX_BRIEF_FILE_SIZE_BYTES + 1))

    from specify_cli.cli.commands.intake import _write_brief_from_candidate

    with pytest.raises((SystemExit, typer.Exit)):
        _write_brief_from_candidate(tmp_path, oversized, "test", None, force=True)
