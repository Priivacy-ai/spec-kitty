"""Pair-atomicity regression for the brief + source sidecar write.

The intake brief is two files: ``.kittify/mission-brief.md`` and
``.kittify/brief-source.yaml``. Each individual file write is
``open + fsync + replace``-atomic, but a kill between the two
``os.replace`` calls leaves the pair in a half-written state. The
first review of mission ``stability-and-hygiene-hardening-2026-04``
caught this as P2.5: ``write_brief_atomic`` performed two separate
atomic file replacements, so a kill between them could leave
``mission-brief.md`` present without ``brief-source.yaml`` (FR-010
honoured per-file but not pair-atomic).

The fix renames ``source.yaml`` FIRST and ``brief.md`` SECOND, so
the brief acts as the commit marker for the pair. The reader
(:func:`specify_cli.mission_brief.read_brief_source`) treats
``source-without-brief`` as ``None`` (no brief) so the partial state
is invisible to callers.

These tests pin the new ordering and the reader's tolerance.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.intake.brief_writer import write_brief_atomic
from specify_cli.mission_brief import (
    BRIEF_SOURCE_FILENAME,
    MISSION_BRIEF_FILENAME,
    read_brief_source,
    read_mission_brief,
)


pytestmark = [pytest.mark.fast]


def _kittify(tmp_path: Path) -> Path:
    d = tmp_path / ".kittify"
    d.mkdir(exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# Reader honours the commit-marker semantics
# ---------------------------------------------------------------------------


def test_read_brief_source_returns_none_when_brief_marker_missing(
    tmp_path: Path,
) -> None:
    """source.yaml without brief.md is the kill-mid-write window."""
    kittify = _kittify(tmp_path)
    (kittify / BRIEF_SOURCE_FILENAME).write_text(
        "source_file: /tmp/x.md\nbrief_hash: abc\n", encoding="utf-8"
    )
    # No brief.md on disk.
    assert read_brief_source(tmp_path) is None
    assert read_mission_brief(tmp_path) is None


def test_read_brief_source_returns_dict_when_both_files_present(
    tmp_path: Path,
) -> None:
    kittify = _kittify(tmp_path)
    (kittify / MISSION_BRIEF_FILENAME).write_text(
        "# brief\n", encoding="utf-8"
    )
    (kittify / BRIEF_SOURCE_FILENAME).write_text(
        "source_file: /tmp/x.md\nbrief_hash: abc\n", encoding="utf-8"
    )
    out = read_brief_source(tmp_path)
    assert isinstance(out, dict)
    assert out["source_file"] == "/tmp/x.md"


# ---------------------------------------------------------------------------
# Writer renames source first, brief second
# ---------------------------------------------------------------------------


def test_write_brief_atomic_renames_source_before_brief(tmp_path: Path) -> None:
    """The pair-atomic invariant: brief.md is the commit marker.

    We instrument ``atomic_write_text`` to record the order in which
    the two final paths receive their content. ``source.yaml`` MUST
    arrive before ``brief.md``.
    """
    kittify = _kittify(tmp_path)
    brief = kittify / MISSION_BRIEF_FILENAME
    source = kittify / BRIEF_SOURCE_FILENAME

    order: list[str] = []
    real = __import__(
        "specify_cli.intake.brief_writer",
        fromlist=["atomic_write_text"],
    ).atomic_write_text

    def spy(target: Path, text: str, **kwargs):  # noqa: ANN001
        order.append(Path(target).name)
        return real(target, text, **kwargs)

    with patch(
        "specify_cli.intake.brief_writer.atomic_write_text",
        side_effect=spy,
    ):
        write_brief_atomic(
            scanner_root=tmp_path,
            writer_root=tmp_path,
            brief_path=brief,
            brief_text="# brief\n",
            source_path=source,
            source_yaml="source_file: /tmp/x.md\n",
        )

    assert order == [BRIEF_SOURCE_FILENAME, MISSION_BRIEF_FILENAME], (
        f"FR-010 / P2.5 regression: brief writer must rename source.yaml "
        f"before brief.md so brief is the commit marker. Got order: {order!r}"
    )
    assert brief.exists() and source.exists()


def test_kill_simulated_after_source_rename_leaves_invisible_state(
    tmp_path: Path,
) -> None:
    """Simulate a kill *between* the source rename and the brief rename.

    The visible state to the reader MUST be 'no brief' — both readers
    return None — so the partial state is indistinguishable from 'no
    write happened'.
    """
    kittify = _kittify(tmp_path)
    brief = kittify / MISSION_BRIEF_FILENAME
    source = kittify / BRIEF_SOURCE_FILENAME

    # Hand-stage the kill-mid-write state: source on disk, brief not.
    source.write_text("source_file: /tmp/x.md\nbrief_hash: abc\n", encoding="utf-8")
    assert not brief.exists()

    # The reader pair must agree the brief is absent.
    assert read_mission_brief(tmp_path) is None
    assert read_brief_source(tmp_path) is None
