"""Unit tests for ``specify_cli.charter_runtime.freshness.computer`` (WP02 / FR-005, FR-009).

Covers each documented sub-state:

* ``fresh`` — when SHA-256 of charter.md matches metadata + bundle/DRG mtimes
  are downstream of the charter source.
* ``stale`` — when charter content has drifted from the stored hash, or
  bundle/DRG files are older than their upstream change.
* ``missing`` — when the synthesized DRG file is absent and the manifest
  does not opt into ``built_in_only=true``.
* ``built_in_only`` — when the manifest declares ``built_in_only: true``.
  A residual ``graph.yaml`` the manifest disowns is *stale graph residue*
  (FR-006 / C2-f): still ``built_in_only`` + a non-blocking diagnostic, never
  the formerly-terminal ``invalid`` state.
* ``invalid`` — a genuine inconsistency from ``_compute_charter_source``:
  ``charter.md`` exists but cannot be hashed. (No ``synthesized_drg`` producer
  returns ``invalid`` after FR-006.)
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from textwrap import dedent

import pytest

from specify_cli.charter_runtime.freshness import (
    CharterFreshness,
    FreshnessSubState,
    compute_freshness,
)
from charter.bundle import BUNDLE_CONTENT_HASH_FILES, compute_bundle_content_hash
from charter.hasher import hash_content
from charter.synthesizer import (
    FixtureAdapter,
    SynthesisRequest,
    SynthesisTarget,
    synthesize,
)
from charter.synthesizer.resynthesize_pipeline import run as resynthesize_run


pytestmark = [pytest.mark.fast]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_charter(repo: Path, body: str = "# Charter\n\nHello") -> tuple[Path, Path]:
    charter_dir = repo / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    charter_path = charter_dir / "charter.md"
    metadata_path = charter_dir / "metadata.yaml"
    charter_path.write_text(body, encoding="utf-8")
    return charter_path, metadata_path


def _write_metadata(metadata_path: Path, charter_path: Path, *, mismatched: bool = False) -> None:
    digest = hash_content(charter_path.read_text(encoding="utf-8")).split(":", 1)[1]
    if mismatched:
        digest = "0" * 64
    metadata_path.write_text(
        dedent(
            f"""\
            charter_hash: sha256:{digest}
            timestamp_utc: 2026-01-01T00:00:00+00:00
            """
        ),
        encoding="utf-8",
    )


def _seed_bundle_files(repo: Path) -> None:
    charter_dir = repo / ".kittify" / "charter"
    for name in ("governance.yaml", "directives.yaml", "references.yaml"):
        (charter_dir / name).write_text("schema_version: '1'\n", encoding="utf-8")


def _seed_manifest(
    repo: Path,
    *,
    built_in_only: bool,
    created_at: str = "2099-01-01T00:00:00+00:00",
    bundle_content_hash: str | None = None,
) -> Path:
    manifest_path = repo / ".kittify" / "charter" / "synthesis-manifest.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    hash_line = (
        f"bundle_content_hash: {bundle_content_hash}\n"
        if bundle_content_hash is not None
        else "bundle_content_hash: null\n"
    )
    manifest_path.write_text(
        dedent(
            f"""\
            schema_version: '2'
            mission_id: null
            created_at: '{created_at}'
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


def _seed_full_bundle(repo: Path) -> tuple[Path, Path]:
    """Seed charter.md + metadata.yaml + the remaining three bundle files —
    the complete ``BUNDLE_CONTENT_HASH_FILES`` set (fact #20) required for a
    meaningful ``compute_bundle_content_hash`` comparison."""
    charter_path, metadata_path = _seed_charter(repo)
    _write_metadata(metadata_path, charter_path)
    _seed_bundle_files(repo)
    return charter_path, metadata_path


def _seed_graph(repo: Path) -> Path:
    graph_path = repo / ".kittify" / "doctrine" / "graph.yaml"
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    graph_path.write_text("schema_version: '1.0'\nnodes: []\nedges: []\n", encoding="utf-8")
    return graph_path


def _bump_bundle_mtimes_to_future(repo: Path, *, offset_seconds: float = 100.0) -> None:
    """Simulate a git checkout/rebase/clone/machine-migration bumping bundle
    mtimes into the future with NO content change — the exact #2681 symptom.
    A deterministic future offset (rather than relying on real elapsed
    wall-clock time between calls) keeps the reproduction stable regardless
    of how fast the test machine runs."""
    bump = time.time() + offset_seconds
    for name in BUNDLE_CONTENT_HASH_FILES:
        os.utime(repo / ".kittify" / "charter" / name, (bump, bump))


