"""Checkout-identity reconciliation for ``doctor mission-state`` (WP04).

FR-004 / FR-009; #3051 / #3541. Red-first (T012): from a foreign lane worktree
the base behavior is a silent primary canonicalization on ``--fix`` and a
false-green on ``--audit`` (both modes re-anchor to the primary and read it at
*both* ends). After WP04:

* ``--fix`` from a foreign lane **fails closed** via ``MissionStateWriteRefused``
  (carrying the WP01 ``FailClosedRefusal``), naming the primary and leaving it
  unchanged — the deliberate #2320 primary status-home is preserved, never
  silently written from a lane.
* ``--audit`` computes the honest invoking-checkout-vs-primary disagreement from
  the invoking checkout's *own* ``.git`` (the WP01 guard), never a false-green
  from reading the redirected primary at both ends.

FR-009 manifest honesty (T014): the canonicalization manifest enumerates every
touched field, **including removed fields**.
"""

from __future__ import annotations

import pytest

from specify_cli.core.checkout_identity import FailClosedRefusal
from specify_cli.migration.canonicalization import MigrationContext
from specify_cli.migration.mission_state import (
    CheckoutDisagreement,
    MissionStateWriteRefused,
    _rule_normalize_lanes,
    audit_invocation_disagreement,
    enforce_primary_write_ownership,
)

pytestmark = pytest.mark.regression

_SLUG = "worktree-root-resolution-check"


