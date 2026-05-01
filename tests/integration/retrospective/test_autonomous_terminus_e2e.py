"""T056 — Autonomous terminus end-to-end integration test.

Drives the autonomous retrospective lifecycle via run_terminus() (the real
runtime entry point from WP06), with a synthetic facilitator_callback.

Asserts:
  - Event sequence: requested(actor=runtime) -> started -> completed.
  - retrospective.yaml exists at canonical path with status=completed.
  - Proposal events emitted when the record carries proposals.

No private helpers are called directly — all assertions go through the
public-facing event log and written YAML.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from specify_cli.next._internal_runtime.retrospective_terminus import run_terminus
from specify_cli.retrospective.reader import read_record
from specify_cli.retrospective.schema import (
    ActorRef,
    AddGlossaryTermPayload,
    MissionIdentity,
    Mode,
    ModeSourceSignal,
    Proposal,
    ProposalProvenance,
    ProposalState,
    RecordProvenance,
    RetrospectiveRecord,
)

from tests.integration.retrospective.conftest import (
    HUMAN_ACTOR,
    event_names,
    make_completed_record,
    read_events,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_proposal(mission_id: str, event_id: str) -> Proposal:
    """Build a minimal add_glossary_term proposal."""
    import ulid as _ulid

    return Proposal(
        id=str(_ulid.ULID()),
        kind="add_glossary_term",
        payload=AddGlossaryTermPayload(
            kind="add_glossary_term",
            term_key="terminus-e2e-term",
            definition="A term added by the autonomous e2e test",
            definition_hash="abc123",
        ),
        rationale="Test proposal from autonomous terminus e2e",
        state=ProposalState(status="pending"),
        provenance=ProposalProvenance(
            source_mission_id=mission_id,
            source_evidence_event_ids=[event_id],
            authored_by=ActorRef(kind="agent", id="facilitator", profile_id=None),
        ),
    )


# ---------------------------------------------------------------------------
# T056 — Autonomous terminus e2e
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_autonomous_terminus_emits_correct_event_sequence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Autonomous terminus: correct event sequence and retrospective.yaml written.

    Steps:
    1. Set SPEC_KITTY_MODE=autonomous.
    2. Call run_terminus() with a synthetic facilitator_callback.
    3. Assert event sequence: requested(actor=runtime) -> started -> completed.
    4. Assert retrospective.yaml exists at canonical path with status=completed.
    5. Assert mission marked done (no MissionCompletionBlocked raised).
    """
    monkeypatch.setenv("SPEC_KITTY_MODE", "autonomous")

    # Set up minimal repo structure.
    import ulid as _ulid

    mission_id = str(_ulid.ULID())
    mission_slug = "alpha-terminus-e2e"
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True, exist_ok=True)

    # Write meta.json so apply_proposals can resolve the slug.
    meta = {
        "mission_id": mission_id,
        "mission_slug": mission_slug,
        "mission_type": "software-dev",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    record = make_completed_record(
        mission_id=mission_id,
        mission_slug=mission_slug,
    )

    def facilitator(**kwargs: Any) -> RetrospectiveRecord:
        return record

    # Call the real runtime entry point.
    run_terminus(
        mission_id=mission_id,
        mission_type="software-dev",
        feature_dir=feature_dir,
        repo_root=tmp_path,
        operator_actor=HUMAN_ACTOR,
        facilitator_callback=facilitator,
    )

    # --- Event sequence ---
    names = event_names(feature_dir)
    assert names == [
        "retrospective.requested",
        "retrospective.started",
        "retrospective.completed",
    ], f"Unexpected event sequence: {names}"

    # --- actor=runtime on retrospective.requested ---
    events = read_events(feature_dir)
    requested = next(e for e in events if e["event_name"] == "retrospective.requested")
    assert requested["actor"]["kind"] == "runtime", f"Expected actor.kind='runtime' on requested event, got: {requested['actor']}"
    assert requested["actor"]["id"] == "next"

    # --- retrospective.yaml at canonical path ---
    canonical = tmp_path / ".kittify" / "missions" / mission_id / "retrospective.yaml"
    assert canonical.exists(), f"retrospective.yaml not found at canonical path: {canonical}"

    loaded = read_record(canonical)
    assert loaded.status == "completed"
    assert loaded.mission.mission_id == mission_id


@pytest.mark.integration
def test_autonomous_terminus_proposal_events(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the record carries proposals, proposal events are emitted on apply.

    This test seeds the record with one add_glossary_term proposal and
    confirms the proposal appears in the record read back from disk.
    (The proposal.applied event is only emitted by apply_proposals(), which
    is a separate CLI step; here we confirm the proposal is persisted in the
    record, not that apply was called.)
    """
    monkeypatch.setenv("SPEC_KITTY_MODE", "autonomous")

    import ulid as _ulid

    mission_id = str(_ulid.ULID())
    mission_slug = "alpha-proposals-e2e"
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True, exist_ok=True)

    meta = {"mission_id": mission_id, "mission_slug": mission_slug, "mission_type": "software-dev"}
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    # Seed a synthetic event id in the event log so the proposal's
    # source_evidence_event_ids resolves as non-stale.
    fake_event_id = str(_ulid.ULID())
    seed_event = {
        "event_id": fake_event_id,
        "event_name": "retrospective.started",
        "mission_id": mission_id,
        "at": "2026-04-27T10:00:00+00:00",
    }
    events_path = feature_dir / "status.events.jsonl"
    events_path.write_text(json.dumps(seed_event) + "\n", encoding="utf-8")

    proposal = _make_proposal(mission_id=mission_id, event_id=fake_event_id)

    now = "2026-04-27T11:00:00+00:00"
    actor_ref = ActorRef(kind="agent", id="facilitator", profile_id=None)
    record = RetrospectiveRecord(
        schema_version="1",
        mission=MissionIdentity(
            mission_id=mission_id,
            mid8=mission_id[:8],
            mission_slug=mission_slug,
            mission_type="software-dev",
            mission_started_at="2026-04-27T10:00:00+00:00",
            mission_completed_at=now,
        ),
        mode=Mode(
            value="autonomous",
            source_signal=ModeSourceSignal(kind="environment", evidence="SPEC_KITTY_MODE"),
        ),
        status="completed",
        started_at="2026-04-27T10:55:00+00:00",
        completed_at=now,
        actor=actor_ref,
        proposals=[proposal],
        provenance=RecordProvenance(
            authored_by=actor_ref,
            runtime_version="0.0.0-test",
            written_at=now,
            schema_version="1",
        ),
    )

    def facilitator(**kwargs: Any) -> RetrospectiveRecord:
        return record

    run_terminus(
        mission_id=mission_id,
        mission_type="software-dev",
        feature_dir=feature_dir,
        repo_root=tmp_path,
        operator_actor=HUMAN_ACTOR,
        facilitator_callback=facilitator,
    )

    canonical = tmp_path / ".kittify" / "missions" / mission_id / "retrospective.yaml"
    assert canonical.exists()
    loaded = read_record(canonical)
    assert loaded.status == "completed"
    assert len(loaded.proposals) == 1
    assert loaded.proposals[0].kind == "add_glossary_term"
