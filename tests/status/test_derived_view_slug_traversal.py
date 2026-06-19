"""Fail-closed traversal tests for the derived-view write sinks.

``StatusSnapshot.mission_slug`` is copied verbatim from UNTRUSTED event-record
content (``StatusEvent.from_dict`` → ``reduce``). Three sinks join that slug into
a path and ``mkdir``/write under ``.kittify/derived/``:

- ``progress.generate_progress_json``
- ``lifecycle.generate_lifecycle_json``
- ``views.write_derived_views``

A crafted event ``{"mission_slug": "../../../../evil"}`` must NOT escape the
derived root. The single chokepoint is ``reducer.reduce`` (via
``core.paths.safe_mission_slug``), which downgrades an unsafe slug to ``""`` so
every sink's existing ``slug or feature_dir.name`` fallback engages.

Each sink test asserts:
  1. the traversal target dir does NOT exist after the call, and
  2. output lands under the trusted ``feature_dir.name`` path.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.status.lifecycle import generate_lifecycle_json
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.progress import generate_progress_json
from specify_cli.status.reducer import reduce
from specify_cli.status.store import EVENTS_FILENAME, append_event
from specify_cli.status.views import write_derived_views

pytestmark = pytest.mark.fast

# Escapes the derived_dir boundary (one level up) while staying inside the test
# sandbox so the assertion never depends on a shared system path like /tmp/evil.
# The security property under test is "does not escape derived_dir", which this
# exercises exactly; a deeper "../../../../" slug resolves the same way through
# the same unguarded mkdir but would write to a shared location.
_HOSTILE_SLUG = "../evil"
_FEATURE_NAME = "034-trusted-feature"


def _hostile_event(slug: str = _HOSTILE_SLUG) -> StatusEvent:
    """Build a StatusEvent whose mission_slug is an attacker traversal string."""
    return StatusEvent(
        event_id="01HXYZ0123456789ABCDEFGHJK",
        mission_slug=slug,
        wp_id="WP01",
        from_lane=Lane.PLANNED,
        to_lane=Lane.CLAIMED,
        at="2026-02-08T12:00:00Z",
        actor="claude-opus",
        force=False,
        execution_mode="worktree",
        mission_id=None,
    )


def _seed_hostile_feature_dir(tmp_path: Path) -> Path:
    """Create a feature dir with an event log carrying a hostile mission_slug."""
    feature_dir = tmp_path / "kitty-specs" / _FEATURE_NAME
    feature_dir.mkdir(parents=True)
    append_event(feature_dir, _hostile_event())
    return feature_dir


# --- direct seam unit test (reduce) ---


def test_reduce_downgrades_hostile_mission_slug_to_empty() -> None:
    """The reduce seam sanitizes an unsafe event slug to '' (fail-closed source)."""
    snapshot = reduce([_hostile_event()])

    # Downgraded to empty so every sink falls back to the trusted feature_dir.name.
    assert snapshot.mission_slug == ""


def test_reduce_preserves_a_safe_mission_slug() -> None:
    """A well-formed slug is preserved untouched (guard does not over-reject)."""
    snapshot = reduce([_hostile_event(slug="034-real-mission")])

    assert snapshot.mission_slug == "034-real-mission"


# --- sink integration tests ---


def test_generate_progress_json_fail_closed_on_traversal_slug(tmp_path: Path) -> None:
    feature_dir = _seed_hostile_feature_dir(tmp_path)
    derived_dir = tmp_path / "derived"
    derived_dir.mkdir()

    generate_progress_json(feature_dir, derived_dir)

    # Traversal target must NOT exist; output lands under the trusted name.
    assert not (derived_dir / _HOSTILE_SLUG).resolve().exists()
    assert (derived_dir / _FEATURE_NAME / "progress.json").exists()


def test_generate_lifecycle_json_fail_closed_on_traversal_slug(tmp_path: Path) -> None:
    feature_dir = _seed_hostile_feature_dir(tmp_path)
    derived_dir = tmp_path / "derived"
    derived_dir.mkdir()

    generate_lifecycle_json(feature_dir, derived_dir)

    assert not (derived_dir / _HOSTILE_SLUG).resolve().exists()
    assert (derived_dir / _FEATURE_NAME / "lifecycle.json").exists()


def test_write_derived_views_fail_closed_on_traversal_slug(tmp_path: Path) -> None:
    feature_dir = _seed_hostile_feature_dir(tmp_path)
    derived_dir = tmp_path / "derived"
    derived_dir.mkdir()

    write_derived_views(feature_dir, derived_dir)

    assert not (derived_dir / _HOSTILE_SLUG).resolve().exists()
    assert (derived_dir / _FEATURE_NAME / "status.json").exists()


def test_event_log_round_trips_through_read_with_hostile_slug(tmp_path: Path) -> None:
    """Sanity: the hostile slug survives read_events onto the event (not pre-filtered).

    This proves the sink tests above are exercising a real attack path: the slug
    is NOT scrubbed at read time — it is carried verbatim onto the StatusEvent and
    only sanitized at the reduce seam.
    """
    feature_dir = _seed_hostile_feature_dir(tmp_path)
    raw = (feature_dir / EVENTS_FILENAME).read_text(encoding="utf-8")
    assert json.loads(raw.splitlines()[0])["mission_slug"] == _HOSTILE_SLUG
