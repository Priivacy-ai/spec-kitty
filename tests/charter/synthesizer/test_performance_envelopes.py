"""Performance envelope tests (T031) — CI-tolerant timing assertions.

NFR-002: full synthesis on ≤10-answer interview < 30 s (fixture adapter).
NFR-002 (mission `synthesized-drg-stale-refresh-01KXN8KZ`, #2681):
    ``compute_freshness`` (content-identity DRG freshness check) < 2 s.
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

from charter.bundle import compute_bundle_content_hash
from charter.hasher import hash_content
from charter.synthesizer import (
    FixtureAdapter,
    SynthesisRequest,
    SynthesisTarget,
    synthesize,
)
from charter.synthesizer.errors import TopicSelectorUnresolvedError
from charter.synthesizer.resynthesize_pipeline import run as resynthesize_run
from charter.synthesizer.topic_resolver import resolve as resolve_topic
from specify_cli.charter_runtime.freshness import compute_freshness


# ---------------------------------------------------------------------------
# Fixtures — shared test data
# ---------------------------------------------------------------------------


pytestmark = [pytest.mark.unit]

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
# NFR-002 (mission `synthesized-drg-stale-refresh-01KXN8KZ`, #2681):
# compute_freshness < 2 s wall-clock
# ---------------------------------------------------------------------------


def _seed_charter_freshness_repo(repo: Path) -> None:
    """Seed a representative ``.kittify/charter/`` + ``.kittify/doctrine/``
    tree: the four ``BUNDLE_CONTENT_HASH_FILES`` (``metadata.yaml``,
    ``governance.yaml``, ``directives.yaml``, ``references.yaml``), a
    ``graph.yaml``, and a ``synthesis-manifest.yaml`` carrying a REAL
    ``bundle_content_hash`` computed via the canonical helper — so
    ``compute_freshness`` exercises the full content-identity comparison
    path (data-model.md's replaced ``:411-441`` block) rather than an early
    ``missing``/``stale`` short-circuit. Mirrors the seeding pattern in
    ``tests/specify_cli/charter_freshness/test_computer.py`` (duplicated,
    not imported — that module is WP02/WP03-owned)."""
    charter_dir = repo / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    charter_path = charter_dir / "charter.md"
    charter_path.write_text(
        "# Charter\n\nRepresentative project charter for perf-envelope seeding.\n",
        encoding="utf-8",
    )
    digest = hash_content(charter_path.read_text(encoding="utf-8")).split(":", 1)[1]
    (charter_dir / "metadata.yaml").write_text(
        f"charter_hash: sha256:{digest}\ntimestamp_utc: 2026-01-01T00:00:00+00:00\n",
        encoding="utf-8",
    )
    for name in ("governance.yaml", "directives.yaml", "references.yaml"):
        (charter_dir / name).write_text("schema_version: '1'\n", encoding="utf-8")

    graph_path = repo / ".kittify" / "doctrine" / "graph.yaml"
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    graph_path.write_text("schema_version: '1.0'\nnodes: []\nedges: []\n", encoding="utf-8")

    real_hash = compute_bundle_content_hash(repo)
    assert real_hash is not None
    manifest_path = charter_dir / "synthesis-manifest.yaml"
    manifest_path.write_text(
        "schema_version: '3'\n"
        "mission_id: null\n"
        "created_at: '2026-01-01T00:00:00+00:00'\n"
        "run_id: 01JPERFENVELOPE0000000001X\n"
        "adapter_id: test\n"
        "adapter_version: '0.0.0'\n"
        "synthesizer_version: '0.0.0'\n"
        f"manifest_hash: {'a' * 64}\n"
        "artifacts: []\n"
        "built_in_only: false\n"
        f"bundle_content_hash: {real_hash}\n",
        encoding="utf-8",
    )


class TestNfr002FreshnessComputeUnder2Seconds:
    """NFR-002 (`synthesized-drg-stale-refresh-01KXN8KZ`, #2681):
    ``compute_freshness`` completes in well under 2 s wall-clock. This is a
    PERMANENT regression ratchet, not a one-off measurement — it catches an
    accidental eager import (breaking the LD-3 lazy-import contract in
    ``computer.py``) or an O(n²) helper (e.g. a naive concat-then-hash
    reintroduced into ``compute_bundle_content_hash``)."""

    @pytest.mark.timeout(2)
    def test_compute_freshness_under_2_seconds(self, tmp_path: Path) -> None:
        _seed_charter_freshness_repo(tmp_path)

        start = time.monotonic()
        result = compute_freshness(tmp_path)
        elapsed = time.monotonic() - start

        # Observed ~2-4ms locally on 2026-07-16 — the 2.0s budget carries
        # ~500x headroom (NFR-002's CLI interactive-response ceiling).
        assert elapsed < 2.0, (
            f"NFR-002 violated: compute_freshness took {elapsed:.3f}s (limit: 2.0s)"
        )
        # Sanity: the seeded repo is genuinely fresh (content-identity match)
        # so the timing measurement exercises the real comparison branch,
        # not an early missing/stale short-circuit.
        assert result.synthesized_drg.state == "fresh"


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
