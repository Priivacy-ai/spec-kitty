"""Unit tests for the ``accept`` stranded-verdict provenance diagnostic.

verdict-seam-write-unification-01KZ9Q35 pre-merge remediation (FR-012/SC-008).
``_stranded_verdict_provenance_note`` is the non-blocking ``spec-kitty accept``
diagnostic that surfaces a WP carrying a terminal review-cycle ``.md`` verdict
with no event-log ``review_result`` slot -- prompting an operator to run
``spec-kitty upgrade`` (which runs the backfill) before a consumer reads the
retired frontmatter authority mid-upgrade. It reuses the WP02 SC-008 hermetic
fixture shape.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.cli.commands.accept import _stranded_verdict_provenance_note
from specify_cli.migration.verdict_provenance_backfill import backfill_verdict_provenance
from specify_cli.review.artifacts import ReviewCycleArtifact

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _write_stranded_mission(tmp_path: Path, *, wp_id: str = "WP01") -> Path:
    slug = "042-accept-provenance-demo"
    feature_dir = tmp_path / "kitty-specs" / slug
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {"mission_slug": slug, "mission_id": "01JRDACCEPTPROV0000000000"}
        ),
        encoding="utf-8",
    )
    sub_dir = feature_dir / "tasks" / f"{wp_id}-demo"
    artifact = ReviewCycleArtifact(
        cycle_number=1,
        wp_id=wp_id,
        mission_slug=slug,
        reviewer_agent="reviewer-renata",
        reviewed_at="2026-01-01T00:00:00+00:00",
        body="# Review\n",
    )
    path = sub_dir / "review-cycle-1.md"
    artifact.write(path)
    text = path.read_text(encoding="utf-8")
    path.write_text(f"---\nverdict: rejected\n{text[4:]}", encoding="utf-8")
    return feature_dir


def test_note_reports_stranded_wp(tmp_path: Path) -> None:
    feature_dir = _write_stranded_mission(tmp_path)

    note = _stranded_verdict_provenance_note(feature_dir)

    assert note is not None
    assert "WP01" in note
    assert "spec-kitty upgrade" in note
    assert "1 WP(s)" in note


def test_note_none_after_backfill(tmp_path: Path) -> None:
    feature_dir = _write_stranded_mission(tmp_path)
    backfill_verdict_provenance(feature_dir)

    assert _stranded_verdict_provenance_note(feature_dir) is None


def test_note_none_when_nothing_stranded(tmp_path: Path) -> None:
    feature_dir = tmp_path / "kitty-specs" / "042-empty"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"mission_slug": "042-empty", "mission_id": "01JRDEMPTY0000000000000000"}),
        encoding="utf-8",
    )

    assert _stranded_verdict_provenance_note(feature_dir) is None


def test_note_none_and_never_raises_on_unreadable_dir(tmp_path: Path) -> None:
    """The diagnostic must never abort accept: a non-existent dir degrades to
    ``None``, not an exception."""
    assert _stranded_verdict_provenance_note(tmp_path / "does-not-exist") is None