def _write(path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_primary_and_lane(tmp_path, *, primary_status: str, lane_status: str):
    """Fabricate a primary checkout and a linked lane worktree pointing at it.

    ``resolve_checkout_identity`` parses ``.git`` directly (stdlib only, no real
    git), so a ``.git`` directory on the primary plus a ``gitdir:`` pointer file
    on the lane is enough to make the guard resolve ownership deterministically.
    """
    primary = (tmp_path / "primary").resolve()
    lane = (tmp_path / "lane-d").resolve()
    # Primary owns itself: a real ``.git`` *directory*.
    (primary / ".git" / "worktrees" / "lane-d").mkdir(parents=True, exist_ok=True)
    # Lane is a linked worktree: a ``.git`` *file* pointing into the primary.
    lane.mkdir(parents=True, exist_ok=True)
    _write(lane / ".git", f"gitdir: {primary}/.git/worktrees/lane-d\n")
    # Divergent mission state on each side.
    _write(primary / "kitty-specs" / _SLUG / "status.json", primary_status)
    _write(lane / "kitty-specs" / _SLUG / "status.json", lane_status)
    return primary, lane


# --- T012: --fix fail-closed refusal -----------------------------------------


def test_foreign_lane_fix_fails_closed_naming_primary(tmp_path) -> None:
    """A foreign-lane ``--fix`` refuses, names the primary, leaves it unchanged."""
    primary, lane = _make_primary_and_lane(
        tmp_path, primary_status='{"v": "primary"}', lane_status='{"v": "lane"}'
    )
    primary_status_before = (primary / "kitty-specs" / _SLUG / "status.json").read_text(
        encoding="utf-8"
    )

    with pytest.raises(MissionStateWriteRefused) as exc:
        # resolved_root is the re-anchored #2320 primary (kept, not flipped).
        enforce_primary_write_ownership(lane, primary)

    assert isinstance(exc.value.refusal, FailClosedRefusal)
    assert exc.value.refusal.refusal_path == primary
    assert str(primary) in str(exc.value)  # message names the primary verbatim
    # Primary status home is untouched — no silent canonicalization, no lane write.
    assert (
        primary / "kitty-specs" / _SLUG / "status.json"
    ).read_text(encoding="utf-8") == primary_status_before


def test_owner_fix_proceeds_without_refusal(tmp_path) -> None:
    """An owner invocation (cwd IS the primary) is a silent no-op — #2320 fix path."""
    primary, _lane = _make_primary_and_lane(
        tmp_path, primary_status='{"v": "primary"}', lane_status='{"v": "lane"}'
    )

    # Must NOT raise: owner writes to the primary it owns.
    enforce_primary_write_ownership(primary, primary)


def test_explicit_root_that_is_not_the_invocation_primary_is_ignored(tmp_path) -> None:
    """A resolved target that is not this invocation's re-anchored primary is a no-op.

    Guards the explicit-``repo_root=``/fixture callers (and this test suite, which
    itself runs from a lane worktree): the enforcement keys off the guard's
    ``canonical_target``, so an unrelated target never trips a refusal.
    """
    _primary, lane = _make_primary_and_lane(
        tmp_path, primary_status="{}", lane_status="{}"
    )
    unrelated = (tmp_path / "unrelated").resolve()
    unrelated.mkdir(parents=True, exist_ok=True)

    enforce_primary_write_ownership(lane, unrelated)  # must not raise


# --- T012: --audit honest disagreement ---------------------------------------


def test_foreign_lane_audit_reports_honest_disagreement(tmp_path) -> None:
    """From a lane, audit reports the invoking-vs-primary mismatch (no false-green)."""
    primary, lane = _make_primary_and_lane(
        tmp_path, primary_status='{"v": "primary"}', lane_status='{"v": "lane"}'
    )

    disagreements = audit_invocation_disagreement(lane, primary, mission=_SLUG)

    assert disagreements, "a differing lane checkout must NOT report agreement"
    assert all(isinstance(d, CheckoutDisagreement) for d in disagreements)
    statuses = {(d.mission_slug, d.artifact) for d in disagreements}
    assert (_SLUG, "status.json") in statuses
    row = next(d for d in disagreements if d.artifact == "status.json")
    assert row.invoking_sha256 != row.primary_sha256


def test_agreeing_lane_audit_reports_no_disagreement(tmp_path) -> None:
    """Identical state on both sides yields no disagreement (no false-red)."""
    same = '{"v": "identical"}'
    primary, lane = _make_primary_and_lane(
        tmp_path, primary_status=same, lane_status=same
    )

    assert audit_invocation_disagreement(lane, primary, mission=_SLUG) == []


def test_owner_audit_never_disagrees_with_itself(tmp_path) -> None:
    """An owner audit (cwd IS the primary) has no cross-checkout read to disagree."""
    primary, _lane = _make_primary_and_lane(
        tmp_path, primary_status='{"v": "primary"}', lane_status='{"v": "lane"}'
    )

    assert audit_invocation_disagreement(primary, primary, mission=_SLUG) == []


# --- T014: manifest honesty (FR-009) -----------------------------------------


def _ctx() -> MigrationContext:
    return MigrationContext(
        mission_slug=_SLUG,
        mission_id="01J0000000000000000MANIFEST",
        line_number=1,
    )


def _normalized_row_with_extra_field() -> dict[str, object]:
    return {
        "event_id": "01J000000000000000000EVENT",
        "mission_slug": _SLUG,
        "wp_id": "WP04",
        "from_lane": "planned",
        "to_lane": "claimed",
        "at": "2026-08-18T20:00:00+00:00",
        "actor": "claude",
        "force": False,
        "execution_mode": "worktree",
        # A field the closed allowlist drops — the manifest must say so.
        "legacy_dropped_field": "value-that-gets-removed",
    }


def test_manifest_enumerates_removed_field(tmp_path) -> None:
    """A repair that drops a field lists it as ``removed_field:<key>`` (FR-009)."""
    result = _rule_normalize_lanes(_normalized_row_with_extra_field(), _ctx())

    assert result.error is None
    assert "removed_field:legacy_dropped_field" in result.actions
    # The dropped field is genuinely gone from the canonical row.
    assert "legacy_dropped_field" not in result.state


def test_manifest_reports_no_removal_when_nothing_dropped(tmp_path) -> None:
    """A row with only allowlisted fields records no phantom ``removed_field``."""
    row = _normalized_row_with_extra_field()
    del row["legacy_dropped_field"]

    result = _rule_normalize_lanes(row, _ctx())

    assert result.error is None
    assert not any(a.startswith("removed_field:") for a in result.actions)
