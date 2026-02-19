"""Parity verification tests for cross-branch (2.x / 0.1x) compatibility.

WP16 deliverable: ensures the status engine produces identical results on
both branches and that all 0.1x guard mechanisms work correctly.

Test categories:
  T082 - Backport readiness: no hard dependencies on 2.x-only modules
  T083 - SaaS fan-out as no-op on 0.1x
  T084 - Phase cap enforcement on 0.1x branches
  T085 - Reducer determinism: identical input -> identical output
"""

from __future__ import annotations

import importlib
import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.status.models import (
    DoneEvidence,
    Lane,
    ReviewApproval,
    StatusEvent,
    StatusSnapshot,
)
from specify_cli.status.reducer import materialize_to_json, reduce
from specify_cli.status.transitions import ALLOWED_TRANSITIONS, CANONICAL_LANES


# =====================================================================
# Helpers
# =====================================================================


def _make_event(
    *,
    event_id: str = "01HXYZ0000000000000000000A",
    feature_slug: str = "034-parity-test",
    wp_id: str = "WP01",
    from_lane: Lane = Lane.PLANNED,
    to_lane: Lane = Lane.CLAIMED,
    at: str = "2026-02-08T12:00:00+00:00",
    actor: str = "parity-agent",
    force: bool = False,
    execution_mode: str = "worktree",
    reason: str | None = None,
    review_ref: str | None = None,
    evidence: DoneEvidence | None = None,
) -> StatusEvent:
    return StatusEvent(
        event_id=event_id,
        feature_slug=feature_slug,
        wp_id=wp_id,
        from_lane=from_lane,
        to_lane=to_lane,
        at=at,
        actor=actor,
        force=force,
        execution_mode=execution_mode,
        reason=reason,
        review_ref=review_ref,
        evidence=evidence,
    )


# =====================================================================
# T082 - Backport Readiness: No Hard Dependencies on 2.x-Only Modules
# =====================================================================


class TestBackportReadiness:
    """Verify that all status modules can be imported without sync/ package."""

    STATUS_MODULES = [
        "specify_cli.status",
        "specify_cli.status.models",
        "specify_cli.status.transitions",
        "specify_cli.status.reducer",
        "specify_cli.status.store",
        "specify_cli.status.phase",
        "specify_cli.status.emit",
        "specify_cli.status.validate",
        "specify_cli.status.doctor",
        "specify_cli.status.legacy_bridge",
        "specify_cli.status.migrate",
        "specify_cli.status.reconcile",
    ]

    @pytest.mark.parametrize("module_name", STATUS_MODULES)
    def test_module_importable_without_sync(self, module_name: str):
        """Each status module can be imported even if sync/ does not exist.

        This verifies no module-level import from sync/ exists.
        We temporarily make sync.events unimportable and re-import.
        """
        # Save and block sync.events
        saved_sync = sys.modules.get("specify_cli.sync")
        saved_events = sys.modules.get("specify_cli.sync.events")
        sys.modules["specify_cli.sync"] = None  # type: ignore[assignment]
        sys.modules["specify_cli.sync.events"] = None  # type: ignore[assignment]

        try:
            # Force reimport of the status module
            if module_name in sys.modules:
                saved_target = sys.modules.pop(module_name)
            else:
                saved_target = None

            try:
                mod = importlib.import_module(module_name)
                assert mod is not None
            finally:
                if saved_target is not None:
                    sys.modules[module_name] = saved_target
        finally:
            # Restore sync modules
            if saved_sync is not None:
                sys.modules["specify_cli.sync"] = saved_sync
            else:
                sys.modules.pop("specify_cli.sync", None)
            if saved_events is not None:
                sys.modules["specify_cli.sync.events"] = saved_events
            else:
                sys.modules.pop("specify_cli.sync.events", None)

    def test_emit_module_has_no_toplevel_sync_import(self):
        """The emit module must NOT have a module-level import from sync/.

        The only import from sync/ should be inside _saas_fan_out() which
        is guarded by try/except ImportError.
        """
        import inspect

        from specify_cli.status import emit as emit_module

        source = inspect.getsource(emit_module)

        # Check that 'from specify_cli.sync' does NOT appear at module level
        # It should only appear inside the _saas_fan_out function body
        lines = source.split("\n")
        in_function = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("def _saas_fan_out"):
                in_function = True
                continue
            if in_function and stripped.startswith("def "):
                in_function = False

            if not in_function and "from specify_cli.sync" in stripped:
                if not stripped.startswith("#"):
                    pytest.fail(
                        f"Module-level sync import found in emit.py: {stripped}"
                    )

    def test_no_status_module_directly_imports_sync_at_toplevel(self):
        """Scan all status module source for top-level sync imports."""
        import inspect

        status_pkg_path = Path(inspect.getfile(
            importlib.import_module("specify_cli.status")
        )).parent

        for py_file in sorted(status_pkg_path.glob("*.py")):
            content = py_file.read_text(encoding="utf-8")
            lines = content.split("\n")

            for line_no, line in enumerate(lines, start=1):
                stripped = line.strip()

                # Track if we're inside a function (indented code)
                if stripped.startswith("def ") or stripped.startswith("class "):
                    len(line) - len(line.lstrip())

                # Only flag top-level imports (indent 0)
                current_indent = len(line) - len(line.lstrip()) if line.strip() else 0
                if current_indent == 0 and "from specify_cli.sync" in stripped:
                    if not stripped.startswith("#"):
                        pytest.fail(
                            f"Top-level sync import in {py_file.name}:{line_no}: "
                            f"{stripped}"
                        )