# ---------------------------------------------------------------------------
# Real synthesize/resynthesize pipeline fixtures (AS-5 / SC-003 e2e proofs)
#
# ``synthesize()``/``resynthesize`` do not themselves write
# ``.kittify/charter/{governance,directives,references,metadata}.yaml`` (fact
# #20, ``bundle.py`` provenance — those are ``charter sync``'s output), so
# tests that need a real ``bundle_content_hash`` must seed them directly.
# These fixtures duplicate (rather than import) the pattern used by
# ``tests/charter/synthesizer/test_orchestrator_resynthesize.py`` — WP03 does
# not edit that WP02-owned file.
# ---------------------------------------------------------------------------


_SYNTH_FIXTURE_ROOT = Path(__file__).resolve().parent.parent.parent / "charter" / "fixtures" / "synthesizer"


def _seed_pipeline_bundle_files(repo: Path) -> None:
    """Seed charter.md + the four content-hash bundle files ahead of a real
    pipeline run.

    ``metadata.yaml`` is BOTH one of ``BUNDLE_CONTENT_HASH_FILES`` AND the
    file ``_compute_charter_source`` reads for ``charter_hash`` — it must
    carry a hash that actually matches ``charter.md``, or ``charter_source``
    (and therefore ``synced_bundle``) reads as ``missing``/``stale`` and the
    PRESERVED ``synced_bundle``-precedence branch short-circuits
    ``synthesized_drg`` to ``stale`` before the content-hash comparison this
    fixture exists to exercise ever runs.
    """
    charter_path, metadata_path = _seed_charter(repo)
    _write_metadata(metadata_path, charter_path)
    for name in BUNDLE_CONTENT_HASH_FILES:
        if name == "metadata.yaml":
            continue
        (repo / ".kittify" / "charter" / name).write_text(
            f"# {name} fixture content\n", encoding="utf-8"
        )


def _synth_adapter() -> FixtureAdapter:
    return FixtureAdapter(fixture_root=_SYNTH_FIXTURE_ROOT)


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


# ---------------------------------------------------------------------------
# Fresh / stale / missing / built_in_only / invalid cases
# ---------------------------------------------------------------------------


def test_bundle_file_lists_stay_in_sync() -> None:
    """The reader's ``_BUNDLE_FILES`` must equal the canonical bundle hash set.

    ``charter.bundle.BUNDLE_CONTENT_HASH_FILES`` (the content-identity input
    set, drives the ``synthesized_drg`` hash) and
    ``computer._BUNDLE_FILES`` (drives ``synced_bundle`` existence + mtime) are
    deliberately duplicated 4-tuples in different modules to keep the
    ``charter``→``specify_cli`` dependency direction intact (data-model
    Decision 5). This pins them equal so a future edit to one that silently
    drifts from the other — which would let the two freshness sub-states track
    different file sets — is caught, honoring the single-canonical-authority
    principle without inverting the import direction.
    """
    from specify_cli.charter_runtime.freshness.computer import _BUNDLE_FILES

    assert tuple(_BUNDLE_FILES) == tuple(BUNDLE_CONTENT_HASH_FILES)


def test_returns_three_sub_objects(tmp_path: Path) -> None:
    """The result always exposes all three layers."""
    result = compute_freshness(tmp_path)
    assert isinstance(result, CharterFreshness)
    for sub in (result.charter_source, result.synced_bundle, result.synthesized_drg):
        assert isinstance(sub, FreshnessSubState)
        assert sub.state in {"fresh", "stale", "missing", "built_in_only", "invalid"}


def test_charter_source_missing_when_charter_md_absent(tmp_path: Path) -> None:
    result = compute_freshness(tmp_path)
    assert result.charter_source.state == "missing"
    assert result.charter_source.remediation == "spec-kitty charter sync"


def test_charter_source_fresh_when_hash_matches(tmp_path: Path) -> None:
    charter_path, metadata_path = _seed_charter(tmp_path)
    _write_metadata(metadata_path, charter_path)
    result = compute_freshness(tmp_path)
    assert result.charter_source.state == "fresh"
    assert result.charter_source.last_change is not None


def test_charter_source_stale_when_hash_mismatches(tmp_path: Path) -> None:
    charter_path, metadata_path = _seed_charter(tmp_path)
    _write_metadata(metadata_path, charter_path, mismatched=True)
    result = compute_freshness(tmp_path)
    assert result.charter_source.state == "stale"
    assert result.charter_source.remediation == "spec-kitty charter sync"


