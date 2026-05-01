"""Tests for is_completion_allowed() — complete decision matrix coverage.

Each test corresponds to one row (or sub-row) of the gate decision matrix
defined in gate_api.md and data-model.md.

Decision matrix covered:
  autonomous × {none, completed, skipped, skipped+charter, failed, only-requested}
  human_in_command × {none, completed-runtime, completed-human, skipped, failed}

Also covers:
  - Determinism replay (NFR-008)
  - Performance smoke (NFR-007: < 500 ms with completed present; generous slack 1500 ms)
  - Charter authorizes autonomous-skip
  - Typed errors (MissionIdentityMissing, EventLogUnreadable)
  - before_mark_done thin caller (T024)
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from specify_cli.retrospective.gate import (
    EventLogUnreadable,
    GateDecision,
    MissionIdentityMissing,
    is_completion_allowed,
)
from specify_cli.retrospective.schema import Mode, ModeSourceSignal
from specify_cli.next._internal_runtime.retrospective_hook import (
    MissionCompletionBlocked,
    before_mark_done,
)

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_MISSION_ID = "01KQ6YEGT4YBZ3GZF7X680KQ3V"  # 26-char ULID (test fixture)

# ULID event ids — monotonically increasing for tiebreak correctness.
_EID_1 = "01KQ6YEGT4YBZ3GZF7X680KQ3A"
_EID_2 = "01KQ6YEGT4YBZ3GZF7X680KQ3B"
_EID_3 = "01KQ6YEGT4YBZ3GZF7X680KQ3C"

# ---------------------------------------------------------------------------
# Mode helpers
# ---------------------------------------------------------------------------


def _mode_autonomous() -> Mode:
    return Mode(
        value="autonomous",
        source_signal=ModeSourceSignal(kind="explicit_flag", evidence="autonomous"),
    )


def _mode_hic() -> Mode:
    return Mode(
        value="human_in_command",
        source_signal=ModeSourceSignal(kind="explicit_flag", evidence="human_in_command"),
    )


# ---------------------------------------------------------------------------
# Event log builder
# ---------------------------------------------------------------------------


def _write_events(
    feature_dir: Path,
    events: list[dict[str, object]],
) -> Path:
    """Write events to status.events.jsonl in feature_dir.

    Each entry in ``events`` is a complete envelope dict (sorted-key JSON).
    Returns the path to the written file.
    """
    events_path = feature_dir / "status.events.jsonl"
    feature_dir.mkdir(parents=True, exist_ok=True)
    with events_path.open("w", encoding="utf-8") as fh:
        for env in events:
            fh.write(json.dumps(env, sort_keys=True) + "\n")
    return events_path


def _make_envelope(
    event_name: str,
    event_id: str,
    at: str,
    actor_kind: str = "human",
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build a minimal retrospective event envelope."""
    return {
        "actor": {"id": "test-actor", "kind": actor_kind, "profile_id": None},
        "at": at,
        "event_id": event_id,
        "event_name": event_name,
        "mid8": _MISSION_ID[:8],
        "mission_id": _MISSION_ID,
        "mission_slug": "test-mission",
        "payload": payload or {},
    }


def _requested_envelope(
    event_id: str,
    at: str,
    actor_kind: str = "human",
) -> dict[str, object]:
    return _make_envelope(
        event_name="retrospective.requested",
        event_id=event_id,
        at=at,
        actor_kind=actor_kind,
        payload={
            "mode": {"source_signal": {"evidence": "test", "kind": "explicit_flag"}, "value": "autonomous"},
            "requested_by": {"id": "test", "kind": actor_kind, "profile_id": None},
            "terminus_step_id": "step-001",
        },
    )


def _completed_envelope(
    event_id: str,
    at: str,
    actor_kind: str = "human",
) -> dict[str, object]:
    return _make_envelope(
        event_name="retrospective.completed",
        event_id=event_id,
        at=at,
        actor_kind=actor_kind,
        payload={
            "findings_summary": {"gaps": 0, "helped": 1, "not_helpful": 0},
            "proposals_count": 0,
            "record_hash": "abc123",
            "record_path": ".kittify/missions/test/retrospective.yaml",
        },
    )


