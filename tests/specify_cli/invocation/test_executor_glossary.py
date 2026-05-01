"""Tests for GlossaryChokepoint integration in ProfileInvocationExecutor (WP03).

Five focused tests covering:
1. invoke() returns payload with glossary_observations present
2. to_dict() includes "glossary_observations" key
3. Exception in chokepoint -> error-bundle returned, invocation completes normally
4. Clean invocation (no conflicts) -> NO glossary_checked line in trail JSONL
5. Conflict invocation -> glossary_checked line appears in trail JSONL
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.glossary.chokepoint import GlossaryObservationBundle
from specify_cli.invocation.executor import InvocationPayload, ProfileInvocationExecutor
from specify_cli.invocation.writer import EVENTS_DIR

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "profiles"

_COMPACT_CTX = MagicMock()
_COMPACT_CTX.mode = "compact"
_COMPACT_CTX.text = "compact governance context"


def _setup_fixture_profiles(tmp_path: Path) -> None:
    """Copy fixture profiles into simulated project structure."""
    profiles_dir = tmp_path / ".kittify" / "profiles"
    profiles_dir.mkdir(parents=True)
    for yaml_file in FIXTURES_DIR.glob("*.agent.yaml"):
        shutil.copy(yaml_file, profiles_dir / yaml_file.name)


def _clean_bundle() -> GlossaryObservationBundle:
    """A bundle with no conflicts and no error (clean invocation)."""
    return GlossaryObservationBundle(
        matched_urns=(),
        high_severity=(),
        all_conflicts=(),
        tokens_checked=5,
        duration_ms=1.2,
        error_msg=None,
    )


def _conflict_bundle() -> GlossaryObservationBundle:
    """A non-clean bundle that triggers the glossary_checked trail event.

    Uses ``error_msg`` (non-None) as the trigger condition rather than building
    real SemanticConflict objects — this avoids coupling the test to the full
    SemanticConflict / TermSurface / Provenance object graph while still
    exercising the write path for non-clean invocations.

    Note: The invariant is ``not bundle.all_conflicts and bundle.error_msg is None``
    means "clean".  Having ``error_msg`` set (even with empty conflicts) is
    sufficient to trigger the glossary_checked write.
    """
    return GlossaryObservationBundle(
        matched_urns=("glossary:d93244e7",),
        high_severity=(),
        all_conflicts=(),
        tokens_checked=8,
        duration_ms=2.7,
        error_msg="degraded: term index unavailable",  # non-null triggers write
    )


def _error_bundle() -> GlossaryObservationBundle:
    """A bundle produced when the chokepoint raises an unexpected exception."""
    return GlossaryObservationBundle(
        matched_urns=(),
        high_severity=(),
        all_conflicts=(),
        tokens_checked=0,
        duration_ms=0.0,
        error_msg="RuntimeError('chokepoint exploded')",
    )


# ---------------------------------------------------------------------------
# Test 1: invoke() returns payload with glossary_observations present
# ---------------------------------------------------------------------------


class TestInvokeReturnsGlossaryObservations:
    def test_invoke_payload_has_glossary_observations_attribute(
        self, tmp_path: Path
    ) -> None:
        """invoke() must attach glossary_observations to the returned InvocationPayload."""
        _setup_fixture_profiles(tmp_path)
        with patch(
            "specify_cli.invocation.executor.build_charter_context",
            return_value=_COMPACT_CTX,
        ), patch(
            "specify_cli.glossary.chokepoint.GlossaryChokepoint.run",
            return_value=_clean_bundle(),
        ):
            executor = ProfileInvocationExecutor(tmp_path)
            payload = executor.invoke("implement the login feature", profile_hint="implementer-fixture")

        assert isinstance(payload, InvocationPayload)
        assert hasattr(payload, "glossary_observations"), (
            "InvocationPayload must have a glossary_observations attribute"
        )
        assert isinstance(payload.glossary_observations, GlossaryObservationBundle)


# ---------------------------------------------------------------------------
# Test 2: to_dict() includes "glossary_observations" key
# ---------------------------------------------------------------------------


class TestToDictIncludesGlossaryObservations:
    def test_to_dict_contains_glossary_observations_key(
        self, tmp_path: Path
    ) -> None:
        """to_dict() must include 'glossary_observations' and it must be JSON-serialisable."""
        _setup_fixture_profiles(tmp_path)
        with patch(
            "specify_cli.invocation.executor.build_charter_context",
            return_value=_COMPACT_CTX,
        ), patch(
            "specify_cli.glossary.chokepoint.GlossaryChokepoint.run",
            return_value=_clean_bundle(),
        ):
            executor = ProfileInvocationExecutor(tmp_path)
            payload = executor.invoke("plan the sprint", profile_hint="implementer-fixture")

        d = payload.to_dict()
        assert "glossary_observations" in d, (
            "'glossary_observations' key must be present in to_dict() output"
        )
        # The value must be a plain dict (JSON-serialisable), not the dataclass object.
        obs = d["glossary_observations"]
        assert isinstance(obs, dict), (
            "to_dict() must convert GlossaryObservationBundle to a plain dict"
        )
        # Verify round-trippable through json.dumps (no TypeError)
        serialised = json.dumps(d)
        assert "glossary_observations" in json.loads(serialised)


# ---------------------------------------------------------------------------
# Test 3: Exception in chokepoint → error-bundle returned, invocation completes
# ---------------------------------------------------------------------------


class TestChokepointExceptionHandled:
    def test_chokepoint_exception_returns_error_bundle_and_completes(
        self, tmp_path: Path
    ) -> None:
        """When the chokepoint raises, an error-bundle is produced and invoke() still returns."""
        _setup_fixture_profiles(tmp_path)
        with patch(
            "specify_cli.invocation.executor.build_charter_context",
            return_value=_COMPACT_CTX,
        ), patch(
            "specify_cli.glossary.chokepoint.GlossaryChokepoint.run",
            side_effect=RuntimeError("chokepoint exploded"),
        ):
            executor = ProfileInvocationExecutor(tmp_path)
            # Must NOT raise — exceptions are swallowed and converted to error-bundles.
            payload = executor.invoke("do something", profile_hint="implementer-fixture")

        assert isinstance(payload, InvocationPayload)
        bundle = payload.glossary_observations
        assert isinstance(bundle, GlossaryObservationBundle)
        assert bundle.error_msg is not None, "error_msg must be set on error-bundle"
        assert "chokepoint exploded" in bundle.error_msg or "RuntimeError" in bundle.error_msg
        # Other fields must be empty/zero on error-bundles.
        assert bundle.matched_urns == ()
        assert bundle.all_conflicts == ()
        assert bundle.tokens_checked == 0


# ---------------------------------------------------------------------------
# Test 4: Clean invocation → NO glossary_checked line in trail JSONL
# ---------------------------------------------------------------------------


class TestCleanInvocationNoGlossaryCheckedEvent:
    def test_clean_invocation_produces_no_glossary_checked_line(
        self, tmp_path: Path
    ) -> None:
        """When the bundle is clean (no conflicts, no error), no glossary_checked event
        is written to the Tier 1 JSONL trail file."""
        _setup_fixture_profiles(tmp_path)
        with patch(
            "specify_cli.invocation.executor.build_charter_context",
            return_value=_COMPACT_CTX,
        ), patch(
            "specify_cli.glossary.chokepoint.GlossaryChokepoint.run",
            return_value=_clean_bundle(),
        ):
            executor = ProfileInvocationExecutor(tmp_path)
            payload = executor.invoke("review the code", profile_hint="implementer-fixture")

        events_dir = tmp_path / EVENTS_DIR
        jsonl_file = events_dir / f"{payload.invocation_id}.jsonl"
        assert jsonl_file.exists(), "Tier 1 JSONL file must exist after invoke()"

        lines = [line.strip() for line in jsonl_file.read_text().splitlines() if line.strip()]
        event_types = [json.loads(line).get("event") for line in lines]

        assert "glossary_checked" not in event_types, (
            "Clean invocations must NOT write a glossary_checked event to the trail"
        )
        assert "started" in event_types, "started event must always be present"


# ---------------------------------------------------------------------------
# Test 5: Conflict invocation → glossary_checked line appears in trail JSONL
# ---------------------------------------------------------------------------


class TestConflictInvocationWritesGlossaryCheckedEvent:
    def test_conflict_invocation_writes_glossary_checked_event(
        self, tmp_path: Path
    ) -> None:
        """When the bundle is non-clean (error_msg set or all_conflicts non-empty),
        a glossary_checked event is appended to the Tier 1 JSONL trail file."""
        _setup_fixture_profiles(tmp_path)
        with patch(
            "specify_cli.invocation.executor.build_charter_context",
            return_value=_COMPACT_CTX,
        ), patch(
            "specify_cli.glossary.chokepoint.GlossaryChokepoint.run",
            return_value=_conflict_bundle(),
        ):
            executor = ProfileInvocationExecutor(tmp_path)
            payload = executor.invoke("implement the feature", profile_hint="implementer-fixture")

        events_dir = tmp_path / EVENTS_DIR
        jsonl_file = events_dir / f"{payload.invocation_id}.jsonl"
        assert jsonl_file.exists(), "Tier 1 JSONL file must exist after invoke()"

        lines = [line.strip() for line in jsonl_file.read_text().splitlines() if line.strip()]
        parsed = [json.loads(line) for line in lines]
        event_types = [p.get("event") for p in parsed]

        assert "glossary_checked" in event_types, (
            "Conflict invocations must write a glossary_checked event to the trail"
        )

        # Find and validate the glossary_checked event content.
        gc_events = [p for p in parsed if p.get("event") == "glossary_checked"]
        assert len(gc_events) == 1, "Exactly one glossary_checked event should be written"
        gc = gc_events[0]

        assert gc["invocation_id"] == payload.invocation_id
        # The bundle has error_msg set (the trigger condition) — verify it's present.
        assert "error_msg" in gc
        assert gc["error_msg"] is not None, "error_msg must be present in the trail event"
        assert "matched_urns" in gc
        assert "tokens_checked" in gc
        assert "duration_ms" in gc