def test_synced_bundle_missing_when_no_bundle_files(tmp_path: Path) -> None:
    _, _ = _seed_charter(tmp_path)
    result = compute_freshness(tmp_path)
    # Metadata file is one of the bundle files; even though charter.md
    # exists, the rest of the bundle is missing.  We need a true "no files"
    # scenario: drop charter dir except for charter.md.
    bundle = tmp_path / ".kittify" / "charter"
    for stale_file in ("governance.yaml", "directives.yaml", "references.yaml", "metadata.yaml"):
        candidate = bundle / stale_file
        if candidate.exists():
            candidate.unlink()
    result = compute_freshness(tmp_path)
    assert result.synced_bundle.state == "missing"


def test_synced_bundle_fresh_when_bundle_followed_charter(tmp_path: Path) -> None:
    charter_path, metadata_path = _seed_charter(tmp_path)
    # Bundle files written AFTER charter — fresh.
    _write_metadata(metadata_path, charter_path)
    _seed_bundle_files(tmp_path)
    result = compute_freshness(tmp_path)
    assert result.charter_source.state == "fresh"
    assert result.synced_bundle.state == "fresh"


def test_synced_bundle_stale_when_charter_is_newer(tmp_path: Path) -> None:
    charter_path, metadata_path = _seed_charter(tmp_path)
    _write_metadata(metadata_path, charter_path)
    _seed_bundle_files(tmp_path)
    # Re-write charter much later but DO NOT update metadata — that flips
    # charter_source to stale → synced_bundle inherits "stale".
    time.sleep(0.01)
    charter_path.write_text("# Charter (drifted)\n", encoding="utf-8")
    result = compute_freshness(tmp_path)
    assert result.charter_source.state == "stale"
    assert result.synced_bundle.state == "stale"


def test_charter_source_uses_sync_hash_normalization(tmp_path: Path) -> None:
    charter_path, metadata_path = _seed_charter(tmp_path, "# Charter\n\nHello\n\n")
    _write_metadata(metadata_path, charter_path)

    result = compute_freshness(tmp_path)

    assert result.charter_source.state == "fresh"


def test_synced_bundle_fresh_when_matching_hash_but_bundle_mtime_older(tmp_path: Path) -> None:
    charter_path, metadata_path = _seed_charter(tmp_path)
    _write_metadata(metadata_path, charter_path)
    _seed_bundle_files(tmp_path)

    time.sleep(0.01)
    charter_path.write_text("# Charter\n\nHello\n\n", encoding="utf-8")
    result = compute_freshness(tmp_path)

    assert result.charter_source.state == "fresh"
    assert result.synced_bundle.state == "fresh"


def test_synthesized_drg_missing_when_no_graph_no_manifest(tmp_path: Path) -> None:
    """Preserved by the #2681 fix — the ``missing`` branch (no ``graph.yaml``,
    no built-in-only opt-in, no legacy seed marker) sits above the
    content-hash comparison. A regress here means T015 touched a branch it
    should not have."""
    charter_path, metadata_path = _seed_charter(tmp_path)
    _write_metadata(metadata_path, charter_path)
    _seed_bundle_files(tmp_path)
    result = compute_freshness(tmp_path)
    assert result.synthesized_drg.state == "missing"
    assert result.synthesized_drg.remediation == "spec-kitty charter synthesize"


def test_synthesized_drg_built_in_only_when_manifest_declares_it(tmp_path: Path) -> None:
    """Preserved by the #2681 fix (data-model.md): ``built_in_only`` short-
    circuits BEFORE the content-hash comparison. A regress here means T015
    touched a branch it should not have."""
    charter_path, metadata_path = _seed_charter(tmp_path)
    _write_metadata(metadata_path, charter_path)
    _seed_bundle_files(tmp_path)
    _seed_manifest(tmp_path, built_in_only=True)
    result = compute_freshness(tmp_path)
    assert result.synthesized_drg.state == "built_in_only"
    assert result.synthesized_drg.remediation is None


