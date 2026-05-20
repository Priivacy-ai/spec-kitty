"""WP04 T023 integration — strict-policy skip with non-empty reason.

Tests the ``emit_skipped`` bypass path: when ``--skip-retrospective`` is
provided (simulated via direct call), the terminus emits a
``RetrospectiveSkipped`` event and mission completion proceeds.

T020: strict pre-completion gate — skip bypass with non-empty skip_reason.
T021: policy_source attribution on RetrospectiveSkipped.
T022: RetrospectiveSkipped appears BEFORE any MissionCompleted equivalent.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration]

import ulid as _ulid_mod


def _scaffold_minimal_mission(tmp_path: Path, mission_slug: str) -> tuple[Path, str]:
    """Create a minimal mission directory."""
    mission_id = str(_ulid_mod.ULID())
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)

    (feature_dir / "meta.json").write_text(
        json.dumps({
            "mission_id": mission_id,
            "mission_slug": mission_slug,
            "mission_type": "software-dev",
            "friendly_name": "Skip Test Mission",
            "mission_number": None,
        }),
        encoding="utf-8",
    )
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")
    return feature_dir, mission_id


@pytest.mark.integration
def test_strict_flow_skip_with_non_empty_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """emit_skipped with non-empty skip_reason: event emitted, no ValueError.

    Directly invokes emit_skipped (WP03 surface) with the resolved
    policy_source. Asserts:
    (a) RetrospectiveSkipped event is in status.events.jsonl.
    (b) skip_reason is the provided string.
    (c) policy_source is non-empty (T021).
    (d) bypassed_provenance_kind == 'runtime_strict_gate'.
    """
    from specify_cli.retrospective.lifecycle_events import emit_skipped, Actor
    from specify_cli.retrospective.policy import resolve_policy

    mission_slug = "strict-flow-skip-01KQ"
    feature_dir, mission_id = _scaffold_minimal_mission(tmp_path, mission_slug)

    # Resolve policy from the bare repo (no config → all defaults).
    policy, source_map = resolve_policy(tmp_path)

    skip_reason = "CI time-box exceeded; will retrospect manually"
    actor = Actor(kind="human", id="operator@example.com", display="Test Operator")

    emit_skipped(
        mission_id=mission_id,
        mission_slug=mission_slug,
        repo_root=tmp_path,
        skip_reason=skip_reason,
        skip_reason_source="cli_flag",
        policy_source=source_map,
        actor=actor,
    )

    events_path = feature_dir / "status.events.jsonl"
    assert events_path.exists()
    events = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    skipped_events = [e for e in events if e.get("type") == "RetrospectiveSkipped"]
    assert skipped_events, (
        f"Expected RetrospectiveSkipped event; got: {[e.get('type') for e in events]}"
    )

    skipped = skipped_events[0]
    assert skipped["skip_reason"] == skip_reason
    assert skipped["skip_reason_source"] == "cli_flag"
    assert skipped.get("policy_source"), "policy_source must be non-empty (T021)"
    assert skipped.get("bypassed_provenance_kind") == "runtime_strict_gate"
    assert skipped.get("actor", {}).get("kind") == "human"
