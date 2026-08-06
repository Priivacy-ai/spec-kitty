"""SC-007 structural gate: the artifact carries no ``verdict`` field (WP06,
T030/T031, FR-003).

D-PLAN-12: this is a SERIALIZED-FIELD assertion -- parse a written
``review-cycle-N.md`` and assert its on-disk frontmatter has no ``verdict``
key -- distinct from ``tests/architectural/verdict_seam_census.yaml``, which
classifies FUNCTIONS (writer/resolver/reader shapes), never asserts on a
literal serialized payload. Also gates the schema directly (squad #12): a
payload without ``verdict`` deserializes cleanly via ``from_dict``, and
``validate_review_artifact`` no longer requires or accepts it as an
authoritative field.

Every assertion here was RED against the pre-WP06 schema (``verdict: str``
field on ``ReviewCycleArtifact``, required by ``to_dict``/``from_dict``/
``validate_review_artifact``) and is GREEN after the field's removal --
verified via ``git stash`` against this same test file, foreground, before
landing (see this WP's final report for the transcript).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.review.artifacts import AffectedFile, ReviewCycleArtifact
from specify_cli.review.cycle import ReviewCycleError, validate_review_artifact

_SAMPLE_KWARGS: dict[str, object] = {
    "cycle_number": 1,
    "wp_id": "WP01",
    "mission_slug": "verdict-seam-write-unification-01KZ9Q35",
    "reviewer_agent": "reviewer-renata",
    "reviewed_at": "2026-08-06T00:00:00+00:00",
    "affected_files": [AffectedFile(path="src/specify_cli/review/artifacts.py", line_range="1-10")],
    "reproduction_command": "pytest tests/review/test_artifacts_no_verdict_field.py -q",
    "body": "## Findings\n\nStructural single-authority check.",
}


def _sample_artifact() -> ReviewCycleArtifact:
    return ReviewCycleArtifact(**_SAMPLE_KWARGS)


# ---------------------------------------------------------------------------
# T030(a): the WRITTEN, on-disk artifact carries no verdict key.
# ---------------------------------------------------------------------------


def test_written_artifact_frontmatter_has_no_verdict_key(tmp_path: Path) -> None:
    """SC-007's structural anchor: a real ``.write()`` call, read back as raw
    text, must not contain a ``verdict:`` frontmatter line -- the artifact
    physically cannot carry a verdict, not merely "happens not to" for this
    one construction path."""
    artifact = _sample_artifact()
    dest = tmp_path / "review-cycle-1.md"
    artifact.write(dest)

    text = dest.read_text(encoding="utf-8")
    frontmatter = text.split("---", 2)[1]
    frontmatter_keys = {
        line.split(":", 1)[0].strip()
        for line in frontmatter.splitlines()
        if line and not line.startswith((" ", "\t", "-"))
    }
    assert "verdict" not in frontmatter_keys, (
        f"written review-cycle artifact frontmatter must carry no verdict key, "
        f"found keys {sorted(frontmatter_keys)} in:\n{frontmatter}"
    )


def test_to_dict_output_has_no_verdict_key() -> None:
    """The in-memory serialization (``to_dict``) has no ``verdict`` key --
    complements the on-disk check above at the dict layer, one level below
    YAML serialization."""
    d = _sample_artifact().to_dict()
    assert "verdict" not in d


def test_dataclass_has_no_verdict_attribute() -> None:
    """The dataclass itself has no ``verdict`` field -- accessing it must
    raise ``AttributeError``, not silently return a stale/default value."""
    artifact = _sample_artifact()
    with pytest.raises(AttributeError):
        _ = artifact.verdict


# ---------------------------------------------------------------------------
# T030(b): from_dict / validate_review_artifact no longer require OR accept
# a verdict key as authoritative (squad #12).
# ---------------------------------------------------------------------------


def test_from_dict_deserializes_cleanly_without_a_verdict_key() -> None:
    """A payload with NO ``verdict`` key at all deserializes cleanly -- the
    field is not merely optional-with-a-default, it does not exist."""
    payload = {
        "cycle_number": 1,
        "wp_id": "WP01",
        "mission_slug": "verdict-seam-write-unification-01KZ9Q35",
        "reviewer_agent": "reviewer-renata",
        "reviewed_at": "2026-08-06T00:00:00+00:00",
        "affected_files": [],
        "reproduction_command": None,
    }
    artifact = ReviewCycleArtifact.from_dict(payload, body="body text")
    assert artifact.cycle_number == 1
    assert not hasattr(artifact, "verdict")


def test_from_dict_ignores_a_stray_legacy_verdict_key_not_as_authority() -> None:
    """A payload carrying a STRAY ``verdict`` key (the real shape of every
    already-committed pre-WP06 ``.md`` file, which will carry this key
    forever) deserializes cleanly and the key is simply DROPPED -- never
    stored on the dataclass, never treated as authoritative. This is the
    "no longer accepts it as authoritative" half of squad #12's gate."""
    payload = {
        "cycle_number": 1,
        "wp_id": "WP01",
        "mission_slug": "verdict-seam-write-unification-01KZ9Q35",
        "reviewer_agent": "reviewer-renata",
        "reviewed_at": "2026-08-06T00:00:00+00:00",
        "affected_files": [],
        "reproduction_command": None,
        "verdict": "approved",
    }
    artifact = ReviewCycleArtifact.from_dict(payload, body="body text")
    assert not hasattr(artifact, "verdict")
    # Round-tripping this artifact must not resurrect the stray key either.
    assert "verdict" not in artifact.to_dict()


