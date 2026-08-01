"""Post-move reality guards for the built-in doctrine-pack relocation (mission
``relocate-builtin-doctrine-packs-01KYT87F``).

WP01 committed three *pre-move* preflight guards that ran **before** WP03
physically moved any file, so the relocation could be proven behavior-preserving
up front:

1. an inventory-completeness sweep that failed if any reader of a *moving* tree
   was unclassified in ``occurrence_map.yaml``;
2. a fixture-integrity check on the captured graph-identity baseline;
3. a manifest-sanity check that every move-set path existed pre-move.

The move is now done. The pre-move-*tree* guards (1) and the pre-move manifest
existence check (3) assert a tree that no longer exists and are therefore
retired — they are replaced below by **post-move reality** assertions that pin
the relocation actually happened: the moving trees are gone from
``src/doctrine/<kind>/built-in`` and present under ``packs/built-in/<kind>``,
and the DRG fragments moved out of the ``src/doctrine`` root into
``packs/built-in``.

Still meaningful and kept unchanged:

* the **fixture-integrity** checks (2) — the graph-identity baseline is a
  historical projection that must stay a full-model projection (DIR-005);
* the **manifest-shape** check — ``content-manifest.json`` is intentionally
  retained in *pre-move* form (its 14 fragments + 2 ``.py`` payloads feed
  ``test_packaging_parity``), so its *shape* is still asserted while its
  per-path *existence* is not;
* the **occurrence_map** REPOINT classification of ``src/charter/catalog.py``.

Note on the reader that the pre-move sweep missed: the sweep's completeness
regex keyed on a literal ``/ "built-in"`` join, so it could not see
``charter.pack_manager._scan_layer_dirs``, which resolved the built-in layer
through a *loop-variable* ``layer`` segment (``root / base_dir / layer``). That
reader was left pointing at the emptied ``src/doctrine`` root by the move and
is repointed to the ``packs/built-in`` seam in the post-merge remediation
(``charter.pack_manager`` now resolves via ``resolve_pack_root("built-in")``).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #

_THIS = Path(__file__).resolve()
REPO_ROOT = _THIS.parents[2]
SRC_ROOT = REPO_ROOT / "src"
DOCTRINE_ROOT = SRC_ROOT / "doctrine"
PACKS_BUILT_IN = REPO_ROOT / "packs" / "built-in"
FIXTURES = _THIS.parent / "fixtures"
BASELINE_JSON = FIXTURES / "graph-identity.baseline.json"
MANIFEST_JSON = FIXTURES / "content-manifest.json"
OCCURRENCE_MAP = (
    REPO_ROOT
    / "kitty-specs"
    / "relocate-builtin-doctrine-packs-01KYT87F"
    / "occurrence_map.yaml"
)

# The 9 content kinds whose ``<kind>/built-in`` directory relocated to
# ``packs/built-in/<kind>``. The value is the artefact glob each kind ships.
MOVING_KIND_GLOBS: dict[str, str] = {
    "agent_profiles": "*.agent.yaml",
    "directives": "*.directive.yaml",
    "procedures": "*.procedure.yaml",
    "tactics": "*.tactic.yaml",
    "paradigms": "*.paradigm.yaml",
    "styleguides": "*.styleguide.yaml",
    "toolguides": "*.toolguide.yaml",
    "assets": "*.asset.yaml",
    "glossary_packs": "*.glossary-pack.yaml",
}
MOVING_KIND_DIRS = frozenset(MOVING_KIND_GLOBS)

# The two ``.py`` asset payloads that lived inside moving trees and relocated as
# *data* (hyphenated ``built-in`` dirs are not importable — these are never
# imported). They now live under ``packs/built-in``.
PAYLOAD_PY = (
    "packs/built-in/assets/docs_structural_lint.py",
    "packs/built-in/toolguides/system_tools/__init__.py",
)


def _artefact_files(directory: Path, pattern: str) -> list[Path]:
    """Return artefact files under *directory* matching *pattern*, ignoring the
    ``__pycache__`` build-artifact directory (a stale ``.pyc`` is not content)."""
    if not directory.is_dir():
        return []
    return [p for p in directory.rglob(pattern) if "__pycache__" not in p.parts]


# --------------------------------------------------------------------------- #
# Check 1 (post-move) — the relocation actually happened
# --------------------------------------------------------------------------- #


def test_moving_trees_are_retired_from_src_doctrine() -> None:
    """Every ``src/doctrine/<kind>/built-in`` tree must hold no artefact content.

    The move emptied these trees; a stray artefact left behind here would be
    loaded from the retired location and silently shadow the relocated pack
    (the exact regression the relocation set out to remove)."""
    survivors: dict[str, list[str]] = {}
    for kind, glob in MOVING_KIND_GLOBS.items():
        legacy = DOCTRINE_ROOT / kind / "built-in"
        found = _artefact_files(legacy, glob)
        if found:
            survivors[kind] = [p.relative_to(REPO_ROOT).as_posix() for p in found]
    assert not survivors, (
        "artefacts still live under the retired src/doctrine/<kind>/built-in "
        f"trees (they must move to packs/built-in/<kind>): {survivors}"
    )


def test_moving_trees_are_present_under_packs_built_in() -> None:
    """Every moving kind must resolve at least one artefact under
    ``packs/built-in/<kind>`` — the relocation target (per-kind floor, so one
    kind's broken glob cannot hide behind another's population)."""
    missing = [
        kind
        for kind, glob in MOVING_KIND_GLOBS.items()
        if not _artefact_files(PACKS_BUILT_IN / kind, glob)
    ]
    assert not missing, f"packs/built-in has zero artefacts for: {missing}"


def test_graph_fragments_relocated_out_of_src_doctrine_root() -> None:
    """The 14 ``*.graph.yaml`` DRG fragments moved from the ``src/doctrine``
    root into ``packs/built-in`` — none may remain at the old root."""
    strays = sorted(p.relative_to(REPO_ROOT).as_posix() for p in DOCTRINE_ROOT.glob("*.graph.yaml"))
    assert not strays, f"DRG fragments still at the retired src/doctrine root: {strays}"

    fragments = sorted(PACKS_BUILT_IN.glob("*.graph.yaml"))
    assert len(fragments) == 14, f"expected 14 DRG fragments under packs/built-in, found {len(fragments)}"  # golden-count: cardinality-is-contract


def test_asset_payloads_relocated_under_packs_built_in() -> None:
    """The two ``.py`` asset payloads that move as data now live under
    ``packs/built-in`` and no longer under the retired ``src/doctrine`` trees."""
    for payload in PAYLOAD_PY:
        assert (REPO_ROOT / payload).is_file(), f"relocated asset payload missing: {payload}"


# --------------------------------------------------------------------------- #
# Check 2 — fixture integrity (DIR-005) — unchanged, still meaningful
# --------------------------------------------------------------------------- #


def _load_baseline() -> dict:
    return json.loads(BASELINE_JSON.read_text(encoding="utf-8"))


def test_baseline_smoke_counts() -> None:
    baseline = _load_baseline()
    assert len(baseline["nodes"]) == 324  # golden-count: cardinality-is-contract
    assert len(baseline["edges"]) == 892  # golden-count: cardinality-is-contract


def test_baseline_is_full_projection_not_degenerate() -> None:
    """DIR-005: the fixture must be a full-model projection, so WP07's identity
    test cannot pass vacuously against an all-null fixture."""
    baseline = _load_baseline()
    edges = baseline["edges"]
    nodes = baseline["nodes"]

    # Every edge row is [source, relation, target, when, reason] — exactly 5.
    for row in edges:
        assert len(row) == 5, f"edge row is not a 5-field projection: {row!r}"  # golden-count: cardinality-is-contract

    # ``when`` gates delivery and ``reason`` documents intent — at least one of
    # each must be non-null, or the projection dropped them.
    assert any(row[3] is not None for row in edges), "no edge carries a non-null `when`"
    assert any(row[4] is not None for row in edges), "no edge carries a non-null `reason`"

    # Every node row is [urn, label, tags]; tags is a list; tagged-kind nodes
    # (e.g. anti-pattern smell nodes) must carry non-empty tags.
    for row in nodes:
        assert len(row) == 3, f"node row is not a 3-field projection: {row!r}"  # golden-count: cardinality-is-contract
        assert isinstance(row[2], list), f"node tags is not a list: {row!r}"
    assert any(row[2] for row in nodes), "no node carries non-empty tags"


# --------------------------------------------------------------------------- #
# Check 3 — manifest shape (pre-move form, kept for test_packaging_parity)
# --------------------------------------------------------------------------- #


def _load_manifest() -> list[str]:
    return json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))


def test_manifest_is_a_sorted_deduped_set() -> None:
    """The content manifest is intentionally retained in *pre-move* form (its
    paths feed ``test_packaging_parity``), so its per-path existence is no longer
    asserted here — only that it is a well-formed, sorted, deduped path set."""
    manifest = _load_manifest()
    assert manifest, "content manifest is empty"
    assert manifest == sorted(set(manifest)), "manifest is not a sorted, deduped set"


def test_manifest_includes_fragments_and_payloads() -> None:
    manifest = set(_load_manifest())
    fragments = [p for p in manifest if p.endswith(".graph.yaml")]
    assert len(fragments) == 14, f"expected 14 DRG fragments, found {len(fragments)}"  # golden-count: cardinality-is-contract
    # The manifest lists the pre-move payload locations (src/doctrine/...); the
    # relocated locations are asserted by
    # ``test_asset_payloads_relocated_under_packs_built_in`` above.
    pre_move_payloads = (
        "src/doctrine/assets/built-in/docs_structural_lint.py",
        "src/doctrine/toolguides/built-in/system_tools/__init__.py",
    )
    for payload in pre_move_payloads:
        assert payload in manifest, f"asset payload missing from manifest: {payload}"


# --------------------------------------------------------------------------- #
# Check 4 — occurrence_map REPOINT classification (historical, still meaningful)
# --------------------------------------------------------------------------- #


def test_charter_catalog_present_as_repoint() -> None:
    """The catalog scanner is a second, files("doctrine")-rooted built-in reader
    that no per-kind-anchor guard catches; it must be classified REPOINT."""
    lines = OCCURRENCE_MAP.read_text(encoding="utf-8").splitlines()
    idx = next(
        (i for i, ln in enumerate(lines) if "catalog.py" in ln),
        None,
    )
    assert idx is not None, "src/charter/catalog.py missing from occurrence_map"
    # The disposition sits on the same or the immediately-following action line.
    window = "\n".join(lines[idx : idx + 2])
    assert "REPOINT" in window, "catalog.py must be classified REPOINT"
