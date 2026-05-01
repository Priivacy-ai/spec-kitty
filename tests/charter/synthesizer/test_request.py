"""Tests for SynthesisRequest, SynthesisTarget, and normalize_request_for_hash.

Covers:
T001 — Backward-compat: existing requests (no evidence) produce identical hashes.
T002 — EvidenceBundle() empty produces same hash as evidence=None.
T003 — Non-empty code signals produce a different hash.
T004 — URL list is order-insensitive.
T005 — representative_files is order-insensitive.
T006 — run_id is excluded from hash.
T007 — detected_at is excluded from hash (timestamps do not affect hash).
"""

from __future__ import annotations


from charter.synthesizer.evidence import (
    CodeSignals,
    CorpusEntry,
    CorpusSnapshot,
    EvidenceBundle,
)
from charter.synthesizer.request import (
    SynthesisRequest,
    SynthesisTarget,
    compute_inputs_hash,
)


# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------

_ADAPTER_ID = "fixture"
_ADAPTER_VERSION = "0.1.0"


def _make_target() -> SynthesisTarget:
    return SynthesisTarget(
        kind="directive",
        slug="project-decision-doc-directive",
        title="Project Decision Documentation Directive",
        artifact_id="PROJECT_001",
        source_section="testing_philosophy",
        source_urns=("directive:DIRECTIVE_003",),
    )


def _make_base_request(**overrides: object) -> SynthesisRequest:
    """Create the canonical sample request (matches conftest.py fixture)."""
    defaults: dict = {
        "target": _make_target(),
        "interview_snapshot": {
            "mission_type": "software_dev",
            "language_scope": ["python"],
            "testing_philosophy": "test-driven development with high coverage",
            "neutrality_posture": "balanced",
            "selected_directives": ["DIRECTIVE_003"],
            "risk_appetite": "moderate",
        },
        "doctrine_snapshot": {
            "directives": {
                "DIRECTIVE_003": {
                    "id": "DIRECTIVE_003",
                    "title": "Decision Documentation",
                    "body": "Document significant architectural decisions via ADRs.",
                }
            },
            "tactics": {},
            "styleguides": {},
        },
        "drg_snapshot": {
            "nodes": [{"urn": "directive:DIRECTIVE_003", "kind": "directive", "id": "DIRECTIVE_003"}],
            "edges": [],
            "schema_version": "1",
        },
        "run_id": "01KPE222CD1MMCYEGB3ZCY51VR",
        "adapter_hints": {"language": "python"},
    }
    defaults.update(overrides)
    return SynthesisRequest(**defaults)  # type: ignore[arg-type]


def _make_code_signals(
    *,
    detected_at: str = "2026-04-19T10:00:00+00:00",
) -> CodeSignals:
    return CodeSignals(
        stack_id="python",
        primary_language="python",
        frameworks=("django",),
        test_frameworks=("pytest",),
        scope_tag="python",
        representative_files=("src/main.py", "src/utils.py"),
        detected_at=detected_at,
    )


# ---------------------------------------------------------------------------
# T001 — Backward-compat: no evidence → byte-for-byte identical hash
# ---------------------------------------------------------------------------

# Hash recorded before WP01 was implemented (pre-evidence code path).
# DO NOT change this value — it is the backward-compat anchor.
_PRE_WP01_HASH = "7a21550328faa83b24c32270b97cb4abf34eb6e2558d029fe7b45fac4632ab7a"


def test_backward_compat_no_evidence_hash_unchanged() -> None:
    """Requests without evidence produce the same hash as the pre-WP01 code path."""
    request = _make_base_request()
    h = compute_inputs_hash(request, _ADAPTER_ID, _ADAPTER_VERSION)
    assert h == _PRE_WP01_HASH, (
        f"Hash changed! Got {h!r}, expected {_PRE_WP01_HASH!r}. This breaks backward compatibility with existing fixtures. See ADR-2026-04-17-1."
    )


def test_backward_compat_explicit_none_evidence_hash_unchanged() -> None:
    """Explicitly passing evidence=None produces the same hash as the pre-WP01 path."""
    request = _make_base_request(evidence=None)
    h = compute_inputs_hash(request, _ADAPTER_ID, _ADAPTER_VERSION)
    assert h == _PRE_WP01_HASH


