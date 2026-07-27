"""Red-first regression: backfill's ``_mission_id`` must read the PRIMARY leg.

#2966 part-1 remainder (folded into WP09 of read-side-placement-seam-migration).
Mirrors the sibling fix already landed for ``_synthesize_claim_anchor`` (Mission
E, see ``test_seed_anchor_determinism.py``): ``_mission_id`` used to read
``meta.json`` from whatever directory the caller happened to pass — in
``_build_seed_events`` that was *feature_dir*, the event-write / COORD leg. In
coordination topology the COORD leg carries no ``meta.json`` at all
(``PRIMARY_METADATA`` lives only on the PRIMARY leg — see
``src/specify_cli/core/paths.py``), so ``_mission_id`` silently degraded to the
directory-name fallback. Two observable symptoms followed:

1. Deterministic seed ``event_id``s namespaced on the COORD directory name
   instead of the mission's real ``mission_id`` ULID.
2. The written claim :class:`StatusEvent`'s own ``mission_id`` field came out
   ``None`` (``_build_seed_events`` sets it to ``None`` whenever the resolved
   mission_id equals the mission slug — exactly what the buggy fallback
   produces), which downstream readers then re-resolve via the legacy
   slug->meta.json lookup and, finding no sibling ``meta.json`` for the COORD
   directory, log a "orphaned event; mission_id will be None" warning
   (``specify_cli/status/store.py::_SlugResolver.resolve``).

The fix pins ``_mission_id`` to read *read_dir* (the PRIMARY leg) exactly as
``_synthesize_claim_anchor`` already does for the claim-anchor fallback. This
file proves both symptoms are gone. It does NOT touch or re-test
``_synthesize_claim_anchor`` itself — that half of #2966 part-1 is already
fixed and covered by ``test_seed_anchor_determinism.py``.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from specify_cli.migration import backfill_runtime_state as b
from specify_cli.status.store import read_event_stream
from tests.unit.migration._backfill_fixture import MISSION_ID, build_mission

pytestmark = [pytest.mark.fast]


def _strip_primary_metadata(feature_dir: Path) -> None:
    """Remove ``meta.json`` to simulate a genuine COORD leg (no PRIMARY_METADATA)."""
    (feature_dir / "meta.json").unlink()


def _build_coord_and_primary(tmp_path: Path) -> tuple[Path, Path]:
    """Build a distinct COORD leg (no meta.json, but WITH ``tasks/``) and a
    distinct PRIMARY ``read_dir`` (carries ``meta.json`` with a real ULID
    ``mission_id`` and its own ``tasks/``).

    Both legs are built via the shared corpus builder (so each independently
    carries a full ``tasks/WP01*.md`` legacy row + ``tasks.md`` checkboxes),
    then the COORD leg's ``meta.json`` is stripped — mirroring real coord
    topology, where PRIMARY_METADATA lives ONLY on the PRIMARY leg.
    """
    primary_dir = build_mission(tmp_path / "primary", with_transitions=False)
    coord_dir = build_mission(tmp_path / "coord", with_transitions=False)
    _strip_primary_metadata(coord_dir)
    return coord_dir, primary_dir


# ---------------------------------------------------------------------------
# T021/T022 — seed identity must namespace on the PRIMARY mission_id
# ---------------------------------------------------------------------------


def test_build_seed_events_namespaces_claim_on_primary_mission_id(tmp_path: Path) -> None:
    """``_build_seed_events`` resolves ``mission_id`` from *read_dir* (PRIMARY),
    never *feature_dir* (COORD) -- mirrors ``_synthesize_claim_anchor``'s pinned
    leg (see that function's docstring for why the anchor fallback must never
    read the COORD leg's own ``meta.json``; the same rationale applies here).
    """
    coord_dir, primary_dir = _build_coord_and_primary(tmp_path)

    legacy = b.read_legacy_runtime(primary_dir)
    anchors = b._claim_anchors(coord_dir)  # empty log -> synthesis from primary frontmatter
    transitions, _annotations = b._build_seed_events(coord_dir, primary_dir, legacy, anchors, [])

    claim = next(t for t in transitions if t.wp_id == "WP01")

    expected_event_id = b._seed_id(MISSION_ID, "WP01", "claim")
    wrong_event_id = b._seed_id(coord_dir.name, "WP01", "claim")

    assert claim.event_id != wrong_event_id, (
        "seed claim event_id must NOT namespace on the COORD dir name "
        f"({coord_dir.name!r}) -- that is exactly the bug"
    )
    assert claim.event_id == expected_event_id, (
        "seed claim event_id must namespace on the PRIMARY mission_id "
        f"({MISSION_ID!r}), read from read_dir"
    )
    assert claim.mission_id == MISSION_ID, (
        "seed claim event must carry the resolved PRIMARY mission_id, not None"
    )


def test_mission_id_reads_read_dir_not_feature_dir(tmp_path: Path) -> None:
    """Direct unit pin on ``_mission_id``'s pinned leg (post-fix signature).

    ``_mission_id(read_dir)`` must resolve the ULID from *read_dir*'s
    ``meta.json`` regardless of what ``feature_dir`` looks like -- there is no
    "feature_dir" parameter anymore, only ``read_dir``, exactly mirroring
    ``_synthesize_claim_anchor(read_dir, runtime)``.
    """
    coord_dir, primary_dir = _build_coord_and_primary(tmp_path)

    assert b._mission_id(primary_dir) == MISSION_ID
    # The COORD leg has no meta.json at all -> degrades to its own dir name,
    # which is a DIFFERENT (and wrong, for seeding purposes) value.
    assert b._mission_id(coord_dir) == coord_dir.name
    assert b._mission_id(coord_dir) != MISSION_ID


# ---------------------------------------------------------------------------
# T023 — green: full public path, on-disk bytes + no orphaned-event warning
# ---------------------------------------------------------------------------


def test_backfill_runtime_state_seeds_from_primary_mission_id(tmp_path: Path) -> None:
    """End-to-end through the public seam: the written claim event on the
    COORD leg's ``status.events.jsonl`` carries the PRIMARY-namespaced
    ``event_id`` and a populated (non-``None``) ``mission_id`` field.
    """
    coord_dir, primary_dir = _build_coord_and_primary(tmp_path)

    result = b.backfill_runtime_state(coord_dir, read_dir=primary_dir)
    assert result.action == "wrote", result.reason

    expected_event_id = b._seed_id(MISSION_ID, "WP01", "claim")
    events_path = coord_dir / "status.events.jsonl"
    rows = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]

    claim_row = next((r for r in rows if r.get("event_id") == expected_event_id), None)
    assert claim_row is not None, (
        "expected a claim seed namespaced on the PRIMARY mission_id "
        f"({MISSION_ID!r}) but none was found on disk: {rows!r}"
    )
    assert claim_row["mission_id"] == MISSION_ID


def test_backfill_runtime_state_avoids_orphaned_event_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Reading the seeded COORD event log back must not warn "orphaned event".

    That warning (``specify_cli/status/store.py::_SlugResolver.resolve``) fires
    only when a raw event's ``mission_id`` field is absent/``None`` and the
    slug-based fallback resolution finds no sibling ``meta.json`` -- exactly
    the shape a COORD-leg seed produces under the pre-fix bug (the seed's own
    ``mission_id`` field was ``None`` because the resolved mission_id equalled
    the mission slug).
    """
    coord_dir, primary_dir = _build_coord_and_primary(tmp_path)

    result = b.backfill_runtime_state(coord_dir, read_dir=primary_dir)
    assert result.action == "wrote", result.reason

    caplog.set_level(logging.WARNING, logger="specify_cli.status.store")
    read_event_stream(coord_dir)

    assert "orphaned event" not in caplog.text, caplog.text
