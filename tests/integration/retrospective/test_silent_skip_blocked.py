"""T058 — Silent skip blocked in autonomous mode.

Scenario:
  - Mode = autonomous.
  - No charter clause permits skip.
  - A ``retrospective.skipped`` event is pre-seeded into the event log
    (simulating an agent that tried to bypass the lifecycle).
  - We call is_completion_allowed() directly (which is what before_mark_done
    calls internally), and assert the gate blocks with reason
    ``silent_skip_attempted``.

We drive this through the gate's public API (is_completion_allowed) rather
than through run_terminus, because run_terminus drives the forward path (it
produces the retrospective terminal event itself).  The blocker scenario
is: an agent skips outside of run_terminus and then tries to mark done.
The gate is the enforcement point; this is a real-runtime test via the
public gate API.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.retrospective.gate import is_completion_allowed


# ---------------------------------------------------------------------------
# T058 — Silent skip blocked
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_silent_skip_blocked_in_autonomous_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """autonomous mode + retrospective.skipped (no charter clause) → blocked: silent_skip_attempted.

    This test drives the real gate (is_completion_allowed) against a pre-seeded
    event log containing a skipped event, with no charter and no autonomous_allow_skip
    clause.  The gate must block with reason.code == 'silent_skip_attempted'.
    """
    monkeypatch.setenv("SPEC_KITTY_MODE", "autonomous")

    import ulid as _ulid

    mission_id = str(_ulid.ULID())
    mission_slug = "silent-skip-test"
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True, exist_ok=True)

    # Seed a skipped event directly into the event log.
    # This simulates an agent attempt to bypass the lifecycle.
    skipped_event_id = str(_ulid.ULID())
    skipped_event = {
        "actor": {"kind": "agent", "id": "rogue-agent", "profile_id": None},
        "at": "2026-04-27T11:00:00+00:00",
        "event_id": skipped_event_id,
        "event_name": "retrospective.skipped",
        "mid8": mission_id[:8],
        "mission_id": mission_id,
        "mission_slug": mission_slug,
        "payload": {
            "record_path": "/tmp/fake.yaml",
            "skip_reason": "agent tried to bypass",
            "skipped_by": {"kind": "agent", "id": "rogue-agent", "profile_id": None},
        },
    }

    events_path = feature_dir / "status.events.jsonl"
    events_path.write_text(json.dumps(skipped_event) + "\n", encoding="utf-8")

    # Call the real gate — no charter means no autonomous_allow_skip clause.
    decision = is_completion_allowed(
        mission_id,
        feature_dir=feature_dir,
        repo_root=tmp_path,
    )

    # Gate must block.
    assert not decision.allow_completion, (
        f"Expected gate to block silent skip, but it allowed: {decision}"
    )
    assert decision.reason.code == "silent_skip_attempted", (
        f"Expected reason.code='silent_skip_attempted', got: {decision.reason.code}"
    )
    # The blocking event id must reference the skipped event.
    assert skipped_event_id in decision.reason.blocking_event_ids, (
        f"Expected skipped_event_id in blocking_event_ids, got: {decision.reason.blocking_event_ids}"
    )


@pytest.mark.integration
def test_silent_skip_allowed_with_charter_clause(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """autonomous mode + skipped event + charter autonomous_allow_skip clause → allowed.

    This negative-positive test confirms that the charter override path works:
    when the charter has autonomous_allow_skip, the gate ALLOWS the skip.
    """
    monkeypatch.setenv("SPEC_KITTY_MODE", "autonomous")

    import ulid as _ulid

    mission_id = str(_ulid.ULID())
    mission_slug = "charter-skip-allowed"
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True, exist_ok=True)

    # Write a charter with autonomous_allow_skip.
    charter_dir = tmp_path / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    charter_path = charter_dir / "charter.md"
    charter_path.write_text(
        "---\nautonomous_allow_skip: mode-policy:autonomous-allow-skip\n---\n\nCharter body.\n",
        encoding="utf-8",
    )

    # Seed a skipped event.
    skipped_event_id = str(_ulid.ULID())
    skipped_event = {
        "actor": {"kind": "runtime", "id": "next", "profile_id": None},
        "at": "2026-04-27T11:00:00+00:00",
        "event_id": skipped_event_id,
        "event_name": "retrospective.skipped",
        "mid8": mission_id[:8],
        "mission_id": mission_id,
        "mission_slug": mission_slug,
        "payload": {
            "record_path": "/tmp/fake.yaml",
            "skip_reason": "authorized skip",
            "skipped_by": {"kind": "runtime", "id": "next", "profile_id": None},
        },
    }
    events_path = feature_dir / "status.events.jsonl"
    events_path.write_text(json.dumps(skipped_event) + "\n", encoding="utf-8")

    decision = is_completion_allowed(
        mission_id,
        feature_dir=feature_dir,
        repo_root=tmp_path,
    )

    # Charter clause must allow the skip.
    assert decision.allow_completion, (
        f"Expected charter clause to allow skip, but gate blocked: {decision.reason}"
    )
    assert decision.reason.code == "skipped_permitted"
    assert decision.reason.charter_clause_ref == "mode-policy:autonomous-allow-skip"