def _skipped_envelope(
    event_id: str,
    at: str,
    actor_kind: str = "human",
) -> dict[str, object]:
    return _make_envelope(
        event_name="retrospective.skipped",
        event_id=event_id,
        at=at,
        actor_kind=actor_kind,
        payload={
            "record_path": ".kittify/missions/test/retrospective.yaml",
            "skip_reason": "Operator explicit skip",
            "skipped_by": {"id": "op", "kind": actor_kind, "profile_id": None},
        },
    )


def _failed_envelope(
    event_id: str,
    at: str,
    actor_kind: str = "human",
) -> dict[str, object]:
    return _make_envelope(
        event_name="retrospective.failed",
        event_id=event_id,
        at=at,
        actor_kind=actor_kind,
        payload={
            "failure_code": "facilitator_error",
            "message": "Facilitator crashed.",
            "record_path": None,
        },
    )


def _started_envelope(
    event_id: str,
    at: str,
    actor_kind: str = "human",
) -> dict[str, object]:
    return _make_envelope(
        event_name="retrospective.started",
        event_id=event_id,
        at=at,
        actor_kind=actor_kind,
        payload={"action_id": "action-001", "facilitator_profile_id": "fp-001"},
    )


# ---------------------------------------------------------------------------
# Charter helper
# ---------------------------------------------------------------------------


def _write_charter(
    repo_root: Path,
    mode_value: str = "autonomous",
    autonomous_allow_skip: str | None = None,
) -> None:
    """Write .kittify/charter/charter.md with optional autonomous_allow_skip.

    The charter uses YAML frontmatter.  Values with colons must be wrapped
    in YAML double-quotes (not Python repr), e.g. ``"mode-policy:foo"``.
    """
    charter_dir = repo_root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"mode: {mode_value}"]
    if autonomous_allow_skip is not None:
        # Use YAML double-quotes so colons inside the value don't confuse the parser.
        lines.append(f'autonomous_allow_skip: "{autonomous_allow_skip}"')
    lines += ["---", "", "# Charter", ""]
    (charter_dir / "charter.md").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# AUTONOMOUS MODE TESTS
# ---------------------------------------------------------------------------


