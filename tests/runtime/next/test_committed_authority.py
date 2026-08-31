"""Unit contracts for ``runtime.next.committed_authority`` (WP01 T002).

Mission next-committed-state-authority-01M1CA8W (issues #2947, #3780). Pins
the two public functions' contracts BEFORE they exist (RED-first):

- ``wp_ending`` (IC-01): single reduction -> lane + ``reason_source`` ->
  ``is_acceptable_ending``/``has_operator_provenance`` fold (C-001/C-003/C-004).
- ``mission_terminal_verdict`` (IC-02): PRIMARY-surface, ``mission_number``-keyed
  terminal/conflict/none verdict (D9/C-005).

See ``kitty-specs/next-committed-state-authority-01M1CA8W/research.md`` and
``tracer-design-decisions.md`` (D6, D9, D11, D14) for the full disambiguation.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_SLUG = "committed-authority-01KZAB"


# ---------------------------------------------------------------------------
# Event-log fixture helpers
# ---------------------------------------------------------------------------


def _seed(
    feature_dir: Path,
    wp_id: str,
    *,
    from_lane: Lane,
    to_lane: Lane,
    reason: str | None = None,
    reason_source: str | None = None,
) -> None:
    append_event(
        feature_dir,
        StatusEvent(
            event_id=f"test-{wp_id}-{to_lane}",
            mission_slug=_SLUG,
            wp_id=wp_id,
            from_lane=from_lane,
            to_lane=to_lane,
            at="2026-01-01T00:00:00+00:00",
            actor="test",
            force=True,
            execution_mode="worktree",
            reason=reason,
            reason_source=reason_source,
        ),
    )


def _write_meta(feature_dir: Path, *, mission_number: int | None) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_slug": _SLUG,
                "mission_id": "01KZAB00000000000000000AB",
                "mission_number": mission_number,
                "mission_type": "software-dev",
            }
        ),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# wp_ending (IC-01)
# ---------------------------------------------------------------------------


class TestWpEnding:
    def test_approved_is_acceptable(self, tmp_path: Path) -> None:
        from runtime.next.committed_authority import wp_ending

        _seed(tmp_path, "WP01", from_lane=Lane.IN_REVIEW, to_lane=Lane.APPROVED)

        ending = wp_ending(tmp_path, "WP01")

        assert ending.lane == "approved"
        assert ending.acceptable is True

    def test_done_is_acceptable(self, tmp_path: Path) -> None:
        from runtime.next.committed_authority import wp_ending

        _seed(tmp_path, "WP01", from_lane=Lane.APPROVED, to_lane=Lane.DONE)

        ending = wp_ending(tmp_path, "WP01")

        assert ending.lane == "done"
        assert ending.acceptable is True

    def test_canceled_with_operator_provenance_is_acceptable(self, tmp_path: Path) -> None:
        from runtime.next.committed_authority import wp_ending

        _seed(
            tmp_path,
            "WP01",
            from_lane=Lane.IN_PROGRESS,
            to_lane=Lane.CANCELED,
            reason="scope dropped by operator decision",
            reason_source="operator",
        )

        ending = wp_ending(tmp_path, "WP01")

        assert ending.lane == "canceled"
        assert ending.reason_source == "operator"
        assert ending.acceptable is True

    def test_canceled_with_none_reason_is_synthetic_and_unacceptable(
        self, tmp_path: Path
    ) -> None:
        """A synthetic cancellation (``reason: None``) stays fail-closed (#3780)."""
        from runtime.next.committed_authority import wp_ending

        _seed(
            tmp_path,
            "WP01",
            from_lane=Lane.IN_PROGRESS,
            to_lane=Lane.CANCELED,
            reason=None,
            reason_source=None,
        )

        ending = wp_ending(tmp_path, "WP01")

        assert ending.lane == "canceled"
        assert ending.reason_source == "synthetic"
        assert ending.acceptable is False

    @pytest.mark.parametrize("prefix", ["Force move to canceled", "move-task: planned -> canceled"])
    def test_canceled_with_synthetic_reason_prefix_is_unacceptable(
        self, tmp_path: Path, prefix: str
    ) -> None:
        """A CLI-synthesized reason template (no explicit ``reason_source``) is synthetic."""
        from runtime.next.committed_authority import wp_ending

        _seed(
            tmp_path,
            "WP01",
            from_lane=Lane.IN_PROGRESS,
            to_lane=Lane.CANCELED,
            reason=prefix,
            reason_source=None,
        )

        ending = wp_ending(tmp_path, "WP01")

        assert ending.reason_source == "synthetic"
        assert ending.acceptable is False

    @pytest.mark.parametrize(
        "lane", [Lane.PLANNED, Lane.CLAIMED, Lane.IN_PROGRESS, Lane.FOR_REVIEW, Lane.IN_REVIEW, Lane.BLOCKED]
    )
    def test_other_lanes_are_unacceptable(self, tmp_path: Path, lane: Lane) -> None:
        from runtime.next.committed_authority import wp_ending

        _seed(tmp_path, "WP01", from_lane=Lane.GENESIS, to_lane=lane)

        ending = wp_ending(tmp_path, "WP01")

        assert ending.lane == str(lane)
        assert ending.acceptable is False

    @pytest.mark.regression
    def test_absent_event_log_raises_fail_loud(self, tmp_path: Path) -> None:
        """A genuinely-absent committed status log RAISES — never a silent None
        (D6/C-003: the naive ``wp_snapshot_state`` swap this WP guards against)."""
        from specify_cli.status.lane_reader import CanonicalStatusNotFoundError
        from runtime.next.committed_authority import wp_ending

        missing_dir = tmp_path / "no-status-here"
        missing_dir.mkdir()

        with pytest.raises(CanonicalStatusNotFoundError):
            wp_ending(missing_dir, "WP01")

    @pytest.mark.regression
    def test_wp_ending_performs_exactly_one_reduction(self, tmp_path: Path) -> None:
        """Single-reduction property (C-004): no ``get_wp_lane`` + ``wp_snapshot_state``
        double read — exactly ONE ``reduce()`` call per ``wp_ending`` invocation."""
        import runtime.next.committed_authority as committed_authority_module

        _seed(tmp_path, "WP01", from_lane=Lane.APPROVED, to_lane=Lane.DONE)

        with patch.object(
            committed_authority_module, "reduce", wraps=committed_authority_module.reduce
        ) as reduce_spy:
            committed_authority_module.wp_ending(tmp_path, "WP01")

        reduce_spy.assert_called_once()


# ---------------------------------------------------------------------------
# mission_terminal_verdict (IC-02)
# ---------------------------------------------------------------------------


class TestMissionTerminalVerdict:
    def test_mission_number_absent_is_none(self, tmp_path: Path) -> None:
        from runtime.next.committed_authority import mission_terminal_verdict

        primary = tmp_path / "kitty-specs" / _SLUG
        _write_meta(primary, mission_number=None)

        with patch(
            "runtime.next.runtime_bridge_identity._primary_runtime_feature_dir",
            return_value=primary,
        ):
            verdict = mission_terminal_verdict(tmp_path, _SLUG)

        assert verdict == "none"

    def test_mission_number_present_all_acceptable_is_terminal(self, tmp_path: Path) -> None:
        from runtime.next.committed_authority import mission_terminal_verdict

        primary = tmp_path / "kitty-specs" / _SLUG
        _write_meta(primary, mission_number=7)
        _seed(primary, "WP01", from_lane=Lane.APPROVED, to_lane=Lane.DONE)
        _seed(primary, "WP02", from_lane=Lane.IN_REVIEW, to_lane=Lane.APPROVED)

        with patch(
            "runtime.next.runtime_bridge_identity._primary_runtime_feature_dir",
            return_value=primary,
        ):
            verdict = mission_terminal_verdict(tmp_path, _SLUG)

        assert verdict == "terminal"

    def test_mission_number_present_some_unacceptable_is_blocked_conflict(
        self, tmp_path: Path
    ) -> None:
        """FR-009: a merged mission with an unacceptable-ending WP is a conflict,
        never a silent terminal."""
        from runtime.next.committed_authority import mission_terminal_verdict

        primary = tmp_path / "kitty-specs" / _SLUG
        _write_meta(primary, mission_number=7)
        _seed(primary, "WP01", from_lane=Lane.APPROVED, to_lane=Lane.DONE)
        _seed(primary, "WP02", from_lane=Lane.GENESIS, to_lane=Lane.PLANNED)

        with patch(
            "runtime.next.runtime_bridge_identity._primary_runtime_feature_dir",
            return_value=primary,
        ):
            verdict = mission_terminal_verdict(tmp_path, _SLUG)

        assert verdict == "blocked_conflict"

    @pytest.mark.regression
    def test_committed_log_genuinely_absent_is_none_not_conflict(self, tmp_path: Path) -> None:
        """C-003/D9: a genuinely-absent committed status log is ``none``, never
        misread as a conflict."""
        from runtime.next.committed_authority import mission_terminal_verdict

        primary = tmp_path / "kitty-specs" / _SLUG
        _write_meta(primary, mission_number=7)
        # No status.events.jsonl written under `primary` at all.

        with patch(
            "runtime.next.runtime_bridge_identity._primary_runtime_feature_dir",
            return_value=primary,
        ):
            verdict = mission_terminal_verdict(tmp_path, _SLUG)

        assert verdict == "none"

    def test_never_reads_merge_state_or_merge_head(self, tmp_path: Path) -> None:
        """C-005: keyed ONLY on committed ``mission_number`` — never transient
        merge-progress artifacts. A stray ``.kittify/merge-state.json`` / ``MERGE_HEAD``
        must not influence the verdict."""
        from runtime.next.committed_authority import mission_terminal_verdict

        primary = tmp_path / "kitty-specs" / _SLUG
        _write_meta(primary, mission_number=7)
        _seed(primary, "WP01", from_lane=Lane.APPROVED, to_lane=Lane.DONE)

        # Plant a decoy merge-state artifact that must be irrelevant.
        kittify = tmp_path / ".kittify"
        kittify.mkdir(parents=True)
        (kittify / "merge-state.json").write_text("{}", encoding="utf-8")
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "MERGE_HEAD").write_text("deadbeef\n", encoding="utf-8")

        with patch(
            "runtime.next.runtime_bridge_identity._primary_runtime_feature_dir",
            return_value=primary,
        ):
            verdict = mission_terminal_verdict(tmp_path, _SLUG)

        assert verdict == "terminal"
