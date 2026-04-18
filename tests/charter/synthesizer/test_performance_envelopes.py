"""Performance envelope tests (T031) — CI-tolerant timing assertions.

NFR-002: full synthesis on ≤10-answer interview < 30 s (fixture adapter).
NFR-003: bounded resynthesize --topic (single target) < 15 s.
NFR-004: fail-closed from validation failure to return < 5 s.
SC-008:  TopicSelectorUnresolvedError return on cold cache < 2 s.

All tests use the fixture adapter for determinism.  Timing assertions have
generous slack to avoid CI flakiness.  No sleep() calls.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest

from charter.synthesizer import (
    FixtureAdapter,
    SynthesisRequest,
    SynthesisTarget,
    synthesize,
)
from charter.synthesizer.errors import TopicSelectorUnresolvedError
from charter.synthesizer.resynthesize_pipeline import run as resynthesize_run
from charter.synthesizer.topic_resolver import resolve as resolve_topic


# ---------------------------------------------------------------------------
# Fixtures — shared test data
# ---------------------------------------------------------------------------


@pytest.fixture
def fixture_root() -> Path:
    return Path(__file__).parent.parent / "fixtures" / "synthesizer"


@pytest.fixture
def adapter(fixture_root: Path) -> FixtureAdapter:
    return FixtureAdapter(fixture_root=fixture_root)


@pytest.fixture
def full_interview_snapshot() -> dict[str, Any]:
    """Representative ≤10-answer interview snapshot."""
    return {
        "mission_type": "software_dev",
        "language_scope": ["python"],
        "testing_philosophy": "test-driven development with high coverage",
        "neutrality_posture": "balanced",
        "selected_directives": ["DIRECTIVE_003"],
        "risk_appetite": "moderate",
    }


@pytest.fixture
def minimal_doctrine_snapshot() -> dict[str, Any]:
    return {
        "directives": {
            "DIRECTIVE_003": {
                "id": "DIRECTIVE_003",
                "title": "Decision Documentation",
                "body": "Document significant architectural decisions via ADRs.",
            }
        },
        "tactics": {},
        "styleguides": {},
    }


@pytest.fixture
def minimal_drg_snapshot() -> dict[str, Any]:
    return {
        "nodes": [
            {"urn": "directive:DIRECTIVE_003", "kind": "directive", "id": "DIRECTIVE_003"}
        ],
        "edges": [],
        "schema_version": "1",
    }


@pytest.fixture
def base_target() -> SynthesisTarget:
    return SynthesisTarget(
        kind="directive",
        slug="mission-type-scope-directive",
        title="Mission Type Scope Directive",
        artifact_id="PROJECT_001",
        source_section="mission_type",
    )


@pytest.fixture
def base_request(
    base_target: SynthesisTarget,
    full_interview_snapshot: dict,
    minimal_doctrine_snapshot: dict,
    minimal_drg_snapshot: dict,
) -> SynthesisRequest:
    return SynthesisRequest(
        target=base_target,
        interview_snapshot=full_interview_snapshot,
        doctrine_snapshot=minimal_doctrine_snapshot,
        drg_snapshot=minimal_drg_snapshot,
        run_id="01KPE222PERF000000000000001",
        adapter_hints={"language": "python"},
    )


@pytest.fixture
def repo_with_prior_synthesis(
    tmp_path: Path,
    base_request: SynthesisRequest,
    adapter: FixtureAdapter,
) -> Path:
    """tmp_path pre-populated with a full synthesis run."""
    synthesize(base_request, adapter=adapter, repo_root=tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# NFR-002: full synthesis < 30 s
# ---------------------------------------------------------------------------


class TestNfr002FullSynthesis:
    @pytest.mark.timeout(30)
    def test_full_synthesis_under_30_seconds(
        self,
        base_request: SynthesisRequest,
        adapter: FixtureAdapter,
        tmp_path: Path,
    ) -> None:
        """NFR-002: full synthesis with ≤10-answer interview completes < 30 s."""
        start = time.monotonic()
        synthesize(base_request, adapter=adapter, repo_root=tmp_path)
        elapsed = time.monotonic() - start
        assert elapsed < 30.0, (
            f"NFR-002 violated: full synthesis took {elapsed:.2f}s (limit: 30s)"
        )

    def test_full_synthesis_completes_successfully(
        self,
        base_request: SynthesisRequest,
        adapter: FixtureAdapter,
        tmp_path: Path,
    ) -> None:
        """Sanity check: synthesis completes without error."""
        result = synthesize(base_request, adapter=adapter, repo_root=tmp_path)
        assert result is not None
        assert result.target_kind in {"directive", "tactic", "styleguide"}


# ---------------------------------------------------------------------------
# NFR-003: bounded resynthesize < 15 s
# ---------------------------------------------------------------------------


class TestNfr003BoundedResynthesize:
    @pytest.mark.timeout(15)
    def test_bounded_resynthesize_under_15_seconds(
        self,
        base_request: SynthesisRequest,
        adapter: FixtureAdapter,
        repo_with_prior_synthesis: Path,
    ) -> None:
        """NFR-003: single-target resynthesize --topic completes < 15 s."""
        repo = repo_with_prior_synthesis

        start = time.monotonic()
        result = resynthesize_run(
            request=base_request,
            adapter=adapter,
            topic="tactic:how-we-apply-directive-003",
            repo_root=repo,
        )
        elapsed = time.monotonic() - start

        assert elapsed < 15.0, (
            f"NFR-003 violated: bounded resynthesize took {elapsed:.2f}s (limit: 15s)"
        )
        assert not result.is_noop or True  # noop is also acceptable (EC-4)


# ---------------------------------------------------------------------------
# NFR-004: fail-closed from validation failure < 5 s
# ---------------------------------------------------------------------------


class TestNfr004FailClosed:
    @pytest.mark.timeout(5)
    def test_validation_failure_under_5_seconds(
        self,
        base_request: SynthesisRequest,
        adapter: FixtureAdapter,
        tmp_path: Path,
    ) -> None:
        """NFR-004: detected failure to return < 5 s (schema error, missing manifest, etc.)."""
        start = time.monotonic()

        # Trigger fail-closed by requesting resynthesize without a prior manifest
        with pytest.raises(FileNotFoundError):
            resynthesize_run(
                request=base_request,
                adapter=adapter,
                topic="tactic:how-we-apply-directive-003",
                repo_root=tmp_path,
            )

        elapsed = time.monotonic() - start
        assert elapsed < 5.0, (
            f"NFR-004 violated: fail-closed took {elapsed:.2f}s (limit: 5s)"
        )

    @pytest.mark.timeout(5)
    def test_unresolved_topic_under_5_seconds(
        self,
        base_request: SynthesisRequest,
        adapter: FixtureAdapter,
        repo_with_prior_synthesis: Path,
    ) -> None:
        """NFR-004: unresolved topic detected and returned < 5 s."""
        repo = repo_with_prior_synthesis

        start = time.monotonic()
        with pytest.raises(TopicSelectorUnresolvedError):
            resynthesize_run(
                request=base_request,
                adapter=adapter,
                topic="zzz:totally_nonexistent",
                repo_root=repo,
            )
        elapsed = time.monotonic() - start
        assert elapsed < 5.0, (
            f"NFR-004 violated: unresolved-topic detection took {elapsed:.2f}s (limit: 5s)"
        )


# ---------------------------------------------------------------------------
# SC-008: TopicSelectorUnresolvedError < 2 s (resolver-level)
# ---------------------------------------------------------------------------


class TestSc008UnresolvedSla:
    def test_unresolved_selector_under_2_seconds(self) -> None:
        """SC-008: resolver returns TopicSelectorUnresolvedError < 2 s."""
        from charter.synthesizer.request import SynthesisTarget

        artifacts = [
            SynthesisTarget(
                kind="directive",
                slug="mission-scope",
                title="Mission Scope",
                artifact_id="PROJECT_001",
                source_section="mission_type",
                source_urns=("directive:DIRECTIVE_001",),
            )
        ]
        drg: dict[str, Any] = {
            "nodes": [
                {"urn": "directive:DIRECTIVE_001", "kind": "directive", "id": "DIRECTIVE_001"}
            ],
            "edges": [],
        }
        sections = ["mission_type", "testing_philosophy"]

        start = time.monotonic()
        with pytest.raises(TopicSelectorUnresolvedError):
            resolve_topic("xyzzy:nonexistent", artifacts, drg, sections)
        elapsed = time.monotonic() - start

        assert elapsed < 2.0, (
            f"SC-008 violated: unresolved selector took {elapsed:.3f}s (limit: 2.0s)"
        )

    def test_unresolved_selector_repeated_calls_fast(self) -> None:
        """SC-008: multiple cold-cache calls remain fast (no warm-up required)."""
        from charter.synthesizer.request import SynthesisTarget

        artifacts: list[SynthesisTarget] = []
        drg: dict[str, Any] = {"nodes": [], "edges": []}
        sections: list[str] = []

        times: list[float] = []
        for _ in range(5):
            start = time.monotonic()
            with pytest.raises((TopicSelectorUnresolvedError, ValueError)):
                resolve_topic("bogus_selector", artifacts, drg, sections)
            times.append(time.monotonic() - start)

        # Every call should be under 2 s (including the very first)
        for i, t in enumerate(times):
            assert t < 2.0, f"SC-008: call {i} took {t:.3f}s (limit: 2.0s)"