class TestAutonomousMode:
    """Decision matrix rows for autonomous mode."""

    def test_no_events_blocks_missing_completion(self, tmp_path: Path) -> None:
        """autonomous + no retro events → block, missing_completion_autonomous."""
        feature_dir = tmp_path / "feature"
        feature_dir.mkdir()
        # Empty events file
        (feature_dir / "status.events.jsonl").write_text("", encoding="utf-8")

        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_autonomous(),
        )

        assert decision.allow_completion is False
        assert decision.reason.code == "missing_completion_autonomous"
        assert decision.mode.value == "autonomous"

    def test_no_file_blocks_missing_completion(self, tmp_path: Path) -> None:
        """autonomous + missing events file → block, missing_completion_autonomous."""
        feature_dir = tmp_path / "feature"
        feature_dir.mkdir()
        # No status.events.jsonl

        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_autonomous(),
        )

        assert decision.allow_completion is False
        assert decision.reason.code == "missing_completion_autonomous"

    def test_only_requested_started_blocks(self, tmp_path: Path) -> None:
        """autonomous + only requested/started → block, missing_completion_autonomous."""
        feature_dir = tmp_path / "feature"
        _write_events(
            feature_dir,
            [
                _requested_envelope(_EID_1, "2026-04-27T09:00:00+00:00"),
                _started_envelope(_EID_2, "2026-04-27T09:01:00+00:00"),
            ],
        )

        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_autonomous(),
        )

        assert decision.allow_completion is False
        assert decision.reason.code == "missing_completion_autonomous"

    def test_completed_event_allows(self, tmp_path: Path) -> None:
        """autonomous + retrospective.completed → allow, completed_present."""
        feature_dir = tmp_path / "feature"
        _write_events(
            feature_dir,
            [
                _requested_envelope(_EID_1, "2026-04-27T09:00:00+00:00"),
                _completed_envelope(_EID_2, "2026-04-27T09:05:00+00:00"),
            ],
        )

        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_autonomous(),
        )

        assert decision.allow_completion is True
        assert decision.reason.code == "completed_present"
        assert decision.mode.value == "autonomous"

    def test_skipped_blocks_silent_skip(self, tmp_path: Path) -> None:
        """autonomous + retrospective.skipped (no charter) → block, silent_skip_attempted."""
        feature_dir = tmp_path / "feature"
        _write_events(
            feature_dir,
            [
                _skipped_envelope(_EID_1, "2026-04-27T09:00:00+00:00"),
            ],
        )

        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_autonomous(),
        )

        assert decision.allow_completion is False
        assert decision.reason.code == "silent_skip_attempted"
        assert _EID_1 in decision.reason.blocking_event_ids

    def test_skipped_with_charter_allows(self, tmp_path: Path) -> None:
        """autonomous + retrospective.skipped + charter clause → allow, skipped_permitted."""
        feature_dir = tmp_path / "feature"
        _write_events(
            feature_dir,
            [
                _skipped_envelope(_EID_1, "2026-04-27T09:00:00+00:00"),
            ],
        )
        _write_charter(
            tmp_path,
            mode_value="autonomous",
            autonomous_allow_skip="mode-policy:autonomous-allow-skip",
        )

        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_autonomous(),
        )

        assert decision.allow_completion is True
        assert decision.reason.code == "skipped_permitted"
        assert decision.reason.charter_clause_ref == "mode-policy:autonomous-allow-skip"

    def test_failed_blocks_facilitator_failure(self, tmp_path: Path) -> None:
        """autonomous + retrospective.failed → block, facilitator_failure."""
        feature_dir = tmp_path / "feature"
        _write_events(
            feature_dir,
            [
                _failed_envelope(_EID_1, "2026-04-27T09:00:00+00:00"),
            ],
        )

        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_autonomous(),
        )

        assert decision.allow_completion is False
        assert decision.reason.code == "facilitator_failure"
        assert _EID_1 in decision.reason.blocking_event_ids


# ---------------------------------------------------------------------------
# HUMAN_IN_COMMAND MODE TESTS
# ---------------------------------------------------------------------------


class TestHumanInCommandMode:
    """Decision matrix rows for human_in_command mode."""

    def test_no_events_blocks_silent_auto_run(self, tmp_path: Path) -> None:
        """HiC + no events → block, silent_auto_run_attempted."""
        feature_dir = tmp_path / "feature"
        feature_dir.mkdir()

        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_hic(),
        )

        assert decision.allow_completion is False
        assert decision.reason.code == "silent_auto_run_attempted"

    def test_completed_human_requested_allows(self, tmp_path: Path) -> None:
        """HiC + completed (operator-driven requested) → allow, completed_present_hic."""
        feature_dir = tmp_path / "feature"
        _write_events(
            feature_dir,
            [
                _requested_envelope(_EID_1, "2026-04-27T09:00:00+00:00", actor_kind="human"),
                _completed_envelope(_EID_2, "2026-04-27T09:05:00+00:00", actor_kind="human"),
            ],
        )

        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_hic(),
        )

        assert decision.allow_completion is True
        assert decision.reason.code == "completed_present_hic"
        assert decision.mode.value == "human_in_command"

    def test_completed_agent_requested_allows(self, tmp_path: Path) -> None:
        """HiC + completed where upstream requested actor.kind='agent' → allow.

        'agent' is not 'runtime', so it is treated as operator-driven.
        """
        feature_dir = tmp_path / "feature"
        _write_events(
            feature_dir,
            [
                _requested_envelope(_EID_1, "2026-04-27T09:00:00+00:00", actor_kind="agent"),
                _completed_envelope(_EID_2, "2026-04-27T09:05:00+00:00", actor_kind="agent"),
            ],
        )

        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_hic(),
        )

        assert decision.allow_completion is True
        assert decision.reason.code == "completed_present_hic"

    def test_completed_runtime_requested_blocks(self, tmp_path: Path) -> None:
        """HiC + completed (runtime-driven requested) → block, silent_auto_run_attempted."""
        feature_dir = tmp_path / "feature"
        _write_events(
            feature_dir,
            [
                _requested_envelope(_EID_1, "2026-04-27T09:00:00+00:00", actor_kind="runtime"),
                _completed_envelope(_EID_2, "2026-04-27T09:05:00+00:00", actor_kind="runtime"),
            ],
        )

        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_hic(),
        )

        assert decision.allow_completion is False
        assert decision.reason.code == "silent_auto_run_attempted"
        assert _EID_2 in decision.reason.blocking_event_ids

    def test_skipped_allows_skipped_permitted(self, tmp_path: Path) -> None:
        """HiC + retrospective.skipped → allow, skipped_permitted."""
        feature_dir = tmp_path / "feature"
        _write_events(
            feature_dir,
            [
                _skipped_envelope(_EID_1, "2026-04-27T09:00:00+00:00"),
            ],
        )

        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_hic(),
        )

        assert decision.allow_completion is True
        assert decision.reason.code == "skipped_permitted"

    def test_failed_blocks_facilitator_failure(self, tmp_path: Path) -> None:
        """HiC + retrospective.failed → block, facilitator_failure."""
        feature_dir = tmp_path / "feature"
        _write_events(
            feature_dir,
            [
                _failed_envelope(_EID_1, "2026-04-27T09:00:00+00:00"),
            ],
        )

        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_hic(),
        )

        assert decision.allow_completion is False
        assert decision.reason.code == "facilitator_failure"
        assert _EID_1 in decision.reason.blocking_event_ids