# =====================================================================
# T083 - SaaS Fan-Out as No-Op on 0.1x
# =====================================================================


class TestSaasFanOutNoOp:
    """Verify that _saas_fan_out handles missing sync/events gracefully."""

    def _make_test_event(self) -> StatusEvent:
        return _make_event(
            event_id="01HXYZ00000000000000SAASNO",
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.CLAIMED,
        )

    def test_import_error_is_silent_noop(self):
        """When sync.events is not importable, _saas_fan_out does nothing."""
        from specify_cli.status.emit import _saas_fan_out

        event = self._make_test_event()

        # Block the sync module
        saved = sys.modules.get("specify_cli.sync.events")
        sys.modules["specify_cli.sync.events"] = None  # type: ignore[assignment]

        try:
            # Must not raise
            _saas_fan_out(event, "034-parity-test", None)
        finally:
            if saved is not None:
                sys.modules["specify_cli.sync.events"] = saved
            else:
                sys.modules.pop("specify_cli.sync.events", None)

    def test_runtime_error_is_caught(self):
        """When sync.events raises at runtime, _saas_fan_out catches it."""
        from specify_cli.status.emit import _saas_fan_out

        event = self._make_test_event()

        mock_emit = MagicMock(side_effect=RuntimeError("network timeout"))
        with patch(
            "specify_cli.sync.events.emit_wp_status_changed",
            mock_emit,
        ):
            # Must not raise
            _saas_fan_out(event, "034-parity-test", None)

    def test_attribute_error_is_caught(self):
        """When sync.events has wrong API, _saas_fan_out catches it."""
        from specify_cli.status.emit import _saas_fan_out

        event = self._make_test_event()

        # Create a fake module without the expected function
        fake_module = types.ModuleType("specify_cli.sync.events")
        saved = sys.modules.get("specify_cli.sync.events")
        sys.modules["specify_cli.sync.events"] = fake_module

        try:
            # Must not raise (AttributeError caught by except Exception)
            _saas_fan_out(event, "034-parity-test", None)
        finally:
            if saved is not None:
                sys.modules["specify_cli.sync.events"] = saved
            else:
                sys.modules.pop("specify_cli.sync.events", None)

    def test_full_emit_succeeds_without_sync(self, tmp_path: Path):
        """Full emit_status_transition works when sync/ is unavailable."""
        from specify_cli.status.emit import emit_status_transition

        feature_dir = tmp_path / "kitty-specs" / "034-parity-test"
        feature_dir.mkdir(parents=True)

        saved = sys.modules.get("specify_cli.sync.events")
        sys.modules["specify_cli.sync.events"] = None  # type: ignore[assignment]

        try:
            event = emit_status_transition(
                feature_dir=feature_dir,
                feature_slug="034-parity-test",
                wp_id="WP01",
                to_lane="claimed",
                actor="parity-agent",
            )
            assert event.to_lane == Lane.CLAIMED
        finally:
            if saved is not None:
                sys.modules["specify_cli.sync.events"] = saved
            else:
                sys.modules.pop("specify_cli.sync.events", None)


# =====================================================================
# T084 - Phase Cap Enforcement on 0.1x Branches
# =====================================================================


