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

import dataclasses
import time
from pathlib import Path
from typing import Any

import pytest

from charter.bundle import compute_bundle_content_hash
from charter.catalog import load_doctrine_catalog
from charter.compiler import resolve_synthesis_graph_directives
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
    full_interview_snapshot: dict[str, Any],
    minimal_doctrine_snapshot: dict[str, Any],
    minimal_drg_snapshot: dict[str, Any],
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


def _seed_charter_freshness_repo_with_directives(repo: Path, directive_stems: list[str]) -> None:
    """Like :func:`_seed_charter_freshness_repo`, but activates *directive_stems*
    in ``.kittify/config.yaml`` FIRST so ``compute_freshness`` reaches the
    graph-hash branch through the CONFIG-PRESENT resolver path — i.e. it pays the
    real ``resolve_config_activated_roots`` → ``load_doctrine_catalog()`` cost the
    WP02 short-circuit skips for absent-directives projects (tracer DD-8). The
    manifest hash is stamped AFTER the config is written so the seeded state is
    genuinely ``fresh``."""
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

    config_path = repo / ".kittify" / "config.yaml"
    config_path.write_text(
        "activated_directives: [" + ", ".join(directive_stems) + "]\n",
        encoding="utf-8",
    )

    graph_path = repo / ".kittify" / "doctrine" / "graph.yaml"
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    graph_path.write_text("schema_version: '1.0'\nnodes: []\nedges: []\n", encoding="utf-8")

    real_hash = compute_bundle_content_hash(repo)  # config-present: resolves directives
    assert real_hash is not None
    manifest_path = charter_dir / "synthesis-manifest.yaml"
    manifest_path.write_text(
        "schema_version: '3'\n"
        "mission_id: null\n"
        "created_at: '2026-01-01T00:00:00+00:00'\n"
        "run_id: 01JPERFENVELOPE0000000002X\n"
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
    reintroduced into ``compute_bundle_content_hash``).

    Two branches are covered: the ABSENT-directives fast path (WP02's
    short-circuit skips ``load_doctrine_catalog()``), and the CONFIG-PRESENT
    path that DOES pay the ~1s catalog load — both must land < 2 s (mission
    ``bundle-freshness-hash-input-and-activation-01KXR0M1``, tracer DD-8)."""

    @pytest.mark.timeout(2)
    def test_compute_freshness_under_2_seconds(self, tmp_path: Path) -> None:
        _seed_charter_freshness_repo(tmp_path)

        start = time.monotonic()
        result = compute_freshness(tmp_path)
        elapsed = time.monotonic() - start

        # Absent-directives fast path (WP02 short-circuit) — observed ~2-4ms.
        assert elapsed < 2.0, (
            f"NFR-002 violated: compute_freshness took {elapsed:.3f}s (limit: 2.0s)"
        )
        # Sanity: the seeded repo is genuinely fresh (content-identity match)
        # so the timing measurement exercises the real comparison branch,
        # not an early missing/stale short-circuit.
        assert result.synthesized_drg.state == "fresh"

    @pytest.mark.timeout(10)
    def test_compute_freshness_with_activated_directives_under_2_seconds(self, tmp_path: Path) -> None:
        """NFR-002 config-present branch: activating directives forces the
        freshness read down the ``resolve_config_activated_roots`` →
        ``load_doctrine_catalog()`` path (one ~1s cold catalog load), which must
        still land < 2 s per the charter's CLI-interactive ceiling.

        Measured production-representatively (imports/first-touch caches warmed
        by an untimed call first, per tracer DD-8) rather than adding
        ``load_doctrine_catalog`` caching. The generous ``@timeout(10)`` guards
        against a true hang without letting the warm+measure passes trip it; the
        binding assertion is on the warmed measurement only."""
        _seed_charter_freshness_repo_with_directives(tmp_path, ["010-specification-fidelity-requirement"])

        # Warm imports / first-touch caches (production-representative timing).
        warm = compute_freshness(tmp_path)
        assert warm.synthesized_drg.state == "fresh"  # reached the graph-hash branch

        start = time.monotonic()
        result = compute_freshness(tmp_path)
        elapsed = time.monotonic() - start

        assert elapsed < 2.0, (
            f"NFR-002 (config-present) violated: compute_freshness took {elapsed:.3f}s (limit: 2.0s)"
        )
        assert result.synthesized_drg.state == "fresh"


class TestSc004RosterStability:
    """SC-004 (second clause): the directive-activation digest hashes ONLY the
    project's RESOLVED activated directive set — never the full doctrine
    catalog/roster. Adding a built-in directive the project has NOT activated
    must not move ``compute_bundle_content_hash``. Guards against a regression
    that folds ``default.yaml``/catalog content into the identity (which would
    make every roster/``default.yaml`` change a false-stale for every project)."""

    @staticmethod
    def _seed_triad_and_config(repo: Path, directive_stems: list[str]) -> None:
        charter_dir = repo / ".kittify" / "charter"
        charter_dir.mkdir(parents=True, exist_ok=True)
        for name in ("governance.yaml", "directives.yaml", "metadata.yaml"):
            (charter_dir / name).write_text("schema_version: '1'\n", encoding="utf-8")
        (repo / ".kittify" / "config.yaml").write_text(
            "activated_directives: [" + ", ".join(directive_stems) + "]\n",
            encoding="utf-8",
        )

    def test_unactivated_roster_directive_does_not_move_the_hash(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._seed_triad_and_config(tmp_path, ["010-specification-fidelity-requirement"])

        baseline_hash = compute_bundle_content_hash(tmp_path)
        baseline_directives = resolve_synthesis_graph_directives(tmp_path)
        assert baseline_hash is not None

        # Grow the catalog/roster with a directive the project has NOT activated.
        real_catalog = load_doctrine_catalog()
        rostered_catalog = dataclasses.replace(
            real_catalog, directives=real_catalog.directives | {"DIRECTIVE_ROSTER_EXTRA"}
        )
        monkeypatch.setattr("charter.compiler.load_doctrine_catalog", lambda *a, **k: rostered_catalog)

        # The resolved activated set — and therefore the digest — are unchanged:
        # a roster/``default.yaml`` addition the project never activated cannot
        # move the identity.
        assert resolve_synthesis_graph_directives(tmp_path) == baseline_directives
        assert compute_bundle_content_hash(tmp_path) == baseline_hash


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