# ---------------------------------------------------------------------------
# DETERMINISM (NFR-008)
# ---------------------------------------------------------------------------


class TestDeterminism:
    """Gate must produce identical decisions for identical inputs."""

    def test_determinism_autonomous_completed(self, tmp_path: Path) -> None:
        """Same event log in autonomous mode → identical GateDecision twice."""
        feature_dir = tmp_path / "feature"
        _write_events(
            feature_dir,
            [
                _requested_envelope(_EID_1, "2026-04-27T09:00:00+00:00"),
                _completed_envelope(_EID_2, "2026-04-27T09:05:00+00:00"),
            ],
        )

        d1 = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_autonomous(),
        )
        d2 = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_autonomous(),
        )

        assert d1.model_dump() == d2.model_dump()

    def test_determinism_hic_skipped(self, tmp_path: Path) -> None:
        """Same event log in HiC mode → identical GateDecision twice."""
        feature_dir = tmp_path / "feature"
        _write_events(
            feature_dir,
            [
                _skipped_envelope(_EID_1, "2026-04-27T09:00:00+00:00"),
            ],
        )

        d1 = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_hic(),
        )
        d2 = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_hic(),
        )

        assert d1.model_dump() == d2.model_dump()

    def test_determinism_blocking_event_ids_order(self, tmp_path: Path) -> None:
        """blocking_event_ids must be in stable order across two calls."""
        feature_dir = tmp_path / "feature"
        _write_events(
            feature_dir,
            [
                _failed_envelope(_EID_1, "2026-04-27T09:00:00+00:00"),
            ],
        )

        d1 = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_autonomous(),
        )
        d2 = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_autonomous(),
        )

        assert d1.reason.blocking_event_ids == d2.reason.blocking_event_ids


# ---------------------------------------------------------------------------
# PERFORMANCE SMOKE (NFR-007)
# ---------------------------------------------------------------------------


class TestPerformance:
    """Gate with retrospective.completed present must return in < 1500 ms (generous CI slack)."""

    def test_perf_autonomous_completed(self, tmp_path: Path) -> None:
        """Gate with completed event returns fast (target < 500 ms; CI slack 1500 ms)."""
        feature_dir = tmp_path / "feature"
        _write_events(
            feature_dir,
            [
                _requested_envelope(_EID_1, "2026-04-27T09:00:00+00:00"),
                _completed_envelope(_EID_2, "2026-04-27T09:05:00+00:00"),
            ],
        )

        start = time.perf_counter()
        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_autonomous(),
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert decision.allow_completion is True
        assert elapsed_ms < 1500, f"Gate took {elapsed_ms:.1f} ms; target < 1500 ms"


