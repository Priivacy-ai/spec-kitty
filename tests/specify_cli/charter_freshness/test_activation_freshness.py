"""End-to-end acceptance for directive-activation freshness (WP03 / T005).

Mission ``bundle-freshness-hash-input-and-activation-01KXR0M1`` — proves the
operator-facing ``charter status`` surface (``compute_freshness(repo)
.synthesized_drg.state`` / ``.remediation``, the API the landed ``13caf4ca8``
test uses) against every US1/US2 acceptance scenario:

- **US1 (#2758)**: a missing/pruned ``references.yaml`` at a non-``built_in_only``
  synthesized state must NOT make ``synthesized_drg`` stale, and ``synthesize``
  must persist a real (non-``None``) hash — no unrecoverable permanent stale.
- **US2 (#2759)**: activating/deactivating a **directive** that changes the
  resolved set flips to ``stale``; activating a **paradigm** or **tactic** (a
  real ``config.yaml`` byte-change that does NOT vary ``graph.yaml``) stays
  ``fresh`` (the false-stale boundary guard); a no-op leaves the state unchanged;
  a drifted stem yields a recoverable ``stale`` without crashing, and the
  ``synthesize`` request path surfaces the actionable resolution error (FR-005);
  ``synthesize`` recovers to ``fresh`` (FR-006).

Activation ids are derived FROM the resolver (``resolve_synthesis_graph_directives``)
— never hardcoded ``default.yaml`` content. ``charter activate``/``deactivate``
write only ``config.yaml`` (spec §Grounded facts), so the tests drive activation
by writing ``config.yaml`` directly.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from charter.bundle import compute_bundle_content_hash
from charter.compiler import (
    resolve_config_activated_roots,
    resolve_synthesis_graph_directives,
)
from charter.hasher import hash_content
from charter.interview import default_interview, write_interview_answers
from charter.kind_vocabulary import UnknownArtifactIdError
from charter.synthesizer import FixtureAdapter, SynthesisRequest, SynthesisTarget, synthesize
from charter.synthesizer.manifest import MANIFEST_PATH, load_yaml as load_manifest
from specify_cli.charter_runtime.freshness import FreshnessSubState, compute_freshness

pytestmark = [pytest.mark.integration]


# Real doctrine stems (present in the built-in catalog); the resolver maps them
# to canonical ids — this module never asserts on the mapped ids directly.
_DIR_A = "010-specification-fidelity-requirement"
_DIR_B = "024-locality-of-change"
_PARADIGM = "domain-driven-design"
_TACTIC = "acceptance-test-first"

_SYNTH_FIXTURE_ROOT = Path(__file__).resolve().parent.parent.parent / "charter" / "fixtures" / "synthesizer"


# --------------------------------------------------------------------------- #
# Seeding helpers (duplicated from test_computer.py by convention — WP03 must
# not edit that WP02-owned file; cross-test-module imports are avoided).
# --------------------------------------------------------------------------- #


def _seed_charter(repo: Path, body: str = "# Charter\n\nHello") -> tuple[Path, Path]:
    charter_dir = repo / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    charter_path = charter_dir / "charter.md"
    metadata_path = charter_dir / "metadata.yaml"
    charter_path.write_text(body, encoding="utf-8")
    return charter_path, metadata_path


def _write_metadata(metadata_path: Path, charter_path: Path) -> None:
    digest = hash_content(charter_path.read_text(encoding="utf-8")).split(":", 1)[1]
    metadata_path.write_text(
        dedent(
            f"""\
            charter_hash: sha256:{digest}
            timestamp_utc: 2026-01-01T00:00:00+00:00
            """
        ),
        encoding="utf-8",
    )


def _seed_triad(repo: Path) -> None:
    """Seed the governance/directives half of the content-hash triad (metadata
    is written by ``_write_metadata`` with a charter-matching hash)."""
    charter_dir = repo / ".kittify" / "charter"
    for name in ("governance.yaml", "directives.yaml"):
        (charter_dir / name).write_text("schema_version: '1'\n", encoding="utf-8")


def _seed_references(repo: Path) -> None:
    (repo / ".kittify" / "charter" / "references.yaml").write_text("schema_version: '1'\n", encoding="utf-8")


def _seed_graph(repo: Path) -> Path:
    graph_path = repo / ".kittify" / "doctrine" / "graph.yaml"
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    graph_path.write_text("schema_version: '1.0'\nnodes: []\nedges: []\n", encoding="utf-8")
    return graph_path


def _seed_manifest(repo: Path, *, built_in_only: bool, bundle_content_hash: str | None) -> Path:
    manifest_path = repo / ".kittify" / "charter" / "synthesis-manifest.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    schema_version = "3" if bundle_content_hash is not None else "2"
    hash_line = (
        f"bundle_content_hash: {bundle_content_hash}\n"
        if bundle_content_hash is not None
        else "bundle_content_hash: null\n"
    )
    manifest_path.write_text(
        dedent(
            f"""\
            schema_version: '{schema_version}'
            mission_id: null
            created_at: '2026-01-01T00:00:00+00:00'
            run_id: 01JTESTRUNIDXXXXXXXXXXXXXX
            adapter_id: test
            adapter_version: '0.0.0'
            synthesizer_version: '0.0.0'
            manifest_hash: {"a" * 64}
            artifacts: []
            built_in_only: {str(built_in_only).lower()}
            """
        )
        + hash_line,
        encoding="utf-8",
    )
    return manifest_path


def _write_config(
    repo: Path,
    *,
    directives: list[str] | None = None,
    paradigms: list[str] | None = None,
    tactics: list[str] | None = None,
) -> Path:
    """Write ``.kittify/config.yaml`` — the sole activation source.

    A key left as ``None`` is OMITTED (absent → three-state ``None``); an empty
    list emits an explicit flow-style ``[]`` (present-but-empty).
    """
    lines: list[str] = []
    for key, vals in (
        ("activated_directives", directives),
        ("activated_paradigms", paradigms),
        ("activated_tactics", tactics),
    ):
        if vals is not None:
            lines.append(f"{key}: [{', '.join(vals)}]")
    config_path = repo / ".kittify" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return config_path


def _seed_non_built_in_graph_state(repo: Path) -> None:
    """Seed a fully-fresh, non-``built_in_only`` synthesized state EXCEPT the
    manifest hash — call ``_stamp_fresh`` after configuring activation."""
    charter_path, metadata_path = _seed_charter(repo)
    _write_metadata(metadata_path, charter_path)
    _seed_triad(repo)
    _seed_graph(repo)


def _stamp_fresh(repo: Path) -> str:
    """Stamp the manifest with the CURRENT content hash → a ``fresh`` baseline
    (what ``charter synthesize`` persists), and return that hash."""
    # Explicit annotation: ``charter.*`` is ``follow_imports=skip``'d, collapsing
    # compute_bundle_content_hash's ``str | None`` return to ``Any`` at this call
    # site — annotate to recover the real type without a suppression.
    current: str | None = compute_bundle_content_hash(repo)
    assert current is not None, "triad + resolvable directives must yield a real hash"
    _seed_manifest(repo, built_in_only=False, bundle_content_hash=current)
    return current


def _synth_adapter() -> FixtureAdapter:
    return FixtureAdapter(fixture_root=_SYNTH_FIXTURE_ROOT)


def _seed_pipeline_bundle_files(repo: Path) -> None:
    """Seed charter.md + a charter-matching metadata.yaml + the governance/
    directives files ahead of a real ``synthesize`` run (references.yaml is
    deliberately NOT seeded — it is out of the content-hash set post-#2758)."""
    charter_path, metadata_path = _seed_charter(repo)
    _write_metadata(metadata_path, charter_path)
    _seed_triad(repo)


def _base_synthesis_request(run_id: str) -> SynthesisRequest:
    target = SynthesisTarget(
        kind="directive",
        slug="mission-type-scope-directive",
        title="Mission Type Scope Directive",
        artifact_id="PROJECT_001",
        source_section="mission_type",
    )
    return SynthesisRequest(
        target=target,
        interview_snapshot={
            "mission_type": "software_dev",
            "language_scope": ["python"],
            "testing_philosophy": "test-driven development with high coverage",
            "neutrality_posture": "balanced",
            "selected_directives": ["DIRECTIVE_003"],
            "risk_appetite": "moderate",
        },
        doctrine_snapshot={
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
        drg_snapshot={
            "nodes": [
                {"urn": "directive:DIRECTIVE_003", "kind": "directive", "id": "DIRECTIVE_003"},
            ],
            "edges": [],
            "schema_version": "1",
        },
        run_id=run_id,
        adapter_hints={"language": "python"},
    )


def _assert_state_remediation_consistent(sub: FreshnessSubState) -> None:
    """FR-005: state ⇔ remediation are internally consistent — a passing state
    advertises no remediation; a non-passing state advertises a resolving one."""
    if sub.state in ("fresh", "built_in_only"):
        assert sub.remediation is None, f"{sub.state} must not advertise a remediation"
    else:
        assert sub.remediation, f"{sub.state} must advertise a resolving remediation"


# --------------------------------------------------------------------------- #
# US1 — missing references.yaml must not cause permanent stale (#2758)
# --------------------------------------------------------------------------- #


def test_us1_references_absent_is_not_stale_and_synthesize_persists_real_hash() -> None:
    """US1 AC-1/AC-2: at a non-``built_in_only`` graph with ``references.yaml``
    absent, ``synthesized_drg`` is NOT stale, state+remediation are consistent,
    and ``charter synthesize`` persists a real (non-``None``) hash (FR-006)."""
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        repo = Path(d)
        _seed_pipeline_bundle_files(repo)  # no references.yaml, no config → directives []
        assert not (repo / ".kittify" / "charter" / "references.yaml").exists()

        synthesize(_base_synthesis_request("01AAAAAAAAAAAAAAAAAAAAAAAA"), adapter=_synth_adapter(), repo_root=repo)

        drg = compute_freshness(repo).synthesized_drg
        assert drg.state == "fresh"  # not stale on account of the missing references.yaml
        _assert_state_remediation_consistent(drg)

        # No permanent-``None`` re-store: synthesize baked a real hash.
        manifest = load_manifest(repo / MANIFEST_PATH)
        assert manifest.bundle_content_hash is not None
        assert manifest.bundle_content_hash == compute_bundle_content_hash(repo)


# --------------------------------------------------------------------------- #
# US2 — directive activation visibility (#2759)
# --------------------------------------------------------------------------- #


def test_us2_activate_directive_that_changes_resolved_set_goes_stale(tmp_path: Path) -> None:
    """US2 AC-1 / SC-002: activating a directive that changes the resolved set
    flips ``synthesized_drg`` to ``stale`` with a resolving remediation."""
    _seed_non_built_in_graph_state(tmp_path)
    _write_config(tmp_path, directives=[_DIR_A])
    _stamp_fresh(tmp_path)
    assert compute_freshness(tmp_path).synthesized_drg.state == "fresh"

    before = resolve_synthesis_graph_directives(tmp_path)
    _write_config(tmp_path, directives=[_DIR_A, _DIR_B])
    after = resolve_synthesis_graph_directives(tmp_path)
    assert before != after  # resolver-derived: the set genuinely changed

    drg = compute_freshness(tmp_path).synthesized_drg
    assert drg.state == "stale"
    assert drg.remediation == "spec-kitty charter synthesize"
    _assert_state_remediation_consistent(drg)


def test_us2_deactivate_directive_goes_stale(tmp_path: Path) -> None:
    """US2 AC-2 / SC-002: deactivating a previously-active directive → ``stale``."""
    _seed_non_built_in_graph_state(tmp_path)
    _write_config(tmp_path, directives=[_DIR_A, _DIR_B])
    _stamp_fresh(tmp_path)
    assert compute_freshness(tmp_path).synthesized_drg.state == "fresh"

    before = resolve_synthesis_graph_directives(tmp_path)
    _write_config(tmp_path, directives=[_DIR_A])
    after = resolve_synthesis_graph_directives(tmp_path)
    assert before != after

    assert compute_freshness(tmp_path).synthesized_drg.state == "stale"


def test_us2_paradigm_and_tactic_activation_stays_fresh(tmp_path: Path) -> None:
    """US2 AC-3 / SC-002 boundary guard: activating a **paradigm** AND a
    **tactic** (a real ``config.yaml`` byte-change) does NOT vary ``graph.yaml``,
    so ``synthesized_drg`` MUST stay ``fresh`` — proving non-graph kinds are not
    false-stale."""
    _seed_non_built_in_graph_state(tmp_path)
    _write_config(tmp_path, directives=[_DIR_A])
    _stamp_fresh(tmp_path)
    assert compute_freshness(tmp_path).synthesized_drg.state == "fresh"

    before = resolve_synthesis_graph_directives(tmp_path)
    _write_config(tmp_path, directives=[_DIR_A], paradigms=[_PARADIGM], tactics=[_TACTIC])
    after = resolve_synthesis_graph_directives(tmp_path)
    assert before == after  # resolver-derived: the DIRECTIVE set is unchanged

    # The bundle content hash is likewise unchanged (paradigm/tactic are inert).
    assert compute_freshness(tmp_path).synthesized_drg.state == "fresh"


def test_us2_noop_reactivation_leaves_state_unchanged(tmp_path: Path) -> None:
    """US2 AC-4 / SC-003: re-activating an already-resolved directive id (no
    change to the resolved set) produces zero freshness-state change."""
    _seed_non_built_in_graph_state(tmp_path)
    _write_config(tmp_path, directives=[_DIR_A])
    _stamp_fresh(tmp_path)
    assert compute_freshness(tmp_path).synthesized_drg.state == "fresh"

    before = resolve_synthesis_graph_directives(tmp_path)
    _write_config(tmp_path, directives=[_DIR_A])  # re-activate the same id
    after = resolve_synthesis_graph_directives(tmp_path)
    assert before == after

    assert compute_freshness(tmp_path).synthesized_drg.state == "fresh"


def test_us2_drifted_stem_is_recoverable_stale_and_synthesize_surfaces_error(tmp_path: Path) -> None:
    """US2 AC-6 / FR-005 / NFR-003: a ``config.yaml`` whose activated directive
    stem no longer resolves yields a recoverable ``stale`` — ``charter status``
    does NOT crash — and the ``synthesize`` request path surfaces the actionable
    ``UnknownArtifactIdError`` rather than silently re-storing ``None``."""
    from specify_cli.cli.commands.charter._synthesis import _build_synthesis_request

    _seed_non_built_in_graph_state(tmp_path)
    _write_config(tmp_path, directives=[_DIR_A])
    _stamp_fresh(tmp_path)
    assert compute_freshness(tmp_path).synthesized_drg.state == "fresh"

    # Drift: an activated directive stem that no longer resolves in the catalog.
    _write_config(tmp_path, directives=["999-does-not-exist"])

    # The resolver genuinely raises on this stem (the drift path under test)...
    with pytest.raises(UnknownArtifactIdError):
        resolve_config_activated_roots(repo_root=tmp_path)
    # ...the hash helper swallows it → None...
    assert compute_bundle_content_hash(tmp_path) is None
    # ...and ``charter status`` reports a recoverable stale WITHOUT crashing.
    drg = compute_freshness(tmp_path).synthesized_drg
    assert drg.state == "stale"
    assert drg.remediation == "spec-kitty charter synthesize"

    # FR-005: the ``charter synthesize`` request build surfaces the actionable
    # resolution error (it derives graph activation from the same resolver).
    answers_path = tmp_path / ".kittify" / "charter" / "interview" / "answers.yaml"
    write_interview_answers(answers_path, default_interview(mission="software-dev", profile="minimal"))
    with pytest.raises(UnknownArtifactIdError):
        _build_synthesis_request(tmp_path, "fixture")


def test_us2_activation_recovers_to_fresh_after_synthesize(tmp_path: Path) -> None:
    """US2 AC-5 / FR-006 / SC-002: directive activation → ``stale`` → ``charter
    synthesize`` → ``fresh`` (via the REAL synthesize pipeline)."""
    _seed_pipeline_bundle_files(tmp_path)
    _write_config(tmp_path, directives=[_DIR_A])
    adapter = _synth_adapter()

    synthesize(_base_synthesis_request("01BBBBBBBBBBBBBBBBBBBBBBBB"), adapter=adapter, repo_root=tmp_path)
    assert compute_freshness(tmp_path).synthesized_drg.state == "fresh"

    _write_config(tmp_path, directives=[_DIR_A, _DIR_B])
    assert compute_freshness(tmp_path).synthesized_drg.state == "stale"

    synthesize(_base_synthesis_request("01CCCCCCCCCCCCCCCCCCCCCCCC"), adapter=adapter, repo_root=tmp_path)
    assert compute_freshness(tmp_path).synthesized_drg.state == "fresh"
