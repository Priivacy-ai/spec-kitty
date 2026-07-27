"""WP01 red-first regression: claim-anchor payload determinism across legs.

Runtime-state seed **identity** (``deterministic_ulid = sha256(mission_id |
wp_id | field)``) has always been leg-independent — it carries no wall-clock
or randomness. The seed **payload**, specifically the resolved claim ``at``
anchor, was not: :func:`_synthesize_claim_anchor` fell back to reading
``meta.json.created_at`` from whichever directory happened to be the
*event-write* leg (``feature_dir``) rather than the mission's PRIMARY leg
(``read_dir`` — where ``tasks/`` frontmatter and ``meta.json`` canonically
live). Under coordination topology the two legs are genuinely different
directories, so the two stamp callers (``spec-kitty merge`` and the WP02
accept-time seam) could synthesize two different anchors for the exact same
mission, producing a flipped-but-unverifiable corpus (R5 / NFR-004).

This test seeds the same fixture mission from two distinct COORD write-leg
directories against one shared PRIMARY read leg and asserts the produced
``status.events.jsonl`` bytes are identical -- proving the anchor is pinned
to the PRIMARY leg regardless of what (if anything) the COORD leg's own
``meta.json`` says.
"""

from __future__ import annotations

import json
from pathlib import Path

from specify_cli.migration.backfill_runtime_state import backfill_runtime_state
from tests.unit.migration._backfill_fixture import MISSION_ID, SLUG, build_mission

_UNPARSEABLE_SHELL_PID_CREATED_AT = "not-a-timestamp"
_PRIMARY_CREATED_AT = "2026-01-01T00:00:00+00:00"
_FOREIGN_COORD_CREATED_AT = "2099-01-01T00:00:00+00:00"


def _events_bytes(feature_dir: Path) -> bytes:
    path = feature_dir / "status.events.jsonl"
    return path.read_bytes() if path.exists() else b""


def _write_coord_leg_meta(coord_dir: Path, *, created_at: str | None) -> None:
    coord_dir.mkdir(parents=True, exist_ok=True)
    meta: dict[str, str] = {"mission_id": MISSION_ID, "mission_slug": SLUG}
    if created_at is not None:
        meta["created_at"] = created_at
    (coord_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")


def test_synthesized_claim_anchor_is_byte_identical_across_leg_contexts(
    tmp_path: Path,
) -> None:
    """R5 / NFR-004: same PRIMARY leg -> byte-identical seed payload.

    Two COORD write legs disagree about ``created_at`` in their *own*
    ``meta.json`` (one omits it, the other carries a foreign/wrong value).
    Neither disagreement may leak into the seeded claim anchor: it must be
    resolved from the shared PRIMARY leg (``read_dir``) every time.
    """
    primary_dir = build_mission(
        tmp_path / "primary",
        with_transitions=False,  # no event-log anchor -> forces synthesis
        shell_pid_created_at=_UNPARSEABLE_SHELL_PID_CREATED_AT,
        meta_created_at=_PRIMARY_CREATED_AT,
    )

    coord_a = tmp_path / "coord-a" / SLUG
    _write_coord_leg_meta(coord_a, created_at=None)

    coord_b = tmp_path / "coord-b" / SLUG
    _write_coord_leg_meta(coord_b, created_at=_FOREIGN_COORD_CREATED_AT)

    result_a = backfill_runtime_state(coord_a, read_dir=primary_dir)
    result_b = backfill_runtime_state(coord_b, read_dir=primary_dir)

    assert result_a.action == "wrote", result_a.reason
    assert result_b.action == "wrote", result_b.reason

    bytes_a = _events_bytes(coord_a)
    bytes_b = _events_bytes(coord_b)

    assert bytes_a, "expected a claim seed synthesized from the PRIMARY leg"
    assert bytes_a == bytes_b, (
        "seed payload diverged across leg contexts (R5): the claim anchor "
        "leaked from the COORD write leg's own meta.json instead of the "
        "shared PRIMARY read leg"
    )
    assert _PRIMARY_CREATED_AT.encode() in bytes_a
    assert _FOREIGN_COORD_CREATED_AT.encode() not in bytes_a


def test_synthesized_claim_anchor_stable_for_a_fixed_created_at(
    tmp_path: Path,
) -> None:
    """Machine-independence: re-seeding from a fresh COORD leg with the same
    fixed PRIMARY ``created_at`` reproduces the exact same anchor byte-for-
    byte -- no wall-clock, no host-local drift.
    """
    primary_dir = build_mission(
        tmp_path / "primary",
        with_transitions=False,
        shell_pid_created_at=_UNPARSEABLE_SHELL_PID_CREATED_AT,
        meta_created_at=_PRIMARY_CREATED_AT,
    )

    coord_first = tmp_path / "coord-first" / SLUG
    coord_first.mkdir(parents=True)
    coord_second = tmp_path / "coord-second" / SLUG
    coord_second.mkdir(parents=True)

    backfill_runtime_state(coord_first, read_dir=primary_dir)
    backfill_runtime_state(coord_second, read_dir=primary_dir)

    assert _events_bytes(coord_first) == _events_bytes(coord_second)


def test_anchor_pin_does_not_alter_an_already_migrated_mission(tmp_path: Path) -> None:
    """C-003: a mission whose claim anchor already comes from the event log
    (no synthesis involved) must be untouched by the anchor-pin change --
    re-running backfill on it is a byte-for-byte no-op, as before.
    """
    feature_dir = build_mission(tmp_path / "migrated", with_transitions=True)

    first = backfill_runtime_state(feature_dir)
    assert first.action == "wrote"
    before = _events_bytes(feature_dir)

    second = backfill_runtime_state(feature_dir)
    assert second.action == "skip"
    after = _events_bytes(feature_dir)

    assert before == after