# ---------------------------------------------------------------------------
# TYPED ERROR TESTS
# ---------------------------------------------------------------------------


class TestTypedErrors:
    """Gate raises typed errors; never silently converts to allow_completion=True."""

    def test_empty_mission_id_raises(self, tmp_path: Path) -> None:
        feature_dir = tmp_path / "feature"
        feature_dir.mkdir()

        with pytest.raises(MissionIdentityMissing):
            is_completion_allowed(
                "",
                feature_dir=feature_dir,
                repo_root=tmp_path,
                mode_override=_mode_autonomous(),
            )

    def test_malformed_jsonl_raises(self, tmp_path: Path) -> None:
        feature_dir = tmp_path / "feature"
        feature_dir.mkdir()
        events_path = feature_dir / "status.events.jsonl"
        events_path.write_text("this is not json\n", encoding="utf-8")

        with pytest.raises(EventLogUnreadable):
            is_completion_allowed(
                _MISSION_ID,
                feature_dir=feature_dir,
                repo_root=tmp_path,
                mode_override=_mode_autonomous(),
            )

    def test_empty_lines_in_jsonl_are_skipped(self, tmp_path: Path) -> None:
        """Empty lines in status.events.jsonl are silently skipped."""
        feature_dir = tmp_path / "feature"
        feature_dir.mkdir()
        events_path = feature_dir / "status.events.jsonl"
        # Mix empty lines with a valid completed event.
        completed = json.dumps(_completed_envelope(_EID_1, "2026-04-27T09:00:00+00:00"), sort_keys=True)
        events_path.write_text(
            f"\n\n{completed}\n\n",
            encoding="utf-8",
        )

        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_autonomous(),
        )

        assert decision.allow_completion is True
        assert decision.reason.code == "completed_present"

    def test_non_dict_json_lines_are_skipped(self, tmp_path: Path) -> None:
        """Non-dict JSON lines (e.g., arrays) in status.events.jsonl are skipped."""
        feature_dir = tmp_path / "feature"
        feature_dir.mkdir()
        events_path = feature_dir / "status.events.jsonl"
        # A JSON array line followed by a valid completed event.
        completed = json.dumps(_completed_envelope(_EID_1, "2026-04-27T09:00:00+00:00"), sort_keys=True)
        events_path.write_text(
            f'["not", "a", "dict"]\n{completed}\n',
            encoding="utf-8",
        )

        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_autonomous(),
        )

        assert decision.allow_completion is True
        assert decision.reason.code == "completed_present"


# ---------------------------------------------------------------------------
# THIN CALLER (T024) — before_mark_done
# ---------------------------------------------------------------------------


class TestBeforeMarkDone:
    """Tests for the thin caller in retrospective_hook.py."""

    def test_allow_completion_returns_none(self, tmp_path: Path) -> None:
        """before_mark_done returns None when gate allows."""
        feature_dir = tmp_path / "feature"
        _write_events(
            feature_dir,
            [
                _completed_envelope(_EID_1, "2026-04-27T09:00:00+00:00"),
            ],
        )
        # Write charter so mode resolves to autonomous via charter override.
        _write_charter(tmp_path, mode_value="autonomous")

        result = before_mark_done(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
        )
        assert result is None

    def test_block_raises_mission_completion_blocked(self, tmp_path: Path) -> None:
        """before_mark_done raises MissionCompletionBlocked when gate blocks."""
        feature_dir = tmp_path / "feature"
        feature_dir.mkdir()
        # No events → gate blocks.
        _write_charter(tmp_path, mode_value="autonomous")

        with pytest.raises(MissionCompletionBlocked) as exc_info:
            before_mark_done(
                _MISSION_ID,
                feature_dir=feature_dir,
                repo_root=tmp_path,
            )

        blocked = exc_info.value
        assert blocked.decision.allow_completion is False
        assert "blocked" in str(blocked).lower()

    def test_decision_attached_to_exception(self, tmp_path: Path) -> None:
        """MissionCompletionBlocked carries a GateDecision on .decision."""
        feature_dir = tmp_path / "feature"
        _write_events(
            feature_dir,
            [
                _failed_envelope(_EID_1, "2026-04-27T09:00:00+00:00"),
            ],
        )
        _write_charter(tmp_path, mode_value="autonomous")

        with pytest.raises(MissionCompletionBlocked) as exc_info:
            before_mark_done(
                _MISSION_ID,
                feature_dir=feature_dir,
                repo_root=tmp_path,
            )

        assert isinstance(exc_info.value.decision, GateDecision)
        assert exc_info.value.decision.reason.code == "facilitator_failure"


