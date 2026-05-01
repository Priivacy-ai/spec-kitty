"""T059 — Silent auto-run blocked in HiC mode.

Scenario:
  - Mode = human_in_command (via env).
  - A ``retrospective.requested`` event with ``actor.kind="runtime"`` is
    pre-seeded, followed immediately by a ``retrospective.completed`` event.
    This simulates an autonomous-style auto-run in HiC context.
  - We call is_completion_allowed() (the real gate) and assert it blocks
    with reason.code == 'silent_auto_run_attempted'.

We drive this through the gate's public API (is_completion_allowed) — the
same public surface that before_mark_done() calls — because the blocker
scenario is about enforcement at the gate, not the forward lifecycle.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.retrospective.gate import is_completion_allowed


# ---------------------------------------------------------------------------
# T059 — Silent auto-run blocked
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_silent_auto_run_blocked_in_hic_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HiC mode + completed event (runtime-driven) → blocked: silent_auto_run_attempted.

    Pre-seeds:
      1. retrospective.requested  (actor=runtime)
      2. retrospective.completed  (actor=runtime, immediately after)

    The gate must detect the completed event was runtime-driven and block.
    """
    monkeypatch.setenv("SPEC_KITTY_MODE", "human_in_command")

    import ulid as _ulid

    mission_id = str(_ulid.ULID())
    mission_slug = "silent-auto-run-test"
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True, exist_ok=True)

    runtime_actor = {"kind": "runtime", "id": "next", "profile_id": None}

    # Event 1: requested by runtime (the blocked scenario).
    requested_event_id = str(_ulid.ULID())
    requested_event = {
        "actor": runtime_actor,
        "at": "2026-04-27T11:00:00+00:00",
        "event_id": requested_event_id,
        "event_name": "retrospective.requested",
        "mid8": mission_id[:8],
        "mission_id": mission_id,
        "mission_slug": mission_slug,
        "payload": {
            "mode": {
                "value": "human_in_command",
                "source_signal": {"kind": "environment", "evidence": "SPEC_KITTY_MODE"},
            },
            "terminus_step_id": "terminus",
            "requested_by": runtime_actor,
        },
    }

    # Event 2: completed immediately after (simulating auto-run).
    completed_event_id = str(_ulid.ULID())
    completed_event = {
        "actor": runtime_actor,
        "at": "2026-04-27T11:00:05+00:00",
        "event_id": completed_event_id,
        "event_name": "retrospective.completed",
        "mid8": mission_id[:8],
        "mission_id": mission_id,
        "mission_slug": mission_slug,
        "payload": {
            "record_path": "/tmp/fake.yaml",
            "record_hash": "",
            "findings_summary": {"helped": 0, "not_helpful": 0, "gaps": 0},
            "proposals_count": 0,
        },
    }

    events_path = feature_dir / "status.events.jsonl"
    lines = [json.dumps(requested_event), json.dumps(completed_event)]
    events_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Call the real gate — HiC mode should detect runtime-driven auto-run.
    decision = is_completion_allowed(
        mission_id,
        feature_dir=feature_dir,
        repo_root=tmp_path,
    )

    # Gate must block.
    assert not decision.allow_completion, f"Expected gate to block silent auto-run, but it allowed: {decision}"
    assert decision.reason.code == "silent_auto_run_attempted", f"Expected reason.code='silent_auto_run_attempted', got: {decision.reason.code}"
    assert completed_event_id in decision.reason.blocking_event_ids, f"Expected completed_event_id in blocking_event_ids, got: {decision.reason.blocking_event_ids}"


@pytest.mark.integration
def test_hic_completed_operator_driven_is_allowed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HiC mode + completed event (human-driven) → allowed: completed_present_hic.

    Contrast test: when the requesting actor is human, the gate allows completion.
    """
    monkeypatch.setenv("SPEC_KITTY_MODE", "human_in_command")

    import ulid as _ulid

    mission_id = str(_ulid.ULID())
    mission_slug = "hic-human-driven-ok"
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True, exist_ok=True)

    human_actor = {"kind": "human", "id": "operator", "profile_id": None}

    requested_event_id = str(_ulid.ULID())
    requested_event = {
        "actor": human_actor,
        "at": "2026-04-27T11:00:00+00:00",
        "event_id": requested_event_id,
        "event_name": "retrospective.requested",
        "mid8": mission_id[:8],
        "mission_id": mission_id,
        "mission_slug": mission_slug,
        "payload": {
            "mode": {
                "value": "human_in_command",
                "source_signal": {"kind": "environment", "evidence": "SPEC_KITTY_MODE"},
            },
            "terminus_step_id": "terminus",
            "requested_by": human_actor,
        },
    }

    completed_event_id = str(_ulid.ULID())
    completed_event = {
        "actor": human_actor,
        "at": "2026-04-27T11:00:05+00:00",
        "event_id": completed_event_id,
        "event_name": "retrospective.completed",
        "mid8": mission_id[:8],
        "mission_id": mission_id,
        "mission_slug": mission_slug,
        "payload": {
            "record_path": "/tmp/fake.yaml",
            "record_hash": "",
            "findings_summary": {"helped": 1, "not_helpful": 0, "gaps": 0},
            "proposals_count": 0,
        },
    }

    events_path = feature_dir / "status.events.jsonl"
    lines = [json.dumps(requested_event), json.dumps(completed_event)]
    events_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    decision = is_completion_allowed(
        mission_id,
        feature_dir=feature_dir,
        repo_root=tmp_path,
    )

    assert decision.allow_completion, f"Expected human-driven completed event to allow completion, got: {decision.reason}"
    assert decision.reason.code == "completed_present_hic"
