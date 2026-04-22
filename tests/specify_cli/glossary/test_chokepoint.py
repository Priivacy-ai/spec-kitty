"""Tests for GlossaryChokepoint and GlossaryObservationBundle (T014).

Coverage checklist:
- Exception injection: broken _load_index -> run() returns error-bundle, no raise
- GlossaryObservationBundle is frozen (immutable)
- to_dict() produces JSON-serialisable output
- Clean request (no index terms) -> error_msg=None, empty collections
- _load_index() idempotent: calling twice returns same object
- DEFAULT_APPLICABLE_SCOPES contains SPEC_KITTY_CORE and TEAM_DOMAIN,
  not MISSION_LOCAL
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from specify_cli.glossary.chokepoint import (
    DEFAULT_APPLICABLE_SCOPES,
    GlossaryChokepoint,
    GlossaryObservationBundle,
)
from specify_cli.glossary.drg_builder import GlossaryTermIndex
from specify_cli.glossary.models import (
    ConflictType,
    Provenance,
    SemanticConflict,
    Severity,
    SenseStatus,
    TermSense,
    TermSurface,
    SenseRef,
)
from specify_cli.glossary.scope import GlossaryScope
from specify_cli.glossary.store import GlossaryStore

pytestmark = pytest.mark.fast

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_LOG = Path("/dev/null")


def _active_sense(surface: str, scope: str = "spec_kitty_core", definition: str = "") -> TermSense:
    return TermSense(
        surface=TermSurface(surface),
        scope=scope,
        definition=definition or f"Definition of {surface}",
        provenance=Provenance(
            actor_id="test",
            timestamp=datetime(2026, 1, 1),
            source="test",
        ),
        confidence=1.0,
        status=SenseStatus.ACTIVE,
    )


def _make_store(*senses: TermSense) -> GlossaryStore:
    store = GlossaryStore(_FAKE_LOG)
    for s in senses:
        store.add_sense(s)
    return store


def _chokepoint_with_store(store: GlossaryStore, repo_root: Path | None = None) -> GlossaryChokepoint:
    """Return a GlossaryChokepoint that has its index pre-built from *store*."""
    from specify_cli.glossary.drg_builder import build_index

    cp = GlossaryChokepoint(repo_root or Path("/tmp/fake"))
    # Pre-build the index so no filesystem access is needed
    cp._index = build_index(store, [s.value for s in DEFAULT_APPLICABLE_SCOPES])
    return cp


# ---------------------------------------------------------------------------
# T014-1: Exception injection — broken _load_index -> error-bundle, no raise
# ---------------------------------------------------------------------------


def test_run_returns_error_bundle_on_exception():
    """Injecting a broken _load_index must yield error_msg, never propagate."""

    class BrokenChokepoint(GlossaryChokepoint):
        def _load_index(self) -> GlossaryTermIndex:
            raise RuntimeError("simulated index failure")

    cp = BrokenChokepoint(Path("/tmp/fake"))
    bundle = cp.run("implement a lane transition in the workspace")

    # Must not raise; must return an error-bundle
    assert bundle.error_msg is not None
    assert "simulated index failure" in bundle.error_msg
    assert bundle.matched_urns == ()
    assert bundle.all_conflicts == ()
    assert bundle.high_severity == ()
    assert bundle.tokens_checked == 0
    assert bundle.duration_ms >= 0.0


def test_run_error_bundle_has_positive_duration():
    """Even for error bundles the duration_ms field is populated."""

    class AlwaysFails(GlossaryChokepoint):
        def _load_index(self) -> GlossaryTermIndex:
            raise ValueError("always fails")

    cp = AlwaysFails(Path("/tmp/fake"))
    bundle = cp.run("some text")
    assert bundle.duration_ms >= 0.0


# ---------------------------------------------------------------------------
# T014-2: GlossaryObservationBundle immutability (frozen=True)
# ---------------------------------------------------------------------------


def test_observation_bundle_is_frozen():
    """GlossaryObservationBundle is a frozen dataclass — attribute assignment must raise."""
    bundle = GlossaryObservationBundle(
        matched_urns=(),
        high_severity=(),
        all_conflicts=(),
        tokens_checked=0,
        duration_ms=1.0,
    )
    with pytest.raises((AttributeError, TypeError)):
        bundle.matched_urns = ("glossary:abc",)  # type: ignore[misc]


def test_observation_bundle_fields_are_tuples():
    """matched_urns / high_severity / all_conflicts must be tuples (immutable)."""
    bundle = GlossaryObservationBundle(
        matched_urns=("glossary:aaa",),
        high_severity=(),
        all_conflicts=(),
        tokens_checked=5,
        duration_ms=2.5,
    )
    assert isinstance(bundle.matched_urns, tuple)
    assert isinstance(bundle.high_severity, tuple)
    assert isinstance(bundle.all_conflicts, tuple)


# ---------------------------------------------------------------------------
# T014-3: to_dict() produces JSON-serialisable output
# ---------------------------------------------------------------------------


def test_to_dict_is_json_serialisable_empty():
    """to_dict() on an empty bundle must round-trip through json.dumps."""
    bundle = GlossaryObservationBundle(
        matched_urns=(),
        high_severity=(),
        all_conflicts=(),
        tokens_checked=0,
        duration_ms=0.5,
        error_msg=None,
    )
    d = bundle.to_dict()
    # Must not raise
    serialised = json.dumps(d)
    restored = json.loads(serialised)
    assert restored["matched_urns"] == []
    assert restored["all_conflicts"] == []
    assert restored["high_severity"] == []
    assert restored["tokens_checked"] == 0
    assert restored["error_msg"] is None


def test_to_dict_is_json_serialisable_with_error():
    """Error bundles with non-None error_msg must also serialise cleanly."""
    bundle = GlossaryObservationBundle(
        matched_urns=(),
        high_severity=(),
        all_conflicts=(),
        tokens_checked=0,
        duration_ms=0.5,
        error_msg="boom",
    )
    serialised = json.dumps(bundle.to_dict())
    restored = json.loads(serialised)
    assert restored["error_msg"] == "boom"


def test_to_dict_contains_expected_keys():
    """to_dict() must include all 6 expected keys."""
    bundle = GlossaryObservationBundle(
        matched_urns=(),
        high_severity=(),
        all_conflicts=(),
        tokens_checked=3,
        duration_ms=1.2,
    )
    d = bundle.to_dict()
    for key in ("matched_urns", "high_severity", "all_conflicts", "tokens_checked", "duration_ms", "error_msg"):
        assert key in d, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# T014-4: Clean request with no index terms -> error_msg=None, empty lists
# ---------------------------------------------------------------------------


def test_clean_request_no_index_terms():
    """A request text with no terms from the index yields an empty, clean bundle."""
    store = _make_store()  # empty store
    cp = _chokepoint_with_store(store)

    bundle = cp.run("hello world foo bar")

    assert bundle.error_msg is None
    assert bundle.matched_urns == ()
    assert bundle.all_conflicts == ()
    assert bundle.high_severity == ()


def test_clean_request_returns_noerror_bundle():
    """run() on an empty store must return a valid bundle with no error."""
    store = _make_store()
    cp = _chokepoint_with_store(store)
    bundle = cp.run("some completely unrelated text that is not in the glossary")
    assert bundle.error_msg is None
    assert bundle.tokens_checked >= 0
    assert isinstance(bundle.duration_ms, float)


# ---------------------------------------------------------------------------
# T014-5: _load_index() is idempotent — two calls return same object
# ---------------------------------------------------------------------------


def test_load_index_idempotent(tmp_path: Path):
    """Calling _load_index() twice returns the exact same object."""
    # Point at tmp_path which has no seed files — that's fine, store is empty
    cp = GlossaryChokepoint(tmp_path)
    idx1 = cp._load_index()
    idx2 = cp._load_index()
    assert idx1 is idx2  # same object identity, not just equality


def test_load_index_caches_after_first_call(tmp_path: Path):
    """After _load_index(), self._index is no longer None."""
    cp = GlossaryChokepoint(tmp_path)
    assert cp._index is None  # starts None
    cp._load_index()
    assert cp._index is not None


# ---------------------------------------------------------------------------
# T014-6: DEFAULT_APPLICABLE_SCOPES contains SPEC_KITTY_CORE and TEAM_DOMAIN
#          but NOT MISSION_LOCAL
# ---------------------------------------------------------------------------


def test_default_scopes_contains_spec_kitty_core():
    """DEFAULT_APPLICABLE_SCOPES must include SPEC_KITTY_CORE."""
    assert GlossaryScope.SPEC_KITTY_CORE in DEFAULT_APPLICABLE_SCOPES


def test_default_scopes_contains_team_domain():
    """DEFAULT_APPLICABLE_SCOPES must include TEAM_DOMAIN."""
    assert GlossaryScope.TEAM_DOMAIN in DEFAULT_APPLICABLE_SCOPES


def test_default_scopes_excludes_mission_local():
    """DEFAULT_APPLICABLE_SCOPES must NOT include MISSION_LOCAL."""
    assert GlossaryScope.MISSION_LOCAL not in DEFAULT_APPLICABLE_SCOPES


# ---------------------------------------------------------------------------
# Additional smoke tests: matched term produces URN
# ---------------------------------------------------------------------------


def test_matched_term_appears_in_matched_urns():
    """A term in the index that appears in the request must produce a matched URN."""
    sense = _active_sense("lane")
    store = _make_store(sense)
    cp = _chokepoint_with_store(store)

    bundle = cp.run("implement a lane transition")

    assert len(bundle.matched_urns) >= 1
    # URN format: glossary:<8-hex-chars>
    for urn in bundle.matched_urns:
        assert urn.startswith("glossary:")


def test_multiple_matched_terms():
    """Multiple index terms in request text should all produce URN matches."""
    senses = [
        _active_sense("lane"),
        _active_sense("mission"),
    ]
    store = _make_store(*senses)
    cp = _chokepoint_with_store(store)

    # Both "lane" and "mission" appear in this text
    bundle = cp.run("implement a lane for this mission today")

    assert len(bundle.matched_urns) >= 2


def test_duration_ms_is_non_negative():
    """duration_ms must always be >= 0."""
    store = _make_store()
    cp = _chokepoint_with_store(store)
    bundle = cp.run("any text")
    assert bundle.duration_ms >= 0.0


def test_to_dict_all_conflicts_serialisable_with_conflict(tmp_path: Path):
    """to_dict() must serialise non-empty conflict lists cleanly."""
    # Build a store with two active senses for the same surface to trigger AMBIGUOUS
    sense1 = TermSense(
        surface=TermSurface("lane"),
        scope="spec_kitty_core",
        definition="A lane is an execution track.",
        provenance=Provenance(actor_id="test", timestamp=datetime(2026, 1, 1), source="test"),
        confidence=1.0,
        status=SenseStatus.ACTIVE,
    )
    sense2 = TermSense(
        surface=TermSurface("lane"),
        scope="team_domain",
        definition="A lane is a bowling alley lane.",
        provenance=Provenance(actor_id="test", timestamp=datetime(2026, 1, 1), source="test"),
        confidence=1.0,
        status=SenseStatus.ACTIVE,
    )
    store = _make_store(sense1, sense2)
    cp = _chokepoint_with_store(store)

    bundle = cp.run("implement a lane transition today")

    # Serialise — must not raise
    d = bundle.to_dict()
    serialised = json.dumps(d)
    restored = json.loads(serialised)
    # Verify structure
    assert isinstance(restored["all_conflicts"], list)
    assert isinstance(restored["matched_urns"], list)