# ---------------------------------------------------------------------------
# T002 — EvidenceBundle() empty produces same hash as evidence=None
# ---------------------------------------------------------------------------


def test_empty_evidence_bundle_same_hash_as_none() -> None:
    """An empty EvidenceBundle (is_empty=True) does not change the hash."""
    request_none = _make_base_request(evidence=None)
    request_empty = _make_base_request(evidence=EvidenceBundle())

    h_none = compute_inputs_hash(request_none, _ADAPTER_ID, _ADAPTER_VERSION)
    h_empty = compute_inputs_hash(request_empty, _ADAPTER_ID, _ADAPTER_VERSION)

    assert h_none == h_empty
    assert h_empty == _PRE_WP01_HASH


# ---------------------------------------------------------------------------
# T003 — Non-empty code signals produce a different hash
# ---------------------------------------------------------------------------


def test_non_empty_code_signals_change_hash() -> None:
    """Adding code signals to the evidence changes the fixture hash."""
    request_no_evidence = _make_base_request(evidence=None)
    request_with_signals = _make_base_request(evidence=EvidenceBundle(code_signals=_make_code_signals()))

    h_base = compute_inputs_hash(request_no_evidence, _ADAPTER_ID, _ADAPTER_VERSION)
    h_signals = compute_inputs_hash(request_with_signals, _ADAPTER_ID, _ADAPTER_VERSION)

    assert h_base != h_signals


def test_url_list_changes_hash() -> None:
    """Adding URLs to the evidence changes the fixture hash."""
    request_no_evidence = _make_base_request(evidence=None)
    request_with_urls = _make_base_request(evidence=EvidenceBundle(url_list=("https://example.com",)))

    h_base = compute_inputs_hash(request_no_evidence, _ADAPTER_ID, _ADAPTER_VERSION)
    h_urls = compute_inputs_hash(request_with_urls, _ADAPTER_ID, _ADAPTER_VERSION)

    assert h_base != h_urls


def test_corpus_snapshot_changes_hash() -> None:
    """Adding a corpus snapshot to the evidence changes the fixture hash."""
    request_no_evidence = _make_base_request(evidence=None)
    snap = CorpusSnapshot(
        snapshot_id="python-v1.0.0",
        profile_key="python",
        entries=(CorpusEntry(topic="testing", tags=("quality",), guidance="Write tests."),),
        loaded_at="2026-04-19T10:00:00+00:00",
    )
    request_with_corpus = _make_base_request(evidence=EvidenceBundle(corpus_snapshot=snap))

    h_base = compute_inputs_hash(request_no_evidence, _ADAPTER_ID, _ADAPTER_VERSION)
    h_corpus = compute_inputs_hash(request_with_corpus, _ADAPTER_ID, _ADAPTER_VERSION)

    assert h_base != h_corpus


# ---------------------------------------------------------------------------
# T004 — URL list is order-insensitive
# ---------------------------------------------------------------------------


def test_url_list_order_insensitive() -> None:
    """("b", "a") and ("a", "b") produce the same hash."""
    request_ab = _make_base_request(evidence=EvidenceBundle(url_list=("https://a.com", "https://b.com")))
    request_ba = _make_base_request(evidence=EvidenceBundle(url_list=("https://b.com", "https://a.com")))

    h_ab = compute_inputs_hash(request_ab, _ADAPTER_ID, _ADAPTER_VERSION)
    h_ba = compute_inputs_hash(request_ba, _ADAPTER_ID, _ADAPTER_VERSION)

    assert h_ab == h_ba


# ---------------------------------------------------------------------------
# T005 — representative_files is order-insensitive
# ---------------------------------------------------------------------------


