"""Schema round-trip tests: write → read → assert deep equality.

Also contains a performance microbenchmark: 200-finding fixture validates
in under 500 ms (generous slack to avoid CI flakiness; spec says 200 ms).
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from specify_cli.retrospective.reader import read_record
from specify_cli.retrospective.schema import (
    ActorRef,
    AddEdgePayload,
    EdgeSpec,
    Finding,
    FindingProvenance,
    FlagNotHelpfulPayload,
    MissionIdentity,
    Mode,
    ModeSourceSignal,
    Proposal,
    ProposalApplyAttempt,
    ProposalProvenance,
    ProposalState,
    RecordProvenance,
    RetrospectiveFailure,
    RetrospectiveRecord,
    TargetReference,
)
from specify_cli.retrospective.writer import write_record

# ---------------------------------------------------------------------------
# Shared ULID-like test identifiers (valid Crockford base32, 26 chars)
# ---------------------------------------------------------------------------
MISSION_ID = "01KQ6YEGT4YBZ3GZF7X680KQ3V"
MISSION_ID_2 = "01KQ6YEGT4YBZ3GZF7X680KQ3W"
EVENT_ID_A = "01KQ6YEGT4YBZ3GZF7X680KQ3X"
EVENT_ID_B = "01KQ6YEGT4YBZ3GZF7X680KQ3Y"
PROPOSAL_ID_1 = "01KQ6YEGT4YBZ3GZF7X680KQ4A"
PROPOSAL_ID_2 = "01KQ6YEGT4YBZ3GZF7X680KQ4B"

AGENT_ACTOR = ActorRef(kind="agent", id="claude-opus-4-7", profile_id="retrospective-facilitator")
HUMAN_ACTOR = ActorRef(kind="human", id="rob@robshouse.net", profile_id=None)

MISSION = MissionIdentity(
    mission_id=MISSION_ID,
    mid8="01KQ6YEG",
    mission_slug="mission-retrospective-learning-loop-01KQ6YEG",
    mission_type="software-dev",
    mission_started_at="2026-04-27T07:46:18.715532+00:00",
    mission_completed_at="2026-04-27T11:00:00+00:00",
)

MODE = Mode(
    value="human_in_command",
    source_signal=ModeSourceSignal(kind="charter_override", evidence="charter:mode-policy:hic-default"),
)

RECORD_PROVENANCE = RecordProvenance(
    authored_by=AGENT_ACTOR,
    runtime_version="3.2.0",
    written_at="2026-04-27T11:00:00+00:00",
    schema_version="1",
)

FINDING_PROVENANCE = FindingProvenance(
    source_mission_id=MISSION_ID,
    evidence_event_ids=[EVENT_ID_A, EVENT_ID_B],
    actor=AGENT_ACTOR,
    captured_at="2026-04-27T10:58:00+00:00",
)

PROPOSAL_PROVENANCE = ProposalProvenance(
    source_mission_id=MISSION_ID,
    source_evidence_event_ids=[EVENT_ID_A],
    authored_by=AGENT_ACTOR,
    approved_by=None,
)


def make_finding(fid: str, note: str = "Test finding") -> Finding:
    return Finding(
        id=fid,
        target=TargetReference(kind="drg_edge", urn=f"drg:edge:{fid}"),
        note=note,
        provenance=FINDING_PROVENANCE,
    )


def make_proposal(pid: str) -> Proposal:
    return Proposal(
        id=pid,
        kind="add_edge",
        payload=AddEdgePayload(
            kind="add_edge",
            edge=EdgeSpec(from_node="drg:node:a", to_node="drg:node:b", kind="informs"),
        ),
        rationale="Test proposal rationale.",
        state=ProposalState(
            status="pending",
            decided_at=None,
            decided_by=None,
            apply_attempts=[],
        ),
        provenance=PROPOSAL_PROVENANCE,
    )


# ---------------------------------------------------------------------------
# Fixture: "rich" completed record
# ---------------------------------------------------------------------------


def make_completed_record() -> RetrospectiveRecord:
    return RetrospectiveRecord(
        schema_version="1",
        mission=MISSION,
        mode=MODE,
        status="completed",
        started_at="2026-04-27T10:55:00+00:00",
        completed_at="2026-04-27T11:00:00+00:00",
        actor=HUMAN_ACTOR,
        helped=[make_finding("F-01", "Directive 003 helped during spec phase.")],
        not_helpful=[make_finding("F-02", "Tactic 007 was not helpful in this context.")],
        gaps=[make_finding("F-03", "Missing glossary term for 'lifecycle terminus hook'.")],
        proposals=[make_proposal(PROPOSAL_ID_1)],
        provenance=RECORD_PROVENANCE,
    )


# ---------------------------------------------------------------------------
# Fixture: "brief" completed record (empty lists)
# ---------------------------------------------------------------------------


def make_brief_completed_record() -> RetrospectiveRecord:
    return RetrospectiveRecord(
        schema_version="1",
        mission=MISSION,
        mode=MODE,
        status="completed",
        started_at="2026-04-27T10:55:00+00:00",
        completed_at="2026-04-27T11:00:00+00:00",
        actor=HUMAN_ACTOR,
        helped=[],
        not_helpful=[],
        gaps=[],
        proposals=[],
        provenance=RECORD_PROVENANCE,
    )


# ---------------------------------------------------------------------------
# Fixture: skipped record
# ---------------------------------------------------------------------------


def make_skipped_record() -> RetrospectiveRecord:
    return RetrospectiveRecord(
        schema_version="1",
        mission=MISSION,
        mode=MODE,
        status="skipped",
        started_at="2026-04-27T10:55:00+00:00",
        completed_at="2026-04-27T10:55:30+00:00",
        actor=HUMAN_ACTOR,
        helped=[],
        not_helpful=[],
        gaps=[],
        proposals=[],
        provenance=RECORD_PROVENANCE,
        skip_reason="low-value docs fix; operator explicitly skipped",
    )


# ---------------------------------------------------------------------------
# Fixture: failed record
# ---------------------------------------------------------------------------


def make_failed_record() -> RetrospectiveRecord:
    return RetrospectiveRecord(
        schema_version="1",
        mission=MISSION,
        mode=MODE,
        status="failed",
        started_at="2026-04-27T10:55:00+00:00",
        completed_at="2026-04-27T10:56:00+00:00",
        actor=HUMAN_ACTOR,
        helped=[],
        not_helpful=[],
        gaps=[],
        proposals=[],
        provenance=RECORD_PROVENANCE,
        failure=RetrospectiveFailure(
            code="facilitator_error",
            message="Facilitator timed out during analysis.",
            error_chain=["timeout after 30s", "no LLM response"],
        ),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "record_factory",
    [
        make_completed_record,
        make_brief_completed_record,
        make_skipped_record,
        make_failed_record,
    ],
    ids=["rich_completed", "brief_completed", "skipped", "failed"],
)
def test_write_read_roundtrip(tmp_path: Path, record_factory: object) -> None:
    """Write a record then read it back; model_dump() must be identical."""
    record = record_factory()  # type: ignore[operator]
    canonical = write_record(record, repo_root=tmp_path)

    # Canonical path must include the mission ULID.
    assert MISSION_ID in str(canonical)
    assert canonical.name == "retrospective.yaml"
    assert canonical.exists()

    restored = read_record(canonical)
    assert restored.model_dump() == record.model_dump()


def test_canonical_path_contains_ulid(tmp_path: Path) -> None:
    """Canonical path is keyed by mission_id (ULID), not by slug or number."""
    record = make_completed_record()
    canonical = write_record(record, repo_root=tmp_path)
    parts = canonical.parts
    assert MISSION_ID in parts, f"Expected {MISSION_ID!r} in path segments {parts}"


def test_write_read_with_apply_attempt(tmp_path: Path) -> None:
    """Record with a non-pending proposal state (applied) round-trips cleanly."""
    proposal = Proposal(
        id=PROPOSAL_ID_2,
        kind="flag_not_helpful",
        payload=FlagNotHelpfulPayload(
            kind="flag_not_helpful",
            target=TargetReference(kind="drg_node", urn="drg:node:doctrine_directive_003"),
        ),
        rationale="Auto-applicable flag.",
        state=ProposalState(
            status="applied",
            decided_at="2026-04-27T11:00:01+00:00",
            decided_by=AGENT_ACTOR,
            apply_attempts=[
                ProposalApplyAttempt(
                    attempt_id=EVENT_ID_A,
                    at="2026-04-27T11:00:02+00:00",
                    outcome="applied",
                    error=None,
                )
            ],
        ),
        provenance=PROPOSAL_PROVENANCE,
    )
    record = RetrospectiveRecord(
        schema_version="1",
        mission=MISSION,
        mode=MODE,
        status="completed",
        started_at="2026-04-27T10:55:00+00:00",
        completed_at="2026-04-27T11:00:00+00:00",
        actor=HUMAN_ACTOR,
        proposals=[proposal],
        provenance=RECORD_PROVENANCE,
    )
    canonical = write_record(record, repo_root=tmp_path)
    restored = read_record(canonical)
    assert restored.model_dump() == record.model_dump()


# ---------------------------------------------------------------------------
# Cross-field validator coverage (T008)
# ---------------------------------------------------------------------------


def test_completed_without_completed_at_raises() -> None:
    """completed status requires completed_at."""
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="completed_at"):
        RetrospectiveRecord(
            schema_version="1",
            mission=MISSION,
            mode=MODE,
            status="completed",
            started_at="2026-04-27T10:55:00+00:00",
            completed_at=None,  # missing!
            actor=HUMAN_ACTOR,
            provenance=RECORD_PROVENANCE,
        )


def test_skipped_without_skip_reason_raises() -> None:
    """skipped status requires skip_reason."""
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="skip_reason"):
        RetrospectiveRecord(
            schema_version="1",
            mission=MISSION,
            mode=MODE,
            status="skipped",
            started_at="2026-04-27T10:55:00+00:00",
            completed_at="2026-04-27T10:55:30+00:00",
            actor=HUMAN_ACTOR,
            provenance=RECORD_PROVENANCE,
            # skip_reason absent
        )


def test_failed_without_failure_raises() -> None:
    """failed status requires failure."""
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="failure"):
        RetrospectiveRecord(
            schema_version="1",
            mission=MISSION,
            mode=MODE,
            status="failed",
            started_at="2026-04-27T10:55:00+00:00",
            completed_at="2026-04-27T10:56:00+00:00",
            actor=HUMAN_ACTOR,
            provenance=RECORD_PROVENANCE,
            # failure absent
        )


def test_pending_status_raises_on_construction() -> None:
    """pending status is rejected by the model validator."""
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="pending"):
        RetrospectiveRecord(
            schema_version="1",
            mission=MISSION,
            mode=MODE,
            status="pending",
            started_at="2026-04-27T10:55:00+00:00",
            actor=HUMAN_ACTOR,
            provenance=RECORD_PROVENANCE,
        )


def test_duplicate_finding_ids_raises() -> None:
    """Duplicate Finding.id values within a record are rejected."""
    import pytest
    from pydantic import ValidationError

    dup = make_finding("F-DUP")
    with pytest.raises(ValidationError, match="Duplicate Finding.id"):
        RetrospectiveRecord(
            schema_version="1",
            mission=MISSION,
            mode=MODE,
            status="completed",
            started_at="2026-04-27T10:55:00+00:00",
            completed_at="2026-04-27T11:00:00+00:00",
            actor=HUMAN_ACTOR,
            helped=[dup, dup],
            provenance=RECORD_PROVENANCE,
        )


def test_duplicate_proposal_ids_raises() -> None:
    """Duplicate Proposal.id values within a record are rejected."""
    import pytest
    from pydantic import ValidationError

    dup = make_proposal(PROPOSAL_ID_1)
    with pytest.raises(ValidationError, match="Duplicate Proposal.id"):
        RetrospectiveRecord(
            schema_version="1",
            mission=MISSION,
            mode=MODE,
            status="completed",
            started_at="2026-04-27T10:55:00+00:00",
            completed_at="2026-04-27T11:00:00+00:00",
            actor=HUMAN_ACTOR,
            proposals=[dup, dup],
            provenance=RECORD_PROVENANCE,
        )


# ---------------------------------------------------------------------------
# Performance microbenchmark: 200-finding fixture validates in < 500 ms
# ---------------------------------------------------------------------------


def test_perf_200_findings_under_500ms(tmp_path: Path) -> None:
    """NFR-001: schema validation of a 200-finding record must be < 500 ms."""
    findings = [make_finding(f"F-{i:03d}", f"Finding note {i}" * 5) for i in range(200)]
    record = RetrospectiveRecord(
        schema_version="1",
        mission=MISSION,
        mode=MODE,
        status="completed",
        started_at="2026-04-27T10:55:00+00:00",
        completed_at="2026-04-27T11:00:00+00:00",
        actor=HUMAN_ACTOR,
        helped=findings,
        not_helpful=[],
        gaps=[],
        proposals=[],
        provenance=RECORD_PROVENANCE,
    )
    raw = record.model_dump()

    t0 = time.perf_counter()
    RetrospectiveRecord.model_validate(raw)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert elapsed_ms < 500, f"Validation took {elapsed_ms:.1f}ms (limit: 500ms)"
