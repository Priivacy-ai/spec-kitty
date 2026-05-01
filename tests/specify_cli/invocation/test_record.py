"""Tests for InvocationRecord Pydantic model and MinimalViableTrailPolicy."""

from __future__ import annotations

import pytest

from specify_cli.invocation.record import (
    MINIMAL_VIABLE_TRAIL_POLICY,
    TIER_3_ACTIONS,
    InvocationRecord,
    MinimalViableTrailPolicy,
    TierPolicy,
    promote_to_evidence,
    tier_eligible,
)


# ---------------------------------------------------------------------------
# InvocationRecord tests
# ---------------------------------------------------------------------------


def _make_started(**overrides: object) -> InvocationRecord:
    defaults: dict[str, object] = {
        "event": "started",
        "invocation_id": "01ABCDEFGHJKMNPQRSTVWXYZ12",  # 26-char ULID
        "profile_id": "implementer-fixture",
        "action": "generate",
        "request_text": "implement the new feature",
        "governance_context_hash": "abcdef0123456789",
        "governance_context_available": True,
        "actor": "claude",
        "router_confidence": "exact",
        "started_at": "2026-04-21T12:00:00+00:00",
    }
    defaults.update(overrides)
    return InvocationRecord(**defaults)  # type: ignore[arg-type]


class TestInvocationRecordStartedFields:
    def test_required_fields_present(self) -> None:
        record = _make_started()
        assert record.event == "started"
        assert record.invocation_id == "01ABCDEFGHJKMNPQRSTVWXYZ12"
        assert record.profile_id == "implementer-fixture"
        assert record.action == "generate"
        assert record.actor == "claude"
        assert record.started_at == "2026-04-21T12:00:00+00:00"

    def test_optional_fields_default(self) -> None:
        record = InvocationRecord(
            event="started",
            invocation_id="01ABCDEFGHJKMNPQRSTVWXYZ12",
            profile_id="implementer-fixture",
            action="generate",
        )
        assert record.request_text == ""
        assert record.governance_context_hash == ""
        assert record.governance_context_available is True
        assert record.actor == "unknown"
        assert record.router_confidence is None
        assert record.started_at == ""
        assert record.completed_at is None
        assert record.outcome is None
        assert record.evidence_ref is None

    def test_completed_event_fields(self) -> None:
        record = InvocationRecord(
            event="completed",
            invocation_id="01ABCDEFGHJKMNPQRSTVWXYZ12",
            profile_id="implementer-fixture",
            action="",
            completed_at="2026-04-21T13:00:00+00:00",
            outcome="done",
            evidence_ref="some-ref",
        )
        assert record.event == "completed"
        assert record.completed_at == "2026-04-21T13:00:00+00:00"
        assert record.outcome == "done"
        assert record.evidence_ref == "some-ref"


class TestInvocationRecordFrozen:
    def test_mutation_raises_validation_error(self) -> None:
        record = _make_started()
        with pytest.raises((TypeError, Exception)):
            record.action = "new_action"  # type: ignore[misc]


class TestInvocationRecordJsonRoundtrip:
    def test_model_dump_roundtrip_is_lossless(self) -> None:
        original = _make_started()
        data = original.model_dump()
        restored = InvocationRecord(**data)
        assert restored.model_dump() == original.model_dump()

    def test_model_dump_includes_all_fields(self) -> None:
        record = _make_started()
        data = record.model_dump()
        expected_keys = {
            "event",
            "invocation_id",
            "profile_id",
            "action",
            "request_text",
            "governance_context_hash",
            "governance_context_available",
            "actor",
            "router_confidence",
            "started_at",
            "completed_at",
            "outcome",
            "evidence_ref",
        }
        assert set(data.keys()) == expected_keys


# ---------------------------------------------------------------------------
# MinimalViableTrailPolicy tests
# ---------------------------------------------------------------------------


def test_mvt_policy_is_frozen_dataclass_instance() -> None:
    """MINIMAL_VIABLE_TRAIL_POLICY must be a MinimalViableTrailPolicy instance, not a dict."""
    assert isinstance(MINIMAL_VIABLE_TRAIL_POLICY, MinimalViableTrailPolicy)
    assert not isinstance(MINIMAL_VIABLE_TRAIL_POLICY, dict)