def test_synthesized_drg_built_in_only_for_legacy_fresh_seed(tmp_path: Path) -> None:
    """Preserved by the #2681 fix — the legacy-fresh-seed branch sits above
    the content-hash comparison and is untouched by T015. A regress here
    means T015 touched a branch it should not have."""
    charter_path, metadata_path = _seed_charter(tmp_path)
    _write_metadata(metadata_path, charter_path)
    _seed_bundle_files(tmp_path)
    provenance = tmp_path / ".kittify" / "doctrine" / "PROVENANCE.md"
    provenance.parent.mkdir(parents=True, exist_ok=True)
    provenance.write_text(
        "# Spec Kitty Doctrine — Fresh Project Seed\n\n"
        "No LLM-authored YAML was present; using built-in doctrine.\n",
        encoding="utf-8",
    )

    result = compute_freshness(tmp_path)

    assert result.synthesized_drg.state == "built_in_only"
    assert result.synthesized_drg.remediation is None


def test_synthesized_drg_residue_reports_built_in_only(tmp_path: Path) -> None:
    """FR-006 (C2-f): built_in_only=true ∧ graph.yaml present is read-time residue.

    The manifest is the declared authority (#083): a graph.yaml it disowns is
    residue, NOT a contradiction. The reader reports the authoritative
    ``built_in_only`` state with a non-blocking diagnostic instead of the
    formerly-terminal ``invalid`` state — making the blocking branch
    unreachable for this condition (structural, not reactive).

    Preserved by the #2681 fix — this branch also sits above the
    content-hash comparison. A regress here means T015 touched a branch it
    should not have.
    """
    charter_path, metadata_path = _seed_charter(tmp_path)
    _write_metadata(metadata_path, charter_path)
    _seed_bundle_files(tmp_path)
    _seed_manifest(tmp_path, built_in_only=True)
    _seed_graph(tmp_path)  # residue: built_in_only=true AND graph.yaml present
    result = compute_freshness(tmp_path)
    assert result.synthesized_drg.state == "built_in_only"
    assert result.synthesized_drg.state != "invalid"
    assert result.synthesized_drg.detail is not None
    assert "stale graph residue" in result.synthesized_drg.detail
    # Read-time normalization is NOT a reactive self-heal: no synthesize push.
    assert result.synthesized_drg.remediation is None


def test_synthesized_drg_stale_when_synced_bundle_not_fresh(tmp_path: Path) -> None:
    """Preserved precedence branch (data-model.md): an upstream-stale
    ``synced_bundle`` short-circuits ``synthesized_drg`` to ``stale`` BEFORE
    any content-hash comparison runs — even when the stored
    ``bundle_content_hash`` still matches the current bundle content. A
    regress here means T015 touched a branch it should not have."""
    charter_path, metadata_path = _seed_charter(tmp_path)
    _write_metadata(metadata_path, charter_path)
    _seed_bundle_files(tmp_path)
    _seed_graph(tmp_path)
    real_hash = compute_bundle_content_hash(tmp_path)
    assert real_hash is not None
    _seed_manifest(tmp_path, built_in_only=False, bundle_content_hash=real_hash)

    # Drift the charter (without updating metadata) so charter_source, and
    # therefore synced_bundle, goes stale — even though bundle_content_hash
    # itself still matches the (untouched) bundle files.
    time.sleep(0.01)
    charter_path.write_text("# Charter (drifted)\n", encoding="utf-8")

    result = compute_freshness(tmp_path)

    assert result.synced_bundle.state == "stale"
    assert result.synthesized_drg.state == "stale"
    assert result.synthesized_drg.remediation == "spec-kitty charter synthesize"


def test_synthesized_drg_fresh_when_graph_followed_bundle(tmp_path: Path) -> None:
    charter_path, metadata_path = _seed_charter(tmp_path)
    _write_metadata(metadata_path, charter_path)
    _seed_bundle_files(tmp_path)
    _seed_graph(tmp_path)
    real_hash = compute_bundle_content_hash(tmp_path)
    assert real_hash is not None
    _seed_manifest(tmp_path, built_in_only=False, bundle_content_hash=real_hash)
    result = compute_freshness(tmp_path)
    assert result.synthesized_drg.state == "fresh"


# ---------------------------------------------------------------------------
# Content-identity comparison (WP03 / #2681 reader swap)
# ---------------------------------------------------------------------------