# ---------------------------------------------------------------------------
# CHARTER AUTHORIZE AUTONOMOUS SKIP — extended tests
# ---------------------------------------------------------------------------


class TestCharterAuthorizeAutonomousSkip:
    """Charter clause tests for T022."""

    def test_charter_without_clause_blocks(self, tmp_path: Path) -> None:
        """Charter present but no autonomous_allow_skip → block."""
        feature_dir = tmp_path / "feature"
        _write_events(
            feature_dir,
            [
                _skipped_envelope(_EID_1, "2026-04-27T09:00:00+00:00"),
            ],
        )
        _write_charter(tmp_path, mode_value="autonomous")  # No autonomous_allow_skip

        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_autonomous(),
        )

        assert decision.allow_completion is False
        assert decision.reason.code == "silent_skip_attempted"
        assert decision.reason.charter_clause_ref is None

    def test_charter_custom_clause_id_set(self, tmp_path: Path) -> None:
        """Custom clause id is reflected in charter_clause_ref."""
        feature_dir = tmp_path / "feature"
        _write_events(
            feature_dir,
            [
                _skipped_envelope(_EID_1, "2026-04-27T09:00:00+00:00"),
            ],
        )
        _write_charter(
            tmp_path,
            mode_value="autonomous",
            autonomous_allow_skip="my-project:skip-ok",
        )

        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_autonomous(),
        )

        assert decision.allow_completion is True
        assert decision.reason.code == "skipped_permitted"
        assert decision.reason.charter_clause_ref == "my-project:skip-ok"

    def test_charter_clause_does_not_affect_hic_skipped(self, tmp_path: Path) -> None:
        """HiC skipped is always allowed regardless of charter clause."""
        feature_dir = tmp_path / "feature"
        _write_events(
            feature_dir,
            [
                _skipped_envelope(_EID_1, "2026-04-27T09:00:00+00:00"),
            ],
        )
        _write_charter(
            tmp_path,
            mode_value="human_in_command",
            autonomous_allow_skip="mode-policy:autonomous-allow-skip",
        )

        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_hic(),
        )

        assert decision.allow_completion is True
        assert decision.reason.code == "skipped_permitted"


# ---------------------------------------------------------------------------
# LATEST EVENT TIEBREAK — ensure deterministic ordering
# ---------------------------------------------------------------------------


class TestLatestEventTiebreak:
    """Verify latest event selection is deterministic under same-timestamp events."""

    def test_latest_by_event_id_ulid(self, tmp_path: Path) -> None:
        """When two terminal events share the same timestamp, higher ULID wins."""
        feature_dir = tmp_path / "feature"
        # Same timestamp, different event_ids.  _EID_2 > _EID_1 lexicographically.
        _write_events(
            feature_dir,
            [
                # completed event with lower ULID
                _completed_envelope(_EID_1, "2026-04-27T09:00:00+00:00"),
                # failed event with higher ULID (same ts) — should win
                _failed_envelope(_EID_2, "2026-04-27T09:00:00+00:00"),
            ],
        )

        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_autonomous(),
        )

        # Failed event has higher ULID, so it should be the latest.
        assert decision.reason.code == "facilitator_failure"

    def test_latest_by_at_timestamp(self, tmp_path: Path) -> None:
        """Later timestamp wins regardless of event_id order."""
        feature_dir = tmp_path / "feature"
        _write_events(
            feature_dir,
            [
                _failed_envelope(_EID_1, "2026-04-27T09:00:00+00:00"),
                _completed_envelope(_EID_2, "2026-04-27T09:05:00+00:00"),  # later
            ],
        )

        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_autonomous(),
        )

        assert decision.allow_completion is True
        assert decision.reason.code == "completed_present"