def test_validate_review_artifact_no_longer_requires_or_rejects_on_verdict() -> None:
    """``validate_review_artifact`` (cycle.py) no longer has a verdict check
    at all -- a well-formed artifact (built with no verdict field) passes
    validation cleanly; this test would have failed with a
    ``ReviewCycleError`` complaining about a missing/invalid verdict against
    the pre-WP06 validator."""
    artifact = _sample_artifact()
    validate_review_artifact(artifact)  # must not raise


def test_write_then_from_file_round_trip_loads_prose_without_verdict(tmp_path: Path) -> None:
    """``.latest``/``.from_file`` (KEPT per WP05's scope correction -- content
    /cycle-number loaders, not verdict-authority readers) still load the
    artifact's PROSE (body, affected_files) correctly with no verdict field
    anywhere in the round trip."""
    artifact = _sample_artifact()
    dest = tmp_path / "review-cycle-1.md"
    artifact.write(dest)

    restored = ReviewCycleArtifact.from_file(dest)
    assert restored.cycle_number == artifact.cycle_number
    assert restored.wp_id == artifact.wp_id
    assert restored.body.strip() == artifact.body.strip()
    assert restored.affected_files == artifact.affected_files
    assert not hasattr(restored, "verdict")

    latest = ReviewCycleArtifact.latest(tmp_path)
    assert latest is not None
    assert latest.body.strip() == artifact.body.strip()
    assert not hasattr(latest, "verdict")


def test_review_cycle_error_is_still_raised_for_genuinely_missing_required_fields() -> None:
    """Sanity/non-vacuity: `from_dict` still refuses a payload missing an
    ACTUAL required field (e.g. ``reviewer_agent``) -- proving the validator
    isn't simply disabled wholesale, only the verdict-specific check was
    removed."""
    payload = {
        "cycle_number": 1,
        "wp_id": "WP01",
        "mission_slug": "verdict-seam-write-unification-01KZ9Q35",
        "reviewer_agent": "",
        "reviewed_at": "2026-08-06T00:00:00+00:00",
    }
    with pytest.raises(ValueError, match="reviewer_agent"):
        ReviewCycleArtifact.from_dict(payload, body="body text")


def test_validate_review_artifact_still_refuses_missing_body() -> None:
    """Non-vacuity for ``validate_review_artifact`` itself: it still refuses
    on a genuinely missing required field (empty body) -- proving the
    function's OTHER checks are intact, only its verdict check is gone."""
    artifact = ReviewCycleArtifact(
        cycle_number=1,
        wp_id="WP01",
        mission_slug="verdict-seam-write-unification-01KZ9Q35",
        reviewer_agent="reviewer-renata",
        reviewed_at="2026-08-06T00:00:00+00:00",
        body="",
    )
    with pytest.raises(ReviewCycleError, match="body"):
        validate_review_artifact(artifact)