def test_representative_files_order_insensitive() -> None:
    """Different orderings of representative_files produce the same hash."""
    signals_ab = CodeSignals(
        stack_id="python",
        primary_language="python",
        frameworks=(),
        test_frameworks=(),
        scope_tag="python",
        representative_files=("src/a.py", "src/b.py"),
        detected_at="2026-04-19T10:00:00+00:00",
    )
    signals_ba = CodeSignals(
        stack_id="python",
        primary_language="python",
        frameworks=(),
        test_frameworks=(),
        scope_tag="python",
        representative_files=("src/b.py", "src/a.py"),
        detected_at="2026-04-19T10:00:00+00:00",
    )

    request_ab = _make_base_request(evidence=EvidenceBundle(code_signals=signals_ab))
    request_ba = _make_base_request(evidence=EvidenceBundle(code_signals=signals_ba))

    h_ab = compute_inputs_hash(request_ab, _ADAPTER_ID, _ADAPTER_VERSION)
    h_ba = compute_inputs_hash(request_ba, _ADAPTER_ID, _ADAPTER_VERSION)

    assert h_ab == h_ba


# ---------------------------------------------------------------------------
# T006 — run_id is excluded from hash
# ---------------------------------------------------------------------------


def test_run_id_excluded_from_hash() -> None:
    """Changing run_id does not change the fixture hash."""
    request_a = _make_base_request(run_id="01AAAAAAAAAAAAAAAAAAAAAAAAA")
    request_b = _make_base_request(run_id="01ZZZZZZZZZZZZZZZZZZZZZZZZZ")

    h_a = compute_inputs_hash(request_a, _ADAPTER_ID, _ADAPTER_VERSION)
    h_b = compute_inputs_hash(request_b, _ADAPTER_ID, _ADAPTER_VERSION)

    assert h_a == h_b


# ---------------------------------------------------------------------------
# T007 — detected_at (and other timestamps) excluded from hash
# ---------------------------------------------------------------------------


def test_detected_at_excluded_from_hash() -> None:
    """Same evidence with different detected_at timestamps produce the same hash."""
    signals_t1 = _make_code_signals(detected_at="2026-01-01T00:00:00+00:00")
    signals_t2 = _make_code_signals(detected_at="2026-12-31T23:59:59+00:00")

    request_t1 = _make_base_request(evidence=EvidenceBundle(code_signals=signals_t1))
    request_t2 = _make_base_request(evidence=EvidenceBundle(code_signals=signals_t2))

    h_t1 = compute_inputs_hash(request_t1, _ADAPTER_ID, _ADAPTER_VERSION)
    h_t2 = compute_inputs_hash(request_t2, _ADAPTER_ID, _ADAPTER_VERSION)

    assert h_t1 == h_t2


def test_corpus_loaded_at_excluded_from_hash() -> None:
    """Same corpus snapshot with different loaded_at produces the same hash."""
    snap_t1 = CorpusSnapshot(
        snapshot_id="python-v1.0.0",
        profile_key="python",
        entries=(CorpusEntry(topic="testing", tags=("quality",), guidance="Write tests."),),
        loaded_at="2026-01-01T00:00:00+00:00",
    )
    snap_t2 = CorpusSnapshot(
        snapshot_id="python-v1.0.0",
        profile_key="python",
        entries=(CorpusEntry(topic="testing", tags=("quality",), guidance="Write tests."),),
        loaded_at="2026-12-31T23:59:59+00:00",
    )

    request_t1 = _make_base_request(evidence=EvidenceBundle(corpus_snapshot=snap_t1))
    request_t2 = _make_base_request(evidence=EvidenceBundle(corpus_snapshot=snap_t2))

    h_t1 = compute_inputs_hash(request_t1, _ADAPTER_ID, _ADAPTER_VERSION)
    h_t2 = compute_inputs_hash(request_t2, _ADAPTER_ID, _ADAPTER_VERSION)

    assert h_t1 == h_t2


def test_collected_at_excluded_from_hash() -> None:
    """Same bundle with different collected_at produces the same hash."""
    cs = _make_code_signals()
    bundle_t1 = EvidenceBundle(code_signals=cs, collected_at="2026-01-01T00:00:00+00:00")
    bundle_t2 = EvidenceBundle(code_signals=cs, collected_at="2026-12-31T23:59:59+00:00")

    request_t1 = _make_base_request(evidence=bundle_t1)
    request_t2 = _make_base_request(evidence=bundle_t2)

    h_t1 = compute_inputs_hash(request_t1, _ADAPTER_ID, _ADAPTER_VERSION)
    h_t2 = compute_inputs_hash(request_t2, _ADAPTER_ID, _ADAPTER_VERSION)

    assert h_t1 == h_t2