def test_synthesized_drg_fresh_after_mtime_only_bump(tmp_path: Path) -> None:
    """AS-1 (fresh survives mtime perturbation).

    A realistic past-dated ``created_at`` (e.g. ``2026-01-01…``, NOT the
    ``2099-…`` sentinel — NFR-006) loses to a bumped bundle mtime under the
    old ``manifest_ts + 1.0 < bundle_ts`` rule, so the pre-swap (still-mtime)
    reader wrongly reports ``stale`` here. GREEN after T015 swaps the
    comparison to content-identity — WP03's load-bearing per-WP red pin.
    """
    _seed_full_bundle(tmp_path)
    _seed_graph(tmp_path)
    real_hash = compute_bundle_content_hash(tmp_path)
    assert real_hash is not None
    _seed_manifest(
        tmp_path,
        built_in_only=False,
        created_at="2026-01-01T00:00:00+00:00",  # realistic past date, NOT 2099
        bundle_content_hash=real_hash,
    )

    _bump_bundle_mtimes_to_future(tmp_path)

    result = compute_freshness(tmp_path)

    assert result.synthesized_drg.state == "fresh"


def test_synthesized_drg_stale_when_bundle_content_genuinely_changed(tmp_path: Path) -> None:
    """AS-2 pin (fact #22): a genuine bundle-content edit is still ``stale``.

    May coincidentally pass on the pre-swap mtime reader too (editing
    content also bumps mtime) — its regression power activates once the
    content-hash reader lands; it is NOT the red-first proof (see AS-1 for
    that).
    """
    _seed_full_bundle(tmp_path)
    _seed_graph(tmp_path)
    real_hash = compute_bundle_content_hash(tmp_path)
    assert real_hash is not None
    _seed_manifest(
        tmp_path,
        built_in_only=False,
        created_at="2026-01-01T00:00:00+00:00",
        bundle_content_hash=real_hash,
    )

    # Genuinely edit bundle CONTENT (not just mtime) without re-seeding the
    # manifest's stored hash.
    governance_path = tmp_path / ".kittify" / "charter" / "governance.yaml"
    governance_path.write_text("schema_version: '1'\nchanged: true\n", encoding="utf-8")

    result = compute_freshness(tmp_path)

    assert result.synthesized_drg.state == "stale"


def test_synthesized_drg_2681_repro_cleared_via_synthesize(tmp_path: Path) -> None:
    """AS-5 (#2681 full repro, ``synthesize`` entry point).

    synthesize once -> a no-op-stable run occurs -> a git-style mtime bump
    (content unchanged) -> the pre-swap reader wrongly reports ``stale`` and
    STAYS stuck ``stale`` even after a ``synthesize`` remediation attempt
    (remediation's own fresh ``created_at`` still lags the artificially
    future-bumped bundle mtime — the exact #2681 "stuck stale" symptom).
    RED on the pre-swap reader (both assertions below fail); GREEN after
    T015 — one of WP03's two load-bearing per-WP red pins (with AS-1).
    """
    _seed_pipeline_bundle_files(tmp_path)
    adapter = _synth_adapter()
    synthesize(_base_synthesis_request("01AAAAAAAAAAAAAAAAAAAAAAAA"), adapter=adapter, repo_root=tmp_path)
    # No-op-stable run: fresh run_id, identical inputs (#1912/#1914).
    synthesize(_base_synthesis_request("01BBBBBBBBBBBBBBBBBBBBBBBB"), adapter=adapter, repo_root=tmp_path)

    _bump_bundle_mtimes_to_future(tmp_path)

    # Content unchanged by the mtime bump alone -> must already read fresh
    # (AS-1's guarantee, exercised here inside the full #2681 timeline).
    assert compute_freshness(tmp_path).synthesized_drg.state == "fresh"

    # Remediation via `synthesize` -- must not leave the DRG stuck stale.
    synthesize(_base_synthesis_request("01CCCCCCCCCCCCCCCCCCCCCCCC"), adapter=adapter, repo_root=tmp_path)

    assert compute_freshness(tmp_path).synthesized_drg.state == "fresh"


def test_synthesized_drg_2681_repro_cleared_via_resynthesize(tmp_path: Path) -> None:
    """AS-5 (#2681 full repro, ``resynthesize`` entry point) — separate fresh
    fixture, mirrors the ``synthesize`` case above via
    ``resynthesize_pipeline.run``. RED-then-GREEN alongside AS-1 (NFR-006:
    BOTH entry points covered)."""
    _seed_pipeline_bundle_files(tmp_path)
    adapter = _synth_adapter()
    synthesize(_base_synthesis_request("01DDDDDDDDDDDDDDDDDDDDDDDD"), adapter=adapter, repo_root=tmp_path)
    synthesize(_base_synthesis_request("01EEEEEEEEEEEEEEEEEEEEEEEE"), adapter=adapter, repo_root=tmp_path)

    _bump_bundle_mtimes_to_future(tmp_path)

    assert compute_freshness(tmp_path).synthesized_drg.state == "fresh"

    resynthesize_run(
        request=_base_synthesis_request("01FFFFFFFFFFFFFFFFFFFFFFFF"),
        adapter=adapter,
        topic="tactic:how-we-apply-directive-003",
        repo_root=tmp_path,
    )

    assert compute_freshness(tmp_path).synthesized_drg.state == "fresh"


