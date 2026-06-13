"""WP05 — cross-seam consumer integration tests (FR-007 + A/B residual sites).

These pin the behaviour of the three dual-seam files this WP migrates onto the
WP03 topology authority (``coordination.surface_resolver``) and the WP04
branch-identity authority (``lanes.branch_naming``):

* ``status/aggregate.py`` — cluster-A topology classification + cluster-B
  branch compose.
* ``coordination/status_transition.py:_identity_for_request`` — FR-007
  fabrication eradication of the on-disk transaction-dir mid8.
* ``cli/commands/implement.py:_resolve_bookkeeping_transaction_identifiers`` —
  FR-007 fabrication eradication of the same idiom.

The headline FR-007 assertions are *adversarial*: a bare-slug mission (no
``mission_id``, no ``mid8``, no legacy ``NNN-`` prefix, no mid8 tail) used to
fabricate ``(slug.replace("-","")+"00000000")[:8]`` for the transaction-dir
name; post-fix it must fail closed with :class:`BranchIdentityUnresolved`
rather than name a wrong-but-plausible on-disk directory (NFR-003).
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from specify_cli.cli.commands.implement import (
    _resolve_bookkeeping_transaction_identifiers,
)
from specify_cli.coordination.status_transition import _identity_for_request
from specify_cli.lanes.branch_naming import BranchIdentityUnresolved
from specify_cli.status.models import Lane, TransitionRequest

pytestmark = pytest.mark.integration


_SRC_ROOT = Path(__file__).resolve().parents[2] / "src"

# The fabrication idiom the seam eradicates (research-authority-seams.md §3).
# Mirrors the ratchet substrings so this integration test fails the same way
# the architectural ratchet would, but scoped to the WP05-owned files.
_FABRICATION_IDIOMS = (
    '+ "00000000")[:8]',
    '+"00000000")[:8]',
    'replace("-", "") + "00000000"',
    'replace("-","") + "00000000"',
)

_WP05_OWNED_FILES = (
    "specify_cli/status/aggregate.py",
    "specify_cli/coordination/status_transition.py",
    "specify_cli/cli/commands/implement.py",
)


def _write_bare_slug_mission(
    repo: Path, slug: str, *, coordination_branch: str | None = None
) -> Path:
    """Create a mission whose meta carries NO identity disambiguator.

    No ``mission_id``, no ``mid8``. When *coordination_branch* is supplied the
    mission declares coordination topology (the fail-closed case); otherwise it
    is a legacy/flattened/meta-less mission that degrades to the bare surface.
    """
    feature_dir = repo / "kitty-specs" / slug
    feature_dir.mkdir(parents=True)
    meta: dict[str, object] = {
        "mission_slug": slug,
        # deliberately NO mission_id / mid8 — the bare-slug case.
        "mission_number": None,
        "mission_type": "software-dev",
        "friendly_name": "Bare slug fixture",
    }
    if coordination_branch is not None:
        meta["coordination_branch"] = coordination_branch
    (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return feature_dir


# ---------------------------------------------------------------------------
# T019 — FR-007: fabrication eradication at the two transaction-identity sites
# ---------------------------------------------------------------------------


def test_status_transition_coord_bare_slug_fails_closed(tmp_path: Path) -> None:
    """``_identity_for_request`` must NOT fabricate a mid8 for a coord mission.

    Pre-fix: ``effective_mid8`` was fabricated from the slug, naming a
    wrong-but-plausible on-disk coord transaction dir. Post-fix: a
    coordination-topology mission (``coordination_branch`` declared) whose mid8
    cascade is exhausted fails closed with :class:`BranchIdentityUnresolved`
    rather than mis-route its coord write (NFR-003).
    """
    slug = "bare-slug-mission"
    feature_dir = _write_bare_slug_mission(
        tmp_path, slug, coordination_branch="kitty/mission-bare-slug-mission"
    )

    request = TransitionRequest(
        feature_dir=feature_dir,
        mission_slug=slug,
        wp_id="WP01",
        to_lane=Lane.PLANNED,
        actor="fixture",
        repo_root=tmp_path,
    )

    with pytest.raises(BranchIdentityUnresolved):
        _identity_for_request(request)


def test_implement_resolver_coord_bare_slug_fails_closed(tmp_path: Path) -> None:
    """``_resolve_bookkeeping_transaction_identifiers`` must fail closed too.

    Same FR-007 eradication at ``cli/commands/implement.py:395`` — gated on
    coordination topology being declared.
    """
    slug = "bare-slug-mission"
    feature_dir = _write_bare_slug_mission(
        tmp_path, slug, coordination_branch="kitty/mission-bare-slug-mission"
    )

    with pytest.raises(BranchIdentityUnresolved):
        _resolve_bookkeeping_transaction_identifiers(feature_dir, slug, tmp_path)


def test_meta_less_modern_slug_degrades_without_fabrication(tmp_path: Path) -> None:
    """A modern slug with NO coord topology degrades to the bare surface.

    Legacy / flattened / orphaned-event-post-merge missions write status with no
    ``coordination_branch`` and often no ``mission_id`` (the status store's
    documented orphaned-event path). The seam must preserve the pre-fix routing
    (bare-slug surface, empty mid8) for these — fail-closing here would break
    legitimate meta-less writes. Only coord-topology missions fail closed.
    """
    slug = "bare-slug-mission"
    feature_dir = _write_bare_slug_mission(tmp_path, slug)  # no coordination_branch

    _coord, _mission_id, _mid8, _eff_id, eff_mid8 = (
        _resolve_bookkeeping_transaction_identifiers(feature_dir, slug, tmp_path)
    )

    assert eff_mid8 == ""


def test_backfilled_legacy_mission_resolves_from_mission_id(tmp_path: Path) -> None:
    """Dual-era rule: a backfilled legacy ``NNN-`` mission resolves from its id.

    A pre-083 mission that has been through ``spec-kitty migrate
    backfill-identity`` carries a minted ``mission_id``; the seam resolves the
    mid8 from it (``mission_id[:8]``) — never from the ``+"00000000"`` idiom.
    """
    slug = "042-legacy-mission"
    feature_dir = tmp_path / "kitty-specs" / slug
    feature_dir.mkdir(parents=True)
    mission_id = "01KT042BACKFILLED0000000001"
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_slug": slug,
                "mission_id": mission_id,
                "mission_number": None,
                "mission_type": "software-dev",
                "friendly_name": "Backfilled legacy fixture",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    _coord, resolved_id, _mid8, _eff_id, eff_mid8 = (
        _resolve_bookkeeping_transaction_identifiers(feature_dir, slug, tmp_path)
    )

    assert resolved_id == mission_id
    assert eff_mid8 == mission_id[:8]


def test_unbackfilled_legacy_slug_resolves_to_bare_surface(tmp_path: Path) -> None:
    """An un-backfilled legacy ``NNN-`` mission routes to its bare-slug surface.

    Dual-era "legacy resolves" arm: a pre-083 mission never had a mid8, so the
    seam yields an empty mid8 (the bare-slug transaction dir) rather than the
    old fabricated ``<slug>-<garbage>`` dir that never existed. This preserves
    the pre-fix primary-checkout routing for legacy missions WITHOUT the
    forbidden idiom — only the modern-unresolvable case fails closed.
    """
    slug = "042-legacy-mission"
    feature_dir = _write_bare_slug_mission(tmp_path, slug)

    _coord, mission_id, _mid8, eff_id, eff_mid8 = (
        _resolve_bookkeeping_transaction_identifiers(feature_dir, slug, tmp_path)
    )

    assert mission_id is None
    assert eff_id == f"legacy-{slug}"
    # Empty mid8 → bare-slug surface; NOT the fabricated idiom output.
    assert eff_mid8 == ""


def test_mid8_slug_tail_resolves_without_fabrication(tmp_path: Path) -> None:
    """Dual-era rule: a modern slug carrying a mid8 tail resolves from the tail."""
    slug = "my-feature-01KT3YBD"
    feature_dir = _write_bare_slug_mission(tmp_path, slug)

    _coord, _mission_id, _mid8, _eff_id, eff_mid8 = (
        _resolve_bookkeeping_transaction_identifiers(feature_dir, slug, tmp_path)
    )

    assert eff_mid8 == "01KT3YBD"


# ---------------------------------------------------------------------------
# T019 — grep-zero fabrication idiom in WP05-owned files
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rel_path", _WP05_OWNED_FILES)
def test_no_fabrication_idiom_in_owned_files(rel_path: str) -> None:
    """The ``+"00000000")[:8]`` fabrication idiom must be absent from owned files.

    Mirrors the architectural ratchet (``test_topology_resolution_boundary``)
    assertion 3, scoped to the three WP05-owned modules so a regression here is
    caught even without the repo-wide ratchet.
    """
    text = (_SRC_ROOT / rel_path).read_text(encoding="utf-8")
    offenders = [idiom for idiom in _FABRICATION_IDIOMS if idiom in text]
    assert not offenders, (
        f"{rel_path} still fabricates a mid8 via {offenders!r}. Route the "
        "exhausted cascade through mid8_from_slug + fail closed with "
        "BranchIdentityUnresolved instead (FR-007)."
    )


# ---------------------------------------------------------------------------
# T019 — aggregate dual-seam behaviour
# ---------------------------------------------------------------------------


def test_aggregate_topology_predicate_uses_registry_authority() -> None:
    """``status/aggregate.py`` must classify coord topology via the WP03 seam.

    ``_is_coord_dir`` must delegate to ``is_registered_coord_worktree`` (the git
    registry authority) rather than infer coord-ness from path shape
    (``part == _WORKTREES_SEGMENT``). Asserted structurally over the AST so the
    test is independent of whitespace.
    """
    source = (_SRC_ROOT / "specify_cli/status/aggregate.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    is_coord_dir = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_is_coord_dir"
    )
    body_text = ast.get_source_segment(source, is_coord_dir) or ""

    assert "is_registered_coord_worktree" in body_text, (
        "_is_coord_dir must delegate to the WP03 topology authority "
        "is_registered_coord_worktree, not infer coord-ness from path shape."
    )
    assert "_WORKTREES_SEGMENT" not in body_text, (
        "_is_coord_dir must not re-introduce the path-shape predicate."
    )


def test_aggregate_branch_compose_uses_naming_authority() -> None:
    """``status/aggregate.py`` must compose the destination ref via the WP04 seam.

    The cluster-B compose site (the ``coordination_branch or ...`` fallback) must
    route through ``mission_branch_name_required`` / ``mission_branch_name``
    rather than the legacy ``f"kitty/mission-{slug}"`` f-string (FR-006 fold-in).
    """
    source = (_SRC_ROOT / "specify_cli/status/aggregate.py").read_text(encoding="utf-8")

    assert 'f"kitty/mission-{self.mission_slug}"' not in source, (
        "aggregate.py must not hand-compose kitty/mission-<slug>; route through "
        "mission_branch_name_required from lanes.branch_naming."
    )
    assert (
        "mission_branch_name_required" in source
        or "mission_branch_name(" in source
    ), "aggregate.py must consume the WP04 branch-naming authority."