def test_mvt_policy_is_frozen() -> None:
    """Frozen dataclass raises on attribute assignment."""
    with pytest.raises(Exception):  # FrozenInstanceError (subclass of AttributeError)
        MINIMAL_VIABLE_TRAIL_POLICY.tier_1 = None  # type: ignore[misc]


def test_mvt_policy_tiers_are_tier_policy_instances() -> None:
    assert isinstance(MINIMAL_VIABLE_TRAIL_POLICY.tier_1, TierPolicy)
    assert isinstance(MINIMAL_VIABLE_TRAIL_POLICY.tier_2, TierPolicy)
    assert isinstance(MINIMAL_VIABLE_TRAIL_POLICY.tier_3, TierPolicy)


def test_mvt_policy_tier_1_is_mandatory() -> None:
    assert MINIMAL_VIABLE_TRAIL_POLICY.tier_1.mandatory is True
    assert MINIMAL_VIABLE_TRAIL_POLICY.tier_2.mandatory is False
    assert MINIMAL_VIABLE_TRAIL_POLICY.tier_3.mandatory is False


def test_mvt_policy_tier_1_name() -> None:
    assert MINIMAL_VIABLE_TRAIL_POLICY.tier_1.name == "every_invocation"


def test_mvt_policy_tier_2_name() -> None:
    assert MINIMAL_VIABLE_TRAIL_POLICY.tier_2.name == "evidence_artifact"


def test_mvt_policy_tier_3_name() -> None:
    assert MINIMAL_VIABLE_TRAIL_POLICY.tier_3.name == "durable_project_state"


def test_mvt_policy_storage_paths_present() -> None:
    assert "{invocation_id}" in MINIMAL_VIABLE_TRAIL_POLICY.tier_1.storage_path
    assert "{invocation_id}" in MINIMAL_VIABLE_TRAIL_POLICY.tier_2.storage_path
    assert "{mission_slug}" in MINIMAL_VIABLE_TRAIL_POLICY.tier_3.storage_path


# ---------------------------------------------------------------------------
# TierEligibility / tier_eligible tests
# ---------------------------------------------------------------------------


def test_tier_eligible_tier1_always_true() -> None:
    record = InvocationRecord(
        event="started",
        invocation_id="01ABCDEFGHJKMNPQRSTVWXYZ12",
        profile_id="p",
        action="implement",
    )
    eligibility = tier_eligible(record)
    assert eligibility.tier_1 is True


def test_tier_eligible_tier2_requires_evidence_ref() -> None:
    record_no_ev = InvocationRecord(
        event="completed",
        invocation_id="01ABCDEFGHJKMNPQRSTVWXYZ12",
        profile_id="p",
        action="implement",
    )
    record_with_ev = InvocationRecord(
        event="completed",
        invocation_id="01ABCDEFGHJKMNPQRSTVWXYZ12",
        profile_id="p",
        action="implement",
        evidence_ref=".kittify/evidence/test/",
    )
    assert tier_eligible(record_no_ev).tier_2 is False
    assert tier_eligible(record_with_ev).tier_2 is True


def test_tier_eligible_tier3_for_specify() -> None:
    record = InvocationRecord(
        event="completed",
        invocation_id="01ABCDEFGHJKMNPQRSTVWXYZ12",
        profile_id="p",
        action="specify",
    )
    assert tier_eligible(record).tier_3 is True


def test_tier_eligible_tier3_for_plan() -> None:
    record = InvocationRecord(
        event="completed",
        invocation_id="01ABCDEFGHJKMNPQRSTVWXYZ12",
        profile_id="p",
        action="plan",
    )
    assert tier_eligible(record).tier_3 is True


def test_tier_eligible_tier3_for_tasks() -> None:
    record = InvocationRecord(
        event="completed",
        invocation_id="01ABCDEFGHJKMNPQRSTVWXYZ12",
        profile_id="p",
        action="tasks",
    )
    assert tier_eligible(record).tier_3 is True


def test_tier_eligible_tier3_for_merge() -> None:
    record = InvocationRecord(
        event="completed",
        invocation_id="01ABCDEFGHJKMNPQRSTVWXYZ12",
        profile_id="p",
        action="merge",
    )
    assert tier_eligible(record).tier_3 is True