def test_synthesized_drg_remediation_clears_genuine_content_change(tmp_path: Path) -> None:
    """Genuine-content-change remediation e2e (SC-003/AS-3 full proof).

    fresh -> edit ``governance.yaml`` CONTENT -> stale -> ``synthesize`` ->
    fresh; repeat the stale -> ``resynthesize`` -> fresh cycle. Proves
    WP02's writer recompute AND WP03's reader compose end-to-end — fails if
    either half is broken.
    """
    _seed_pipeline_bundle_files(tmp_path)
    adapter = _synth_adapter()
    synthesize(_base_synthesis_request("01GGGGGGGGGGGGGGGGGGGGGGGG"), adapter=adapter, repo_root=tmp_path)

    assert compute_freshness(tmp_path).synthesized_drg.state == "fresh"

    governance_path = tmp_path / ".kittify" / "charter" / "governance.yaml"
    governance_path.write_text(
        governance_path.read_text(encoding="utf-8") + "# drift-marker\n", encoding="utf-8"
    )
    assert compute_freshness(tmp_path).synthesized_drg.state == "stale"

    synthesize(_base_synthesis_request("01HHHHHHHHHHHHHHHHHHHHHHHH"), adapter=adapter, repo_root=tmp_path)
    assert compute_freshness(tmp_path).synthesized_drg.state == "fresh"

    governance_path.write_text(
        governance_path.read_text(encoding="utf-8") + "# drift-marker-2\n", encoding="utf-8"
    )
    assert compute_freshness(tmp_path).synthesized_drg.state == "stale"

    resynthesize_run(
        request=_base_synthesis_request("01JJJJJJJJJJJJJJJJJJJJJJJJ"),
        adapter=adapter,
        topic="tactic:how-we-apply-directive-003",
        repo_root=tmp_path,
    )
    assert compute_freshness(tmp_path).synthesized_drg.state == "fresh"


def test_to_dict_shape_matches_contract(tmp_path: Path) -> None:
    """``CharterFreshness.to_dict`` returns the three documented keys."""
    result = compute_freshness(tmp_path)
    d = result.to_dict()
    assert set(d.keys()) == {"charter_source", "synced_bundle", "synthesized_drg"}
    for layer in d.values():
        assert set(layer.keys()) >= {"state", "last_change", "remediation", "detail"}


@pytest.mark.parametrize(
    "scenario",
    ["fresh", "stale", "missing", "built_in_only", "invalid"],
)
def test_states_are_among_documented_vocabulary(scenario: str, tmp_path: Path) -> None:
    """Smoke: every documented state value is reachable by the computer."""
    charter_path, metadata_path = _seed_charter(tmp_path)
    if scenario == "missing":
        result = compute_freshness(tmp_path)
        states = {
            result.charter_source.state,
            result.synced_bundle.state,
            result.synthesized_drg.state,
        }
        assert "missing" in states
        return
    if scenario == "stale":
        _write_metadata(metadata_path, charter_path, mismatched=True)
        result = compute_freshness(tmp_path)
        assert result.charter_source.state == "stale"
        return
    if scenario == "fresh":
        _write_metadata(metadata_path, charter_path)
        _seed_bundle_files(tmp_path)
        result = compute_freshness(tmp_path)
        assert result.charter_source.state == "fresh"
        return
    if scenario == "built_in_only":
        _write_metadata(metadata_path, charter_path)
        _seed_bundle_files(tmp_path)
        _seed_manifest(tmp_path, built_in_only=True)
        result = compute_freshness(tmp_path)
        assert result.synthesized_drg.state == "built_in_only"
        return
    if scenario == "invalid":
        # FR-006 re-pointed this vocabulary smoke-entry: the only ``invalid``
        # producer is now ``_compute_charter_source`` ("charter.md exists but
        # cannot be hashed"), a genuine inconsistency — NOT the downgraded
        # built_in_only ∧ graph residue case.
        _write_metadata(metadata_path, charter_path)
        charter_path.unlink()
        charter_path.mkdir()  # a directory where a file is expected → unhashable
        result = compute_freshness(tmp_path)
        assert result.charter_source.state == "invalid"
        return
    pytest.fail(f"Unhandled scenario {scenario!r}")