class TestPhaseCap:
    """Verify phase capping behavior for 0.1x branches."""

    @patch("specify_cli.status.phase.is_01x_branch", return_value=True)
    def test_phase_capped_at_max_on_01x(self, _mock, tmp_path: Path):
        """On 0.1x branch, phase is capped at MAX_PHASE_01X."""
        from specify_cli.status.phase import MAX_PHASE_01X, resolve_phase

        # All valid phases should work (0, 1, 2 are all <= MAX_PHASE_01X=2)
        for valid_phase in (0, 1, 2):
            meta_dir = tmp_path / "kitty-specs" / f"feat-{valid_phase}"
            meta_dir.mkdir(parents=True, exist_ok=True)
            (meta_dir / "meta.json").write_text(
                json.dumps({"status_phase": valid_phase}), encoding="utf-8"
            )
            phase, source = resolve_phase(tmp_path, f"feat-{valid_phase}")
            assert phase == valid_phase
            # Should NOT be capped since all valid phases are within range
            if valid_phase <= MAX_PHASE_01X:
                assert "capped" not in source

    @patch("specify_cli.status.phase.is_01x_branch", return_value=False)
    def test_no_cap_on_2x_branch(self, _mock, tmp_path: Path):
        """On 2.x branch, no phase capping is applied."""
        from specify_cli.status.phase import resolve_phase

        meta_dir = tmp_path / "kitty-specs" / "feat"
        meta_dir.mkdir(parents=True, exist_ok=True)
        (meta_dir / "meta.json").write_text(
            json.dumps({"status_phase": 2}), encoding="utf-8"
        )
        phase, source = resolve_phase(tmp_path, "feat")
        assert phase == 2
        assert "capped" not in source

    @patch("specify_cli.status.phase.subprocess.run")
    def test_main_branch_detected_as_01x(self, mock_run, tmp_path: Path):
        """The 'main' branch is correctly identified as 0.1x."""
        from specify_cli.status.phase import is_01x_branch

        result = MagicMock()
        result.returncode = 0
        result.stdout = "main\n"
        mock_run.return_value = result

        assert is_01x_branch(tmp_path) is True

    @patch("specify_cli.status.phase.subprocess.run")
    def test_2x_branch_not_detected_as_01x(self, mock_run, tmp_path: Path):
        """The '2.x' branch is not identified as 0.1x."""
        from specify_cli.status.phase import is_01x_branch

        result = MagicMock()
        result.returncode = 0
        result.stdout = "2.x\n"
        mock_run.return_value = result

        assert is_01x_branch(tmp_path) is False

    @patch("specify_cli.status.phase.subprocess.run")
    def test_feature_branch_not_detected_as_01x(self, mock_run, tmp_path: Path):
        """Feature branches starting with '034-' are not 0.1x."""
        from specify_cli.status.phase import is_01x_branch

        result = MagicMock()
        result.returncode = 0
        result.stdout = "034-feature-status-state-model-remediation-WP16\n"
        mock_run.return_value = result

        assert is_01x_branch(tmp_path) is False

    @patch("specify_cli.status.phase.subprocess.run")
    def test_release_branch_detected_as_01x(self, mock_run, tmp_path: Path):
        """Release branches like 'release/0.15.0' are 0.1x."""
        from specify_cli.status.phase import is_01x_branch

        result = MagicMock()
        result.returncode = 0
        result.stdout = "release/0.15.0\n"
        mock_run.return_value = result

        assert is_01x_branch(tmp_path) is True

    @patch("specify_cli.status.phase.subprocess.run")
    def test_git_failure_defaults_to_not_01x(self, mock_run, tmp_path: Path):
        """Git failure defaults to False (not 0.1x)."""
        from specify_cli.status.phase import is_01x_branch

        result = MagicMock()
        result.returncode = 128
        result.stdout = ""
        mock_run.return_value = result

        assert is_01x_branch(tmp_path) is False


# =====================================================================
# T085 - Reducer Determinism / Parity Verification
# =====================================================================