def test_tier_eligible_tier3_for_accept() -> None:
    record = InvocationRecord(
        event="completed",
        invocation_id="01ABCDEFGHJKMNPQRSTVWXYZ12",
        profile_id="p",
        action="accept",
    )
    assert tier_eligible(record).tier_3 is True


def test_tier_eligible_tier3_not_for_advise() -> None:
    record = InvocationRecord(
        event="completed",
        invocation_id="01ABCDEFGHJKMNPQRSTVWXYZ12",
        profile_id="p",
        action="advise",
    )
    assert tier_eligible(record).tier_3 is False


def test_tier_eligible_tier3_not_for_implement() -> None:
    record = InvocationRecord(
        event="completed",
        invocation_id="01ABCDEFGHJKMNPQRSTVWXYZ12",
        profile_id="p",
        action="implement",
    )
    assert tier_eligible(record).tier_3 is False


# ---------------------------------------------------------------------------
# promote_to_evidence tests
# ---------------------------------------------------------------------------


def test_promote_to_evidence_creates_files(tmp_path: object) -> None:
    from pathlib import Path

    tmp = Path(str(tmp_path))  # type: ignore[arg-type]
    record = InvocationRecord(
        event="completed",
        invocation_id="01KPQRX2EVGMRVB4Q1JQBAZJV3",
        profile_id="cleo",
        action="implement",
    )
    artifact = promote_to_evidence(record, tmp, "# Evidence\n\nThis is evidence.")
    assert artifact.evidence_file.exists()
    assert artifact.record_snapshot.exists()
    assert artifact.evidence_file.read_text() == "# Evidence\n\nThis is evidence."


def test_promote_to_evidence_record_snapshot_is_valid_json(tmp_path: object) -> None:
    import json
    from pathlib import Path

    tmp = Path(str(tmp_path))  # type: ignore[arg-type]
    record = InvocationRecord(
        event="completed",
        invocation_id="01KPQRX2EVGMRVB4Q1JQBAZJV3",
        profile_id="cleo",
        action="implement",
    )
    artifact = promote_to_evidence(record, tmp, "content")
    data = json.loads(artifact.record_snapshot.read_text())
    assert data["invocation_id"] == "01KPQRX2EVGMRVB4Q1JQBAZJV3"


def test_promote_to_evidence_creates_exactly_two_files(tmp_path: object) -> None:
    from pathlib import Path

    tmp = Path(str(tmp_path))  # type: ignore[arg-type]
    record = InvocationRecord(
        event="completed",
        invocation_id="01KPQRX2EVGMRVB4Q1JQBAZJV3",
        profile_id="cleo",
        action="implement",
    )
    artifact = promote_to_evidence(record, tmp, "content")
    files = list(artifact.directory.iterdir())
    assert len(files) == 2


def test_promote_to_evidence_directory_named_by_invocation_id(tmp_path: object) -> None:
    from pathlib import Path

    tmp = Path(str(tmp_path))  # type: ignore[arg-type]
    record = InvocationRecord(
        event="completed",
        invocation_id="01KPQRX2EVGMRVB4Q1JQBAZJV3",
        profile_id="cleo",
        action="implement",
    )
    artifact = promote_to_evidence(record, tmp, "content")
    assert artifact.directory.name == "01KPQRX2EVGMRVB4Q1JQBAZJV3"
    assert artifact.invocation_id == "01KPQRX2EVGMRVB4Q1JQBAZJV3"


# ---------------------------------------------------------------------------
# TIER_3_ACTIONS tests
# ---------------------------------------------------------------------------


def test_tier3_actions_contains_expected() -> None:
    assert "specify" in TIER_3_ACTIONS
    assert "plan" in TIER_3_ACTIONS
    assert "tasks" in TIER_3_ACTIONS
    assert "merge" in TIER_3_ACTIONS
    assert "accept" in TIER_3_ACTIONS


def test_tier3_actions_excludes_advise() -> None:
    assert "advise" not in TIER_3_ACTIONS


def test_tier3_actions_excludes_implement() -> None:
    assert "implement" not in TIER_3_ACTIONS


def test_tier3_actions_is_frozenset() -> None:
    assert isinstance(TIER_3_ACTIONS, frozenset)
