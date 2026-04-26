"""Path-canonicalisation + symlink guard tests (WP02 T008).

These tests pin the contract from
``contracts/intake-source-provenance.md``: any candidate that resolves
outside the intake root must raise :class:`IntakePathEscapeError` and
must do so *before* the file is opened.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from specify_cli.intake.errors import (
    IntakeFileMissingError,
    IntakePathEscapeError,
)
from specify_cli.intake.scanner import assert_under_root, read_brief


pytestmark = [pytest.mark.fast]


def _make_root(tmp_path: Path) -> Path:
    root = tmp_path / "intake-root"
    root.mkdir()
    return root


# ---------------------------------------------------------------------------
# Direct traversal — ``../etc/passwd``
# ---------------------------------------------------------------------------


def test_relative_traversal_raises_path_escape(tmp_path):
    root = _make_root(tmp_path)
    # Create something outside the root so resolve(strict=True) succeeds.
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")

    candidate = root / ".." / "outside.txt"
    with pytest.raises(IntakePathEscapeError) as ei:
        assert_under_root(candidate, root)
    # Both paths surface in the structured detail.
    assert "intake_root" in ei.value.detail
    assert "candidate" in ei.value.detail


def test_absolute_path_outside_root_raises_path_escape(tmp_path):
    root = _make_root(tmp_path)
    outside = tmp_path / "abs-outside.txt"
    outside.write_text("secret", encoding="utf-8")

    with pytest.raises(IntakePathEscapeError):
        assert_under_root(outside.resolve(), root)


# ---------------------------------------------------------------------------
# Symlink escape — link inside root, target outside root
# ---------------------------------------------------------------------------


@pytest.mark.requires_symlinks
def test_symlink_pointing_outside_root_is_rejected(tmp_path):
    root = _make_root(tmp_path)
    secret = tmp_path / "secret.txt"
    secret.write_text("OWNED", encoding="utf-8")

    link = root / "innocent.txt"
    try:
        os.symlink(secret, link)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this platform")

    with pytest.raises(IntakePathEscapeError):
        assert_under_root(link, root)


@pytest.mark.requires_symlinks
def test_read_brief_does_not_open_symlinked_escape(tmp_path):
    """The size-cap test in T009 also verifies the file is not opened, but here
    we make doubly sure by writing a poison-pill outside the root and asserting
    the read never returns its contents."""
    root = _make_root(tmp_path)
    poison = tmp_path / "poison.md"
    poison.write_text("DO NOT READ ME", encoding="utf-8")

    link = root / "bait.md"
    try:
        os.symlink(poison, link)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this platform")

    with pytest.raises(IntakePathEscapeError):
        read_brief(link, cap=1024, intake_root=root)


# ---------------------------------------------------------------------------
# Legitimate paths inside the root continue to read.
# ---------------------------------------------------------------------------


def test_legitimate_path_inside_root_resolves_to_canonical_form(tmp_path):
    root = _make_root(tmp_path)
    inner = root / "plan.md"
    inner.write_text("# Plan", encoding="utf-8")

    resolved = assert_under_root(inner, root)
    assert resolved == inner.resolve(strict=True)


def test_read_brief_inside_root_returns_content(tmp_path):
    root = _make_root(tmp_path)
    inner = root / "plan.md"
    inner.write_text("# Plan body", encoding="utf-8")

    text = read_brief(inner, cap=1024, intake_root=root)
    assert text == "# Plan body"


# ---------------------------------------------------------------------------
# Missing candidate produces FILE_MISSING, not PATH_ESCAPE.
# ---------------------------------------------------------------------------


def test_missing_candidate_inside_root_raises_file_missing(tmp_path):
    root = _make_root(tmp_path)
    missing = root / "ghost.md"

    with pytest.raises(IntakeFileMissingError):
        assert_under_root(missing, root)