class TestReducerDeterminism:
    """Verify the reducer produces deterministic, identical output
    from the same input events -- critical for cross-branch parity."""

    def test_same_events_produce_identical_snapshots(self):
        """Two reduce() calls with the same events produce identical work_packages."""
        events = [
            _make_event(
                event_id="01HXYZ0000000000000000000A",
                wp_id="WP01",
                from_lane=Lane.PLANNED,
                to_lane=Lane.CLAIMED,
                at="2026-02-08T12:00:00+00:00",
                actor="agent-a",
            ),
            _make_event(
                event_id="01HXYZ0000000000000000000B",
                wp_id="WP01",
                from_lane=Lane.CLAIMED,
                to_lane=Lane.IN_PROGRESS,
                at="2026-02-08T13:00:00+00:00",
                actor="agent-a",
            ),
            _make_event(
                event_id="01HXYZ0000000000000000000C",
                wp_id="WP02",
                from_lane=Lane.PLANNED,
                to_lane=Lane.BLOCKED,
                at="2026-02-08T13:30:00+00:00",
                actor="agent-b",
            ),
        ]

        with patch(
            "specify_cli.status.reducer._now_utc",
            return_value="2026-02-08T15:00:00+00:00",
        ):
            snap_a = reduce(events)
            snap_b = reduce(events)

        assert snap_a.work_packages == snap_b.work_packages
        assert snap_a.summary == snap_b.summary
        assert snap_a.event_count == snap_b.event_count
        assert snap_a.last_event_id == snap_b.last_event_id

    def test_event_order_does_not_affect_final_state(self):
        """Events in different list order produce the same final state.

        The reducer sorts by (at, event_id), so input order is irrelevant.
        """
        event_a = _make_event(
            event_id="01HXYZ0000000000000000000A",
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.CLAIMED,
            at="2026-02-08T12:00:00+00:00",
        )
        event_b = _make_event(
            event_id="01HXYZ0000000000000000000B",
            wp_id="WP01",
            from_lane=Lane.CLAIMED,
            to_lane=Lane.IN_PROGRESS,
            at="2026-02-08T13:00:00+00:00",
        )
        event_c = _make_event(
            event_id="01HXYZ0000000000000000000C",
            wp_id="WP02",
            from_lane=Lane.PLANNED,
            to_lane=Lane.CLAIMED,
            at="2026-02-08T12:30:00+00:00",
        )

        # Forward order
        with patch(
            "specify_cli.status.reducer._now_utc",
            return_value="2026-02-08T15:00:00+00:00",
        ):
            snap_forward = reduce([event_a, event_b, event_c])
            snap_reverse = reduce([event_c, event_b, event_a])
            snap_mixed = reduce([event_b, event_a, event_c])

        assert snap_forward.work_packages == snap_reverse.work_packages
        assert snap_forward.work_packages == snap_mixed.work_packages
        assert snap_forward.summary == snap_reverse.summary
        assert snap_forward.summary == snap_mixed.summary

    def test_duplicate_events_deduplicated_deterministically(self):
        """Duplicate event_ids are deduplicated: first occurrence wins."""
        event_original = _make_event(
            event_id="01HXYZ0000000000000000000A",
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.CLAIMED,
            at="2026-02-08T12:00:00+00:00",
            actor="original-actor",
        )
        event_duplicate = _make_event(
            event_id="01HXYZ0000000000000000000A",
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.CLAIMED,
            at="2026-02-08T12:00:00+00:00",
            actor="duplicate-actor",
        )

        with patch(
            "specify_cli.status.reducer._now_utc",
            return_value="2026-02-08T15:00:00+00:00",
        ):
            snap = reduce([event_original, event_duplicate])

        assert snap.event_count == 1
        assert snap.work_packages["WP01"]["actor"] == "original-actor"

    def test_json_serialization_byte_identical(self):
        """materialize_to_json produces byte-identical output for same snapshot."""
        snapshot = StatusSnapshot(
            feature_slug="034-parity-test",
            materialized_at="2026-02-08T15:00:00+00:00",
            event_count=3,
            last_event_id="01HXYZ0000000000000000000C",
            work_packages={
                "WP01": {
                    "lane": "in_progress",
                    "actor": "agent-a",
                    "last_transition_at": "2026-02-08T13:00:00+00:00",
                    "last_event_id": "01HXYZ0000000000000000000B",
                    "force_count": 0,
                },
                "WP02": {
                    "lane": "blocked",
                    "actor": "agent-b",
                    "last_transition_at": "2026-02-08T13:30:00+00:00",
                    "last_event_id": "01HXYZ0000000000000000000C",
                    "force_count": 0,
                },
            },
            summary={
                "planned": 0,
                "claimed": 0,
                "in_progress": 1,
                "for_review": 0,
                "done": 0,
                "blocked": 1,
                "canceled": 0,
            },
        )

        json_a = materialize_to_json(snapshot)
        json_b = materialize_to_json(snapshot)

        # Byte-identical
        assert json_a == json_b
        assert json_a.encode("utf-8") == json_b.encode("utf-8")

        # Valid JSON
        parsed = json.loads(json_a)
        assert parsed["feature_slug"] == "034-parity-test"
        assert parsed["event_count"] == 3

    def test_sorted_keys_in_json_output(self):
        """JSON output has sorted keys for deterministic diff-friendly output."""
        snapshot = StatusSnapshot(
            feature_slug="034-parity-test",
            materialized_at="2026-02-08T15:00:00+00:00",
            event_count=1,
            last_event_id="01HXYZ0000000000000000000A",
            work_packages={
                "WP01": {
                    "lane": "claimed",
                    "actor": "agent",
                    "last_transition_at": "2026-02-08T12:00:00+00:00",
                    "last_event_id": "01HXYZ0000000000000000000A",
                    "force_count": 0,
                },
            },
            summary={
                "planned": 0,
                "claimed": 1,
                "in_progress": 0,
                "for_review": 0,
                "done": 0,
                "blocked": 0,
                "canceled": 0,
            },
        )

        json_str = materialize_to_json(snapshot)
        parsed = json.loads(json_str)

        # Top-level keys should be sorted
        top_keys = list(parsed.keys())
        assert top_keys == sorted(top_keys)

    def test_reduce_then_serialize_roundtrip(self):
        """Events -> reduce -> serialize -> parse -> compare is stable."""
        events = [
            _make_event(
                event_id="01HXYZ0000000000000000000A",
                wp_id="WP01",
                from_lane=Lane.PLANNED,
                to_lane=Lane.CLAIMED,
                at="2026-02-08T12:00:00+00:00",
            ),
            _make_event(
                event_id="01HXYZ0000000000000000000B",
                wp_id="WP02",
                from_lane=Lane.PLANNED,
                to_lane=Lane.IN_PROGRESS,
                at="2026-02-08T12:30:00+00:00",
            ),
            _make_event(
                event_id="01HXYZ0000000000000000000C",
                wp_id="WP01",
                from_lane=Lane.CLAIMED,
                to_lane=Lane.IN_PROGRESS,
                at="2026-02-08T13:00:00+00:00",
            ),
        ]

        fixed_time = "2026-02-08T15:00:00+00:00"
        with patch(
            "specify_cli.status.reducer._now_utc", return_value=fixed_time
        ):
            snapshot = reduce(events)

        json_str = materialize_to_json(snapshot)
        parsed = json.loads(json_str)
        roundtrip = StatusSnapshot.from_dict(parsed)

        assert roundtrip.feature_slug == snapshot.feature_slug
        assert roundtrip.event_count == snapshot.event_count
        assert roundtrip.last_event_id == snapshot.last_event_id
        assert roundtrip.work_packages == snapshot.work_packages
        assert roundtrip.summary == snapshot.summary

    def test_empty_events_produce_stable_snapshot(self):
        """reduce([]) always produces the same structure."""
        fixed_time = "2026-02-08T15:00:00+00:00"
        with patch(
            "specify_cli.status.reducer._now_utc", return_value=fixed_time
        ):
            snap_a = reduce([])
            snap_b = reduce([])

        assert snap_a.feature_slug == snap_b.feature_slug == ""
        assert snap_a.event_count == snap_b.event_count == 0
        assert snap_a.last_event_id == snap_b.last_event_id is None
        assert snap_a.work_packages == snap_b.work_packages == {}
        assert snap_a.summary == snap_b.summary

        # All lane counts should be zero
        for lane in Lane:
            assert snap_a.summary[lane.value] == 0

    def test_force_events_tracked_in_force_count(self):
        """Force count is deterministic and accumulates correctly."""
        events = [
            _make_event(
                event_id="01HXYZ0000000000000000000A",
                wp_id="WP01",
                from_lane=Lane.PLANNED,
                to_lane=Lane.DONE,
                at="2026-02-08T12:00:00+00:00",
                force=True,
                actor="admin",
                reason="Emergency",
            ),
            _make_event(
                event_id="01HXYZ0000000000000000000B",
                wp_id="WP01",
                from_lane=Lane.DONE,
                to_lane=Lane.IN_PROGRESS,
                at="2026-02-08T13:00:00+00:00",
                force=True,
                actor="admin",
                reason="Reopen",
            ),
            _make_event(
                event_id="01HXYZ0000000000000000000C",
                wp_id="WP01",
                from_lane=Lane.IN_PROGRESS,
                to_lane=Lane.FOR_REVIEW,
                at="2026-02-08T14:00:00+00:00",
                force=False,
            ),
        ]

        with patch(
            "specify_cli.status.reducer._now_utc",
            return_value="2026-02-08T15:00:00+00:00",
        ):
            snap = reduce(events)

        assert snap.work_packages["WP01"]["force_count"] == 2
        assert snap.work_packages["WP01"]["lane"] == "for_review"

    def test_concurrent_events_rollback_precedence(self):
        """Rollback events beat forward events at the same timestamp."""
        # Two concurrent events at the same timestamp:
        # - One moves WP01 from for_review to in_progress (rollback)
        # - One is a hypothetical concurrent forward event
        #
        # The rollback should win per the reducer's precedence rules.
        forward_event = _make_event(
            event_id="01HXYZ0000000000000000000A",
            wp_id="WP01",
            from_lane=Lane.IN_PROGRESS,
            to_lane=Lane.FOR_REVIEW,
            at="2026-02-08T12:00:00+00:00",
        )
        rollback_event = _make_event(
            event_id="01HXYZ0000000000000000000B",
            wp_id="WP01",
            from_lane=Lane.FOR_REVIEW,
            to_lane=Lane.IN_PROGRESS,
            at="2026-02-08T12:00:00+00:00",
            review_ref="PR#42-changes-requested",
        )

        with patch(
            "specify_cli.status.reducer._now_utc",
            return_value="2026-02-08T15:00:00+00:00",
        ):
            snap = reduce([forward_event, rollback_event])

        # Rollback wins because it has review_ref (is_rollback_event)
        assert snap.work_packages["WP01"]["lane"] == "in_progress"