# ---------------------------------------------------------------------------
# NON-RETRO EVENTS IGNORED
# ---------------------------------------------------------------------------


class TestNonRetroEventsIgnored:
    """Events with non-retrospective names should be invisible to the gate."""

    def test_non_retro_events_ignored(self, tmp_path: Path) -> None:
        """Gate ignores events not in RETROSPECTIVE_EVENT_NAMES."""
        feature_dir = tmp_path / "feature"
        _write_events(
            feature_dir,
            [
                {
                    "actor": {"id": "x", "kind": "human", "profile_id": None},
                    "at": "2026-04-27T09:00:00+00:00",
                    "event_id": _EID_1,
                    "event_name": "mission.status.changed",
                    "mid8": "01KQ6YEG",
                    "mission_id": _MISSION_ID,
                    "mission_slug": "test-mission",
                    "payload": {"from_lane": "planned", "to_lane": "done"},
                },
            ],
        )

        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_autonomous(),
        )

        # Non-retro events are invisible → no terminal event → block
        assert decision.allow_completion is False
        assert decision.reason.code == "missing_completion_autonomous"


# ---------------------------------------------------------------------------
# CHARTER EDGE CASES (coverage for defensive paths in _charter_authorizes_*)
# ---------------------------------------------------------------------------


class TestCharterEdgeCases:
    """Edge-case charter paths: no frontmatter, unclosed block, non-dict."""

    def test_charter_no_frontmatter_does_not_authorize(self, tmp_path: Path) -> None:
        """Charter without leading '---' does not authorize autonomous-skip."""
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True, exist_ok=True)
        (charter_dir / "charter.md").write_text("# Charter\nNo frontmatter.\n", encoding="utf-8")

        feature_dir = tmp_path / "feature"
        _write_events(
            feature_dir,
            [
                _skipped_envelope(_EID_1, "2026-04-27T09:00:00+00:00"),
            ],
        )

        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_autonomous(),
        )

        assert decision.allow_completion is False
        assert decision.reason.code == "silent_skip_attempted"

    def test_charter_unclosed_frontmatter_does_not_authorize(self, tmp_path: Path) -> None:
        """Charter with unclosed frontmatter block does not authorize autonomous-skip."""
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True, exist_ok=True)
        (charter_dir / "charter.md").write_text(
            "---\nmode: autonomous\nautonomous_allow_skip: mode-policy:skip\n# No closing ---\n",
            encoding="utf-8",
        )

        feature_dir = tmp_path / "feature"
        _write_events(
            feature_dir,
            [
                _skipped_envelope(_EID_1, "2026-04-27T09:00:00+00:00"),
            ],
        )

        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_autonomous(),
        )

        assert decision.allow_completion is False
        assert decision.reason.code == "silent_skip_attempted"

    def test_charter_missing_does_not_authorize(self, tmp_path: Path) -> None:
        """No charter at all does not authorize autonomous-skip."""
        feature_dir = tmp_path / "feature"
        _write_events(
            feature_dir,
            [
                _skipped_envelope(_EID_1, "2026-04-27T09:00:00+00:00"),
            ],
        )

        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_autonomous(),
        )

        assert decision.allow_completion is False
        assert decision.reason.code == "silent_skip_attempted"


# ---------------------------------------------------------------------------
# SILENT AUTO-RUN PREDICATE EDGE CASES (T023)
# ---------------------------------------------------------------------------


