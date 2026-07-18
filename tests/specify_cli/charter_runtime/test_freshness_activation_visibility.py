"""#2759 seam core: config-activation visibility in the freshness read-path (WP03).

``charter activate``/``deactivate`` mutate ``.kittify/config.yaml``
(``activated_*``), which is not one of the four files
``charter.bundle.compute_bundle_content_hash`` covers, so a config<->derived
(references.yaml / DRG graph) drift used to stay invisible to
``synthesized_drg`` forever. This WP wires the already-built
``charter.consistency_check.run_consistency_check`` parity guard into the
freshness READ-path (``computer._compute_synthesized_drg``) so that drift
resolves to ``stale`` by construction (fail-closed, FR-003) instead of
silently reporting ``fresh``.

Covers:
- ``test_activation_without_reconcile_is_stale``: T009 red-first (SC-002,
  first half) -- a fresh project + ``charter activate`` (real writer,
  ``activation_engine.commit_plan``) with no compiled ``references.yaml``
  entry for the newly-activated directive reports ``stale``.
- ``test_reconcile_after_activation_returns_to_fresh``: T012 (SC-002, second
  half) -- reconciling the compiled bundle (references.yaml + a matching
  content-hash stamp, what ``charter generate`` + ``charter synthesize``
  produce) clears the drift back to ``fresh``.
- ``test_deactivate_without_reconcile_is_stale``: deactivate symmetric --
  the reverse-direction (paradigm-only) parity check fires when a
  deactivated-but-still-compiled paradigm is orphaned.
- ``test_deactivate_last_activation_writes_explicit_empty_and_stays_visible``:
  deactivate-to-empty edge -- ``.remove()`` writes an explicit ``[]``, which
  ``_has_explicit_activation`` treats as non-``None`` (parity still fires),
  guarding a future key-deletion refactor from silently reopening the hole.
- ``test_multi_kind_drift_reports_single_stale_signal``: cascade edge -- a
  simultaneous multi-kind config drift still resolves to exactly ONE
  ``synthesized_drg`` sub-state per freshness computation (the read-path
  evaluates parity once per call, not per drifted artifact).
- ``test_merge_defaults_seeded_activation_is_visible``: writer-agnostic
  (R-08) -- activation written via ``CharterPackManager.merge_defaults``
  (the ``pack_manager.py`` bypass that never touches
  ``activation_engine.commit_plan``) is equally visible, because
  ``run_consistency_check`` reads ``config.yaml`` directly.
- ``test_unchanged_bundle_hash_unaffected_by_parity_check``: NFR-002 (#2732)
  -- the parity read is a separate, COMPOSED signal; it never becomes a hash
  input, so an unchanged bundle still hashes identically.
- ``test_fresh_seed_built_in_only_project_not_forced_stale_by_drifted_config``:
  NFR-002 / R-01 -- a never-synthesized (``built_in_only``) project is a
  structural short-circuit that returns BEFORE the parity read is ever
  reached, so a drifted config.yaml must not force it stale. Asserts the
  PASS-STATE membership (``built_in_only`` ∈ preflight's ``_PASS_STATES``),
  not a literal ``"fresh"`` string.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from ruamel.yaml import YAML

from charter.invocation_context import ProjectContext
from charter.pack_manager import CharterPackManager
from specify_cli.charter_runtime.freshness import compute_freshness

pytestmark = [pytest.mark.git_repo]

from ..charter_preflight._fixtures import (
    init_git_repo,
    seed_charter,
    seed_manifest,
    write_metadata,
)

# Mirrors the preflight runner's own pass-state set (``_PASS_STATES`` in
# ``specify_cli.charter_runtime.preflight.runner``) -- kept local rather than
# imported so this test asserts the *contract*, not an implementation detail
# reachable only via the preflight package.
_PASS_STATES = frozenset({"fresh", "built_in_only"})

# Real, stable built-in artifacts (matches the pinning rationale in
# tests/doctrine/test_activation_parity_guard.py -- production-shaped ids,
# not placeholders).
_REAL_DIRECTIVE_STEM = "001-architectural-integrity-standard"
_REAL_DIRECTIVE_CANONICAL = "DIRECTIVE_001"
_REAL_PARADIGM_STEM_A = "domain-driven-design"
_REAL_PARADIGM_STEM_B = "atomic-design"


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _seed_project_graph(repo: Path) -> Path:
    """Create a schema-VALID, empty ``.kittify/doctrine/graph.yaml``.

    Deliberately local to this test module rather than reusing
    ``charter_preflight._fixtures.seed_graph``: that shared helper writes
    ``schema_version``/``nodes``/``edges`` only, which satisfies the
    freshness reader (only checks existence/mtime of this path) but is
    REJECTED by ``doctrine.drg.models.DRGGraph`` (``generated_at`` /
    ``generated_by`` are required) the moment something actually pydantic-
    validates it -- which ``charter.consistency_check``'s
    ``_check_graph_kind_parity`` does via ``load_validated_graph`` (it merges
    this file in as the "project" DRG layer). This WP is the first consumer
    that reaches that validation from a freshness-adjacent test, so it seeds
    a conformant document instead of widening the shared fixture's blast
    radius outside this WP's owned files.
    """
    graph_path = repo / ".kittify" / "doctrine" / "graph.yaml"
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    graph_path.write_text(
        dedent(
            """\
            schema_version: '1.0'
            generated_at: '2026-07-17T00:00:00Z'
            generated_by: test-fixture
            nodes: []
            edges: []
            """
        ),
        encoding="utf-8",
    )
    return graph_path


def _write_config(repo: Path, content: str) -> None:
    kittify = repo / ".kittify"
    kittify.mkdir(exist_ok=True)
    (kittify / "config.yaml").write_text(content, encoding="utf-8")


def _reference_entry(ref_id: str, kind: str) -> dict[str, str]:
    return {
        "id": ref_id,
        "kind": kind,
        "title": "x",
        "summary": "x",
        "source_path": "",
        "local_path": "x",
    }


def _write_references(charter_dir: Path, entries: list[dict[str, str]]) -> None:
    charter_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0.0",
        "generated_at": "2026-07-17T00:00:00Z",
        "mission": "software-dev",
        "template_set": "software-dev-default",
        "languages": ["python"],
        "references": entries,
    }
    yaml = YAML()
    yaml.default_flow_style = False
    with (charter_dir / "references.yaml").open("w", encoding="utf-8") as handle:
        yaml.dump(payload, handle)


def _seed_synthesized_repo(repo: Path, ref_entries: list[dict[str, str]]) -> Path:
    """Build a fully-synthesized, freshness-``fresh`` repo.

    Unlike ``_fixtures.make_fresh_repo`` (which seeds a trivial,
    ``references:``-key-less ``references.yaml`` -- fine for tests that never
    exercise activation, but not a valid *compiled reference set* input for
    ``run_consistency_check``), this writes a real ``references.yaml`` with
    the given entries FIRST, then stamps the synthesis manifest's
    ``bundle_content_hash`` from that same finalised bundle content (order
    matters: ``seed_manifest``'s auto-hash reads whatever is on disk at call
    time), so the content-identity hash comparison is genuinely satisfied
    before the (new, #2759) activation-parity read is ever reached.
    """
    init_git_repo(repo)
    charter_path, metadata_path = seed_charter(repo)
    write_metadata(metadata_path, charter_path)
    charter_dir = repo / ".kittify" / "charter"
    (charter_dir / "governance.yaml").write_text("schema_version: '1'\n", encoding="utf-8")
    (charter_dir / "directives.yaml").write_text("schema_version: '1'\n", encoding="utf-8")
    _write_references(charter_dir, ref_entries)
    seed_manifest(repo, built_in_only=False)
    _seed_project_graph(repo)
    return charter_dir


def _reconcile_references(repo: Path, ref_entries: list[dict[str, str]]) -> None:
    """Simulate ``charter generate`` (recompile references.yaml) + ``charter
    synthesize`` (re-stamp the manifest hash) reconciling config.yaml drift.
    """
    charter_dir = repo / ".kittify" / "charter"
    _write_references(charter_dir, ref_entries)
    seed_manifest(repo, built_in_only=False)


def _ctx(repo: Path) -> ProjectContext:
    return ProjectContext.from_repo(repo)


def _synthesized_drg_state(repo: Path) -> str:
    return compute_freshness(repo).synthesized_drg.state


# ---------------------------------------------------------------------------
# T009 / SC-002 (first half): activate without reconciling -> stale
# ---------------------------------------------------------------------------


def test_activation_without_reconcile_is_stale(tmp_path: Path) -> None:
    """A fresh project, then ``charter activate`` with no compiled reference
    for the new directive, reports ``stale`` (desired behavior; RED before
    the #2759 wiring, GREEN after)."""
    _seed_synthesized_repo(tmp_path, ref_entries=[])
    assert _synthesized_drg_state(tmp_path) == "fresh"  # baseline precondition

    _write_config(tmp_path, "activated_directives: []\n")
    CharterPackManager().activate(_ctx(tmp_path), "directive", _REAL_DIRECTIVE_STEM)

    assert _synthesized_drg_state(tmp_path) == "stale"


def test_activation_stale_reason_names_the_drift(tmp_path: Path) -> None:
    """The stale reason composes with (does not replace) the existing
    content-identity stale reasons and names the concrete drift."""
    _seed_synthesized_repo(tmp_path, ref_entries=[])
    _write_config(tmp_path, "activated_directives: []\n")
    CharterPackManager().activate(_ctx(tmp_path), "directive", _REAL_DIRECTIVE_STEM)

    sub = compute_freshness(tmp_path).synthesized_drg
    assert sub.state == "stale"
    assert sub.detail is not None
    assert f"directive/{_REAL_DIRECTIVE_STEM}" in sub.detail
    # Remediation MUST name `charter generate` (recompiles references.yaml from
    # the current activation state) -- bare `synthesize` cannot clear a
    # references-parity divergence, so pointing there would recreate the #2758
    # un-healable dead-end for the parity signal (aggregate-squad finding).
    assert sub.remediation == "spec-kitty charter generate && spec-kitty charter synthesize"
    assert "generate" in sub.remediation


# ---------------------------------------------------------------------------
# T012: SC-002 (second half) -- reconcile clears the drift
# ---------------------------------------------------------------------------


def test_reconcile_after_activation_returns_to_fresh(tmp_path: Path) -> None:
    """activate -> stale -> reconcile (recompile references.yaml + re-stamp
    the manifest, what ``charter generate`` + ``charter synthesize`` do) ->
    fresh again."""
    _seed_synthesized_repo(tmp_path, ref_entries=[])
    _write_config(tmp_path, "activated_directives: []\n")
    CharterPackManager().activate(_ctx(tmp_path), "directive", _REAL_DIRECTIVE_STEM)
    assert _synthesized_drg_state(tmp_path) == "stale"

    _reconcile_references(
        tmp_path,
        [_reference_entry(f"DIRECTIVE:{_REAL_DIRECTIVE_CANONICAL}", "directive")],
    )

    assert _synthesized_drg_state(tmp_path) == "fresh"


# ---------------------------------------------------------------------------
# Deactivate symmetric + deactivate-to-empty edge
# ---------------------------------------------------------------------------


def test_deactivate_without_reconcile_is_stale(tmp_path: Path) -> None:
    """Deactivating one of two compiled paradigms orphans it in
    references.yaml (reverse-direction parity, paradigms only) -- stale."""
    _seed_synthesized_repo(
        tmp_path,
        ref_entries=[
            _reference_entry(f"PARADIGM:{_REAL_PARADIGM_STEM_A}", "paradigm"),
            _reference_entry(f"PARADIGM:{_REAL_PARADIGM_STEM_B}", "paradigm"),
        ],
    )
    _write_config(
        tmp_path,
        f"activated_paradigms:\n  - {_REAL_PARADIGM_STEM_A}\n  - {_REAL_PARADIGM_STEM_B}\n",
    )
    assert _synthesized_drg_state(tmp_path) == "fresh"  # baseline: config matches compiled set

    CharterPackManager().deactivate(_ctx(tmp_path), "paradigm", _REAL_PARADIGM_STEM_B)

    assert _synthesized_drg_state(tmp_path) == "stale"


def test_deactivate_last_activation_writes_explicit_empty_and_stays_visible(tmp_path: Path) -> None:
    """Deactivating the LAST activated paradigm writes an explicit ``[]``
    (``activation_engine`` uses ``.remove()``, never key-deletion) -- and
    ``_has_explicit_activation`` treats ``[]`` as non-``None``, so parity
    still fires. Locks the guard against a future refactor to key-deletion
    silently reopening the hole via the ``if not _has_explicit_activation``
    early-exit.
    """
    _seed_synthesized_repo(
        tmp_path,
        ref_entries=[_reference_entry(f"PARADIGM:{_REAL_PARADIGM_STEM_A}", "paradigm")],
    )
    _write_config(tmp_path, f"activated_paradigms:\n  - {_REAL_PARADIGM_STEM_A}\n")
    assert _synthesized_drg_state(tmp_path) == "fresh"

    CharterPackManager().deactivate(_ctx(tmp_path), "paradigm", _REAL_PARADIGM_STEM_A)

    yaml = YAML(typ="safe")
    config_data = yaml.load((tmp_path / ".kittify" / "config.yaml").read_text(encoding="utf-8"))
    assert config_data.get("activated_paradigms") == []  # explicit [], not a deleted key

    assert _synthesized_drg_state(tmp_path) == "stale"


# ---------------------------------------------------------------------------
# Cascade edge: multi-kind drift still resolves to ONE sub-state per call
# ---------------------------------------------------------------------------


def test_multi_kind_drift_reports_single_stale_signal(tmp_path: Path) -> None:
    """A simultaneous drift across two kinds (what a ``--cascade``
    multi-artifact flip produces) still resolves to exactly one
    ``synthesized_drg`` :class:`FreshnessSubState` per freshness computation
    -- the read-path parity check runs once per ``compute_freshness`` call,
    not once per drifted artifact, so a cascade is structurally moot here.
    """
    _seed_synthesized_repo(tmp_path, ref_entries=[])
    _write_config(tmp_path, "activated_directives: []\nactivated_paradigms: []\n")
    ctx = _ctx(tmp_path)
    CharterPackManager().activate(ctx, "directive", _REAL_DIRECTIVE_STEM)
    CharterPackManager().activate(_ctx(tmp_path), "paradigm", _REAL_PARADIGM_STEM_A)

    result = compute_freshness(tmp_path)

    assert result.synthesized_drg.state == "stale"
    assert result.synthesized_drg.detail is not None
    # Both kinds' drift is named in the SAME, single composed reason -- proves
    # the guard ran once over the whole config, not once per drifted kind.
    assert f"directive/{_REAL_DIRECTIVE_STEM}" in result.synthesized_drg.detail
    assert f"paradigm/{_REAL_PARADIGM_STEM_A}" in result.synthesized_drg.detail


# ---------------------------------------------------------------------------
# Writer-agnostic (R-08): merge_defaults bypasses activation_engine entirely
# ---------------------------------------------------------------------------


def test_merge_defaults_seeded_activation_is_visible(tmp_path: Path) -> None:
    """Activation state seeded via ``CharterPackManager.merge_defaults`` (the
    ``pack_manager.py`` writer that never calls
    ``activation_engine.commit_plan``) is equally visible to the freshness
    read-path, because ``run_consistency_check`` reads ``config.yaml``
    directly rather than being told which writer touched it.
    """
    _seed_synthesized_repo(tmp_path, ref_entries=[])
    assert _synthesized_drg_state(tmp_path) == "fresh"  # baseline: no config.yaml yet

    result = CharterPackManager().merge_defaults(_ctx(tmp_path))
    assert result.kinds_written  # sanity: the bypass writer actually wrote something

    assert _synthesized_drg_state(tmp_path) == "stale"


# ---------------------------------------------------------------------------
# NFR-002 (#2732) preserve: composed signal, not a hash input; fresh-seed intact
# ---------------------------------------------------------------------------


def test_unchanged_bundle_hash_unaffected_by_parity_check(tmp_path: Path) -> None:
    """An unchanged bundle hashes identically before and after the parity
    read runs -- the #2759 signal is COMPOSED WITH content-identity, never
    folded into the hash itself."""
    from charter.bundle import compute_bundle_content_hash

    _seed_synthesized_repo(
        tmp_path,
        ref_entries=[_reference_entry(f"DIRECTIVE:{_REAL_DIRECTIVE_CANONICAL}", "directive")],
    )
    _write_config(tmp_path, f"activated_directives:\n  - {_REAL_DIRECTIVE_STEM}\n")

    hash_before = compute_bundle_content_hash(tmp_path)
    result = compute_freshness(tmp_path)
    hash_after = compute_bundle_content_hash(tmp_path)

    assert hash_before is not None
    assert hash_before == hash_after
    assert result.synthesized_drg.state == "fresh"  # coherent config -> unaffected by the new read


def test_fresh_seed_built_in_only_project_not_forced_stale_by_drifted_config(
    tmp_path: Path,
) -> None:
    """A never-synthesized (``built_in_only``) project is a structural
    short-circuit that returns BEFORE the activation-parity read is ever
    reached (R-01) -- even when config.yaml carries an activation with no
    compiled reference set to check it against at all. Asserts PASS-STATE
    membership, not the literal ``"fresh"`` string (``built_in_only`` is
    itself a distinct passing state)."""
    init_git_repo(tmp_path)
    charter_path, metadata_path = seed_charter(tmp_path)
    write_metadata(metadata_path, charter_path)
    charter_dir = tmp_path / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    (charter_dir / "governance.yaml").write_text("schema_version: '1'\n", encoding="utf-8")
    (charter_dir / "directives.yaml").write_text("schema_version: '1'\n", encoding="utf-8")
    # No references.yaml at all -- this project has never run `charter generate`.
    seed_manifest(tmp_path, built_in_only=True)  # no graph.yaml
    _write_config(tmp_path, f"activated_directives:\n  - {_REAL_DIRECTIVE_STEM}\n")

    state = _synthesized_drg_state(tmp_path)

    assert state in _PASS_STATES
    assert state == "built_in_only"