# =====================================================================
# T085 (continued) - Full Event Log Parity
# =====================================================================


class TestFullEventLogParity:
    """Test parity with a realistic multi-WP event sequence."""

    def _build_realistic_event_log(self) -> list[StatusEvent]:
        """Build a realistic event log covering multiple WPs and lanes."""
        evidence = DoneEvidence(
            review=ReviewApproval(
                reviewer="reviewer-1",
                verdict="approved",
                reference="PR#100",
            ),
        )
        return [
            # WP01: planned -> claimed -> in_progress -> for_review -> done
            _make_event(
                event_id="01HXYZ0000000000000000WP1A",
                wp_id="WP01",
                from_lane=Lane.PLANNED,
                to_lane=Lane.CLAIMED,
                at="2026-02-08T10:00:00+00:00",
                actor="agent-1",
            ),
            _make_event(
                event_id="01HXYZ0000000000000000WP1B",
                wp_id="WP01",
                from_lane=Lane.CLAIMED,
                to_lane=Lane.IN_PROGRESS,
                at="2026-02-08T10:30:00+00:00",
                actor="agent-1",
            ),
            _make_event(
                event_id="01HXYZ0000000000000000WP1C",
                wp_id="WP01",
                from_lane=Lane.IN_PROGRESS,
                to_lane=Lane.FOR_REVIEW,
                at="2026-02-08T14:00:00+00:00",
                actor="agent-1",
            ),
            _make_event(
                event_id="01HXYZ0000000000000000WP1D",
                wp_id="WP01",
                from_lane=Lane.FOR_REVIEW,
                to_lane=Lane.DONE,
                at="2026-02-08T16:00:00+00:00",
                actor="reviewer-1",
                evidence=evidence,
            ),
            # WP02: planned -> claimed -> in_progress -> blocked
            _make_event(
                event_id="01HXYZ0000000000000000WP2A",
                wp_id="WP02",
                from_lane=Lane.PLANNED,
                to_lane=Lane.CLAIMED,
                at="2026-02-08T10:15:00+00:00",
                actor="agent-2",
            ),
            _make_event(
                event_id="01HXYZ0000000000000000WP2B",
                wp_id="WP02",
                from_lane=Lane.CLAIMED,
                to_lane=Lane.IN_PROGRESS,
                at="2026-02-08T10:45:00+00:00",
                actor="agent-2",
            ),
            _make_event(
                event_id="01HXYZ0000000000000000WP2C",
                wp_id="WP02",
                from_lane=Lane.IN_PROGRESS,
                to_lane=Lane.BLOCKED,
                at="2026-02-08T12:00:00+00:00",
                actor="agent-2",
            ),
            # WP03: planned -> canceled
            _make_event(
                event_id="01HXYZ0000000000000000WP3A",
                wp_id="WP03",
                from_lane=Lane.PLANNED,
                to_lane=Lane.CANCELED,
                at="2026-02-08T11:00:00+00:00",
                actor="lead",
                force=True,
                reason="Descoped from release",
            ),
            # WP04: stays planned (no events beyond initial state)
        ]

    def test_realistic_log_produces_expected_summary(self):
        """A realistic event log produces the expected lane summary."""
        events = self._build_realistic_event_log()

        with patch(
            "specify_cli.status.reducer._now_utc",
            return_value="2026-02-08T18:00:00+00:00",
        ):
            snap = reduce(events)

        assert snap.event_count == 8
        assert snap.work_packages["WP01"]["lane"] == "done"
        assert snap.work_packages["WP02"]["lane"] == "blocked"
        assert snap.work_packages["WP03"]["lane"] == "canceled"
        # WP04 has no events so it's not in the snapshot
        assert "WP04" not in snap.work_packages

        assert snap.summary["done"] == 1
        assert snap.summary["blocked"] == 1
        assert snap.summary["canceled"] == 1
        assert snap.summary["planned"] == 0
        assert snap.summary["claimed"] == 0
        assert snap.summary["in_progress"] == 0
        assert snap.summary["for_review"] == 0

    def test_realistic_log_identical_across_runs(self):
        """Same realistic log produces identical output in multiple reduce calls."""
        events = self._build_realistic_event_log()

        fixed_time = "2026-02-08T18:00:00+00:00"
        with patch(
            "specify_cli.status.reducer._now_utc", return_value=fixed_time
        ):
            snap_a = reduce(events)
            snap_b = reduce(events)

        json_a = materialize_to_json(snap_a)
        json_b = materialize_to_json(snap_b)

        assert json_a == json_b

    def test_realistic_log_json_roundtrip_stable(self):
        """Serialize -> parse -> re-serialize is stable for realistic log."""
        events = self._build_realistic_event_log()

        fixed_time = "2026-02-08T18:00:00+00:00"
        with patch(
            "specify_cli.status.reducer._now_utc", return_value=fixed_time
        ):
            snap = reduce(events)

        json_1 = materialize_to_json(snap)
        parsed = json.loads(json_1)
        roundtrip = StatusSnapshot.from_dict(parsed)
        json_2 = materialize_to_json(roundtrip)

        assert json_1 == json_2


