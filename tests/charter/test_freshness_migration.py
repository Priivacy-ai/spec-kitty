"""Migration anchors + cross-caller bake for the content-identity recipe (WP03 / T006).

Mission ``bundle-freshness-hash-input-and-activation-01KXR0M1``. Two DISTINCT
starting states each self-heal to ``fresh`` in one standard ``synthesize`` run,
and every write-side caller bakes the SAME recipe (FR-004 single authority):

- **FR-003** (legacy-``None`` self-heal): a pre-#2732 ``schema: '2'`` manifest with
  ``bundle_content_hash: null`` reads ``stale`` and heals after generate→synthesize.
- **FR-007** (recipe migration): a #2732-era ``schema: '3'`` manifest carrying a
  real OLD 4-file hash (governance/directives/**references**/metadata) that no
  longer matches the NEW recipe (triad + directive digest) reads ``stale`` once
  and heals after a single ``synthesize`` — no schema bump (C-002).
- **Cross-caller bake**: ``promote()`` (via ``synthesize``) and ``resynthesize``
  both stamp ``bundle_content_hash == compute_bundle_content_hash`` (stored ==
  current); the ``built_in_only`` toggle (``project_drg.apply_post_condition``)
  PRESERVES the stored hash rather than recomputing/dropping it.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from charter.bundle import compute_bundle_content_hash
from charter.hasher import hash_content
from charter.synthesizer import FixtureAdapter, SynthesisRequest, SynthesisTarget, synthesize
from charter.synthesizer.manifest import MANIFEST_PATH, load_yaml as load_manifest
from charter.synthesizer.project_drg import apply_post_condition
from charter.synthesizer.resynthesize_pipeline import run as resynthesize_run
from specify_cli.charter_runtime.freshness import compute_freshness

pytestmark = [pytest.mark.integration]

_SYNTH_FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "synthesizer"
# The pre-WP02 (#2732-era) recipe hashed these four files, in this order.
_OLD_RECIPE_FILES = ("governance.yaml", "directives.yaml", "references.yaml", "metadata.yaml")


# --------------------------------------------------------------------------- #
# Seeding helpers (duplicated by convention — no cross-test-module imports).
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
    charter_dir = repo / ".kittify" / "charter"
    for name in ("governance.yaml", "directives.yaml"):
        (charter_dir / name).write_text("schema_version: '1'\n", encoding="utf-8")


def _seed_references(repo: Path) -> None:
    (repo / ".kittify" / "charter" / "references.yaml").write_text("references: []\n", encoding="utf-8")


def _seed_graph(repo: Path) -> Path:
    graph_path = repo / ".kittify" / "doctrine" / "graph.yaml"
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    graph_path.write_text("schema_version: '1.0'\nnodes: []\nedges: []\n", encoding="utf-8")
    return graph_path


def _seed_manifest(
    repo: Path,
    *,
    schema_version: str,
    built_in_only: bool,
    bundle_content_hash: str | None,
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


def _old_recipe_hash(repo: Path) -> str:
    """Reproduce the pre-WP02 (#2732-era) 4-file recipe exactly: per-file
    ``hash_content`` of governance/directives/references/metadata, combined by
    hashing their newline-joined concatenation. Produces a genuine #2732-era
    stored hash that the NEW recipe must self-heal (FR-007)."""
    charter_dir = repo / ".kittify" / "charter"
    # Explicit annotations: ``charter.*`` is ``follow_imports=skip``'d, collapsing
    # hash_content's ``-> str`` return to ``Any`` at these call sites.
    digests: list[str] = [
        hash_content((charter_dir / name).read_text(encoding="utf-8")) for name in _OLD_RECIPE_FILES
    ]
    combined: str = hash_content("\n".join(digests))
    return combined


def _synth_adapter() -> FixtureAdapter:
    return FixtureAdapter(fixture_root=_SYNTH_FIXTURE_ROOT)


def _seed_pipeline_bundle_files(repo: Path) -> None:
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


# --------------------------------------------------------------------------- #
# FR-003 — legacy-``None`` self-heal (distinct anchor)
# --------------------------------------------------------------------------- #


def test_fr003_legacy_none_hash_is_stale_then_fresh_after_synthesize(tmp_path: Path) -> None:
    """FR-003: a pre-#2732 ``schema: '2'`` manifest with ``bundle_content_hash =
    None`` reads ``stale``, then heals to ``fresh`` after a standard synthesize."""
    _seed_pipeline_bundle_files(tmp_path)
    _seed_graph(tmp_path)
    _seed_manifest(tmp_path, schema_version="2", built_in_only=False, bundle_content_hash=None)

    assert compute_freshness(tmp_path).synthesized_drg.state == "stale"

    synthesize(_base_synthesis_request("01AAAAAAAAAAAAAAAAAAAAAAAA"), adapter=_synth_adapter(), repo_root=tmp_path)

    assert compute_freshness(tmp_path).synthesized_drg.state == "fresh"
    assert load_manifest(tmp_path / MANIFEST_PATH).bundle_content_hash is not None


# --------------------------------------------------------------------------- #
# FR-007 — recipe migration self-heal (distinct anchor, no schema bump)
# --------------------------------------------------------------------------- #


def test_fr007_old_four_file_hash_is_stale_once_then_fresh_after_synthesize(tmp_path: Path) -> None:
    """FR-007: a #2732-era ``schema: '3'`` manifest carrying a real OLD 4-file
    hash (incl. references.yaml) mismatches the NEW recipe → one-time ``stale``,
    then ``fresh`` after a single ``synthesize`` (C-002: no schema bump)."""
    _seed_pipeline_bundle_files(tmp_path)
    _seed_references(tmp_path)  # the OLD recipe hashed references.yaml
    _seed_graph(tmp_path)

    old_hash = _old_recipe_hash(tmp_path)
    # The NEW recipe (triad + directive digest, references dropped) differs.
    assert compute_bundle_content_hash(tmp_path) != old_hash
    _seed_manifest(tmp_path, schema_version="3", built_in_only=False, bundle_content_hash=old_hash)

    assert compute_freshness(tmp_path).synthesized_drg.state == "stale"

    synthesize(_base_synthesis_request("01BBBBBBBBBBBBBBBBBBBBBBBB"), adapter=_synth_adapter(), repo_root=tmp_path)

    assert compute_freshness(tmp_path).synthesized_drg.state == "fresh"


# --------------------------------------------------------------------------- #
# Cross-caller bake — one recipe consumed by every writer (FR-004)
# --------------------------------------------------------------------------- #


def test_promote_bakes_the_new_recipe_digest(tmp_path: Path) -> None:
    """``promote()`` (via ``synthesize``) stamps ``bundle_content_hash`` equal to
    a fresh ``compute_bundle_content_hash`` (stored == current)."""
    _seed_pipeline_bundle_files(tmp_path)

    synthesize(_base_synthesis_request("01CCCCCCCCCCCCCCCCCCCCCCCC"), adapter=_synth_adapter(), repo_root=tmp_path)

    manifest = load_manifest(tmp_path / MANIFEST_PATH)
    assert manifest.bundle_content_hash is not None
    assert manifest.bundle_content_hash == compute_bundle_content_hash(tmp_path)


def test_resynthesize_bakes_the_new_recipe_digest(tmp_path: Path) -> None:
    """``resynthesize`` re-stamps ``bundle_content_hash`` via the SAME recipe
    (stored == current), threading ``repo_root`` correctly."""
    _seed_pipeline_bundle_files(tmp_path)
    adapter = _synth_adapter()
    synthesize(_base_synthesis_request("01DDDDDDDDDDDDDDDDDDDDDDDD"), adapter=adapter, repo_root=tmp_path)

    result = resynthesize_run(
        request=_base_synthesis_request("01EEEEEEEEEEEEEEEEEEEEEEEE"),
        adapter=adapter,
        topic="tactic:how-we-apply-directive-003",
        repo_root=tmp_path,
    )

    assert result.manifest.bundle_content_hash is not None
    assert result.manifest.bundle_content_hash == compute_bundle_content_hash(tmp_path)
    assert load_manifest(tmp_path / MANIFEST_PATH).bundle_content_hash == compute_bundle_content_hash(tmp_path)


def test_built_in_only_toggle_preserves_stored_hash_not_recompute(tmp_path: Path) -> None:
    """``project_drg.apply_post_condition`` (the ``built_in_only`` toggle)
    PRESERVES the stored ``bundle_content_hash`` via ``model_copy`` — it does not
    recompute or silently drop it to ``None`` (the reader short-circuits on
    ``built_in_only`` before the hash compare, so recomputing would be dead work).
    """
    _seed_pipeline_bundle_files(tmp_path)
    _seed_graph(tmp_path)
    stored = compute_bundle_content_hash(tmp_path)
    assert stored is not None
    _seed_manifest(tmp_path, schema_version="3", built_in_only=False, bundle_content_hash=stored)

    # Toggle to built_in_only (no project graph) — must preserve the stored hash.
    apply_post_condition(tmp_path, has_project_graph=False)

    toggled = load_manifest(tmp_path / MANIFEST_PATH)
    assert toggled.built_in_only is True
    assert toggled.bundle_content_hash == stored  # preserved, not recomputed/dropped
