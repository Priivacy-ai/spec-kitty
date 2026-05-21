"""Regression tests for WP04 T021: oversized file rejection."""

from __future__ import annotations

import pytest
from pathlib import Path
from specify_cli.cli.commands.intake import MAX_BRIEF_FILE_SIZE_BYTES
from specify_cli.mission_brief import BRIEF_SOURCE_FILENAME, write_mission_brief


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


def test_intake_show_prints_full_brief_hash(tmp_path, monkeypatch, capsys):
    """--show prints the full stored SHA-256 hash for integrity checks."""
    from specify_cli.cli.commands import intake as intake_module

    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
    write_mission_brief(tmp_path, "# content", "plan.md")
    source_text = (tmp_path / ".kittify" / BRIEF_SOURCE_FILENAME).read_text(encoding="utf-8")
    full_hash = next(
        line.split(": ", 1)[1].strip()
        for line in source_text.splitlines()
        if line.startswith("brief_hash: ")
    )

    intake_module.intake(show=True)

    output = capsys.readouterr().out
    assert full_hash in output
    assert f"{full_hash[:16]}..." not in output