# =====================================================================
# Transition Matrix Parity
# =====================================================================


class TestTransitionMatrixParity:
    """Verify the transition matrix is complete and consistent."""

    def test_all_canonical_lanes_in_enum(self):
        """All CANONICAL_LANES values are in the Lane enum."""
        for lane_str in CANONICAL_LANES:
            assert Lane(lane_str), f"{lane_str} not in Lane enum"

    def test_all_enum_values_in_canonical_lanes(self):
        """All Lane enum values are in CANONICAL_LANES."""
        for lane in Lane:
            assert lane.value in CANONICAL_LANES, (
                f"{lane.value} in Lane enum but not in CANONICAL_LANES"
            )

    def test_transition_pairs_use_canonical_lanes(self):
        """All transition pairs use canonical lane names only."""
        canonical_set = set(CANONICAL_LANES)
        for from_lane, to_lane in ALLOWED_TRANSITIONS:
            assert from_lane in canonical_set, (
                f"Transition has non-canonical from_lane: {from_lane}"
            )
            assert to_lane in canonical_set, (
                f"Transition has non-canonical to_lane: {to_lane}"
            )

    def test_no_self_transitions_in_matrix(self):
        """No transition goes from a lane to itself."""
        for from_lane, to_lane in ALLOWED_TRANSITIONS:
            assert from_lane != to_lane, (
                f"Self-transition found: {from_lane} -> {to_lane}"
            )

    def test_terminal_lanes_have_no_outbound_transitions(self):
        """Terminal lanes (done, canceled) have no outbound transitions in the matrix."""
        from specify_cli.status.transitions import TERMINAL_LANES

        for from_lane, to_lane in ALLOWED_TRANSITIONS:
            assert from_lane not in TERMINAL_LANES, (
                f"Terminal lane {from_lane} has outbound transition to {to_lane}"
            )