class TestSilentAutoRunEdgeCases:
    """Edge cases for _is_silent_auto_run predicate."""

    def test_completed_without_preceding_requested_blocks(self, tmp_path: Path) -> None:
        """HiC: completed with no preceding requested event is treated as silent (fail closed).

        Missing provenance MUST NOT pass the gate; HiC completion requires
        positive evidence of operator initiation via a preceding requested event.
        """
        feature_dir = tmp_path / "feature"
        # completed event with NO preceding requested event
        _write_events(
            feature_dir,
            [
                _completed_envelope(_EID_1, "2026-04-27T09:00:00+00:00"),
            ],
        )

        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_hic(),
        )

        assert decision.allow_completion is False
        assert decision.reason.code == "silent_auto_run_attempted"

    def test_completed_with_only_later_requested_blocks(self, tmp_path: Path) -> None:
        """HiC: requested event AFTER completed event is not preceding (fail closed)."""
        feature_dir = tmp_path / "feature"
        _write_events(
            feature_dir,
            [
                _completed_envelope(_EID_1, "2026-04-27T09:00:00+00:00"),
                # requested comes AFTER completed — should not count, fail closed
                _requested_envelope(_EID_2, "2026-04-27T09:10:00+00:00", actor_kind="runtime"),
            ],
        )

        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_hic(),
        )

        assert decision.allow_completion is False
        assert decision.reason.code == "silent_auto_run_attempted"

    def test_completed_with_malformed_actor_in_requested_blocks(self, tmp_path: Path) -> None:
        """HiC: malformed actor in requested event → fail closed (cannot verify operator)."""
        feature_dir = tmp_path / "feature"
        # Inject a requested event with a non-dict actor (malformed).
        bad_requested: dict[str, object] = {
            "actor": "not-a-dict",  # malformed
            "at": "2026-04-27T09:00:00+00:00",
            "event_id": _EID_1,
            "event_name": "retrospective.requested",
            "mid8": _MISSION_ID[:8],
            "mission_id": _MISSION_ID,
            "mission_slug": "test-mission",
            "payload": {},
        }
        _write_events(
            feature_dir,
            [
                bad_requested,
                _completed_envelope(_EID_2, "2026-04-27T09:05:00+00:00"),
            ],
        )

        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_hic(),
        )

        # Malformed actor → cannot verify operator-driven → fail closed → block
        assert decision.allow_completion is False
        assert decision.reason.code == "silent_auto_run_attempted"


# ---------------------------------------------------------------------------
# CHARTER YAML PARSE ERROR — covers _charter_authorizes_autonomous_skip error paths
# ---------------------------------------------------------------------------


class TestCharterYamlEdgeCases:
    """Cover charter YAML parse error and non-dict result paths."""

    def test_charter_with_invalid_yaml_does_not_authorize(self, tmp_path: Path) -> None:
        """Charter with YAML parse error does not authorize autonomous-skip."""
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True, exist_ok=True)
        # Invalid YAML: tab inside block scalar (parse error in strict mode)
        (charter_dir / "charter.md").write_text(
            "---\n: invalid: yaml: [\n---\n\n# Charter\n",
            encoding="utf-8",
        )

        feature_dir = tmp_path / "feature"
        _write_events(
            feature_dir,
            [
                _skipped_envelope(_EID_1, "2026-04-27T09:00:00+00:00"),
            ],
        )

        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_autonomous(),
        )

        # Parse error → can't determine clause → block
        assert decision.allow_completion is False
        assert decision.reason.code == "silent_skip_attempted"

    def test_charter_with_list_frontmatter_does_not_authorize(self, tmp_path: Path) -> None:
        """Charter with non-dict YAML result (e.g., a list) does not authorize."""
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True, exist_ok=True)
        # Valid YAML but a list, not a mapping.
        (charter_dir / "charter.md").write_text(
            "---\n- item1\n- item2\n---\n\n# Charter\n",
            encoding="utf-8",
        )

        feature_dir = tmp_path / "feature"
        _write_events(
            feature_dir,
            [
                _skipped_envelope(_EID_1, "2026-04-27T09:00:00+00:00"),
            ],
        )

        decision = is_completion_allowed(
            _MISSION_ID,
            feature_dir=feature_dir,
            repo_root=tmp_path,
            mode_override=_mode_autonomous(),
        )

        # Non-dict → can't look up clause → block
        assert decision.allow_completion is False
        assert decision.reason.code == "silent_skip_attempted"
