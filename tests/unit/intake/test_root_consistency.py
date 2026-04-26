"""Scanner-vs-writer root consistency tests (WP02 T012)."""
from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.intake.brief_writer import (
    _validate_root_consistency,
    write_brief_atomic,
)
from specify_cli.intake.errors import IntakeRootInconsistentError


pytestmark = [pytest.mark.fast]


def test_validate_root_consistency_accepts_matching_roots(tmp_path):
    a = tmp_path / "root"
    a.mkdir()
    # Same path, different formulations — both must resolve equal.
    _validate_root_consistency(a, a)
    _validate_root_consistency(a, Path(str(a) + "/."))


def test_validate_root_consistency_rejects_distinct_roots(tmp_path):
    a = tmp_path / "scanner-root"
    b = tmp_path / "writer-root"
    a.mkdir()
    b.mkdir()
    with pytest.raises(IntakeRootInconsistentError) as ei:
        _validate_root_consistency(a, b)
    assert ei.value.detail["scanner_root"].endswith("scanner-root")
    assert ei.value.detail["writer_root"].endswith("writer-root")


def test_write_brief_atomic_blocks_root_mismatch(tmp_path):
    """Even if the brief paths are valid, mismatched roots fail before any I/O."""
    scanner_root = tmp_path / "scan"
    writer_root = tmp_path / "write"
    scanner_root.mkdir()
    writer_root.mkdir()

    brief_path = writer_root / ".kittify" / "mission-brief.md"
    source_path = writer_root / ".kittify" / "brief-source.yaml"

    with pytest.raises(IntakeRootInconsistentError):
        write_brief_atomic(
            scanner_root=scanner_root,
            writer_root=writer_root,
            brief_path=brief_path,
            brief_text="# brief",
            source_path=source_path,
            source_yaml="source_file: x\n",
        )

    # No partial writes leaked through.
    assert not brief_path.exists()
    assert not source_path.exists()


def test_write_brief_atomic_succeeds_when_roots_match(tmp_path):
    root = tmp_path / "intake-root"
    root.mkdir()
    brief_path = root / ".kittify" / "mission-brief.md"
    source_path = root / ".kittify" / "brief-source.yaml"

    write_brief_atomic(
        scanner_root=root,
        writer_root=root,
        brief_path=brief_path,
        brief_text="# brief",
        source_path=source_path,
        source_yaml="source_file: x\n",
    )

    assert brief_path.read_text(encoding="utf-8") == "# brief"
    assert source_path.read_text(encoding="utf-8") == "source_file: x\n"
