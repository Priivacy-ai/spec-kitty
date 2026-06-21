"""Unit tests for the guarded read-side seam ``resolve_handle_to_read_path``.

WP01 (IC-01; FR-001, FR-004, FR-005-invariant). These tests pin the five
behaviours the seam must guarantee:

(a) a canonical ``<slug>-<mid8>`` / full-id handle resolves the SAME directory as
    :func:`resolve_mission_read_path` called directly (the seam is a faithful
    super-set, not a divergent re-implementation);
(b) a bare slug whose coordination worktree EXISTS on disk resolves to the coord
    directory (mid8 derived from primary ``meta.json``);
(c) a coordination branch that is DECLARED in primary ``meta.json`` but NOT yet
    materialised on disk resolves to PRIMARY — the #1718 trap cell. The derived
    ``mid8`` is non-empty (proving derivation is orthogonal to the existence
    gate), yet the seam still returns primary because no coord worktree dir
    exists. Routing through ``resolve_status_surface_with_anchor`` instead would
    compose+return the (non-existent) coord path and FAIL this case;
(d) a traversal handle is rejected at ``assert_safe_path_segment`` BEFORE any
    path composition (FR-004);
(e) a coord-DECLARED topology with NO derivable mid8 fails closed with the typed
    :class:`StatusReadPathNotFound` (M5) — never a silent stale-primary read.

Fixtures use realistic test data (NFR-005): a real 26-char Crockford ULID and the
real ``.worktrees/<slug>-<mid8>-coord/kitty-specs/<slug>-<mid8>/`` on-disk layout.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.missions._read_path_resolver import (
    StatusReadPathNotFound,
    resolve_handle_to_read_path,
    _resolve_mission_read_path as resolve_mission_read_path,
)

pytestmark = [pytest.mark.fast]

# A real full 26-char Crockford ULID; the mid8 is its first 8 chars. The
# canonical ``<slug>-<mid8>`` directory name embeds that mid8.
FULL_ULID = "01KVJPEQ7M3K8N2QXR4VBZ9HCD"
MID8 = FULL_ULID[:8]  # "01KVJPEQ"
SLUG = "read-side-surface-resolver-adoption"
HANDLE = f"{SLUG}-{MID8}"  # canonical <slug>-<mid8>
COORD_BRANCH = f"kitty/mission-{SLUG}-{MID8}"


def _write_primary_meta(repo_root: Path, slug: str, meta: dict[str, object]) -> Path:
    """Materialise ``kitty-specs/<slug>/meta.json`` and return its mission dir."""
    primary_dir = repo_root / "kitty-specs" / slug
    primary_dir.mkdir(parents=True, exist_ok=True)
    (primary_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return primary_dir


def _make_coord_mission_dir(repo_root: Path, slug: str, mid8: str) -> Path:
    """Materialise the real ``.worktrees/<slug>-<mid8>-coord/...`` mission dir."""
    coord_dir = (
        repo_root
        / ".worktrees"
        / f"{slug}-{mid8}-coord"
        / "kitty-specs"
        / f"{slug}-{mid8}"
    )
    coord_dir.mkdir(parents=True)
    return coord_dir


class TestResolveHandleToReadPath:
    """The five binding cases for the guarded read-side seam (T005)."""

    def test_a_canonical_handle_matches_direct_resolve(self, tmp_path: Path) -> None:
        """(a) ``<slug>-<mid8>`` handle == direct ``resolve_mission_read_path``.

        The seam must be a faithful consumer of the existence-gated resolver, not
        a divergent re-implementation. With a materialised coord worktree the seam
        and a direct call (same derived mid8) must agree exactly.
        """
        coord_dir = _make_coord_mission_dir(tmp_path, SLUG, MID8)

        seam_result = resolve_handle_to_read_path(tmp_path, HANDLE)
        direct_result = resolve_mission_read_path(tmp_path, HANDLE, MID8)

        assert seam_result == coord_dir
        assert seam_result == direct_result

    def test_b_bare_slug_coord_fresh_returns_coord(self, tmp_path: Path) -> None:
        """(b) bare slug + materialised coord → coord dir (mid8 from primary meta).

        The handle carries no ``-<mid8>`` tail, so the disambiguator must come
        from the primary ``meta.json``. Once derived, the existing coord worktree
        is selected.
        """
        _write_primary_meta(
            tmp_path,
            SLUG,
            {
                "mission_slug": SLUG,
                "mission_id": FULL_ULID,
                "coordination_branch": COORD_BRANCH,
            },
        )
        coord_dir = _make_coord_mission_dir(tmp_path, SLUG, MID8)

        result = resolve_handle_to_read_path(tmp_path, SLUG)

        assert result == coord_dir

    def test_c_declared_but_unmaterialized_coord_returns_primary(
        self, tmp_path: Path
    ) -> None:
        """(c) #1718 trap: coord DECLARED but NOT on disk + bare slug → PRIMARY.

        The primary ``meta.json`` both declares a ``coordination_branch`` AND
        carries a ``mission_id`` (so the derived ``mid8`` is NON-empty — derivation
        is orthogonal to the existence gate). No coord worktree dir exists on
        disk, so the seam MUST return the PRIMARY directory. Routing through a
        composing surface (``resolve_status_surface_with_anchor``) would instead
        return the non-existent coord path and break this cell.
        """
        primary_dir = _write_primary_meta(
            tmp_path,
            SLUG,
            {
                "mission_slug": SLUG,
                "mission_id": FULL_ULID,
                "coordination_branch": COORD_BRANCH,
            },
        )
        # Deliberately do NOT create the coord worktree directory.

        result = resolve_handle_to_read_path(tmp_path, SLUG)

        assert result == primary_dir, (
            "#1718: a declared-but-unmaterialised coord must resolve PRIMARY "
            f"(expected {primary_dir}, got {result})."
        )

    def test_d_traversal_handle_raises_before_composition(
        self, tmp_path: Path
    ) -> None:
        """(d) a traversal handle is rejected at ``assert_safe_path_segment``.

        The guard fires FIRST (FR-004), before any ``kitty-specs`` join, so the
        raised error is ``ValueError`` from the segment guard — not a downstream
        path/file error.
        """
        with pytest.raises(ValueError):
            resolve_handle_to_read_path(tmp_path, "../../etc/passwd")

    def test_e_declared_coord_no_derivable_mid8_fails_closed(
        self, tmp_path: Path
    ) -> None:
        """(e) coord DECLARED + no derivable mid8 → fail-closed typed raise (M5).

        A bare slug (no ``-<mid8>`` tail) whose primary ``meta.json`` declares a
        ``coordination_branch`` but carries NEITHER ``mid8`` NOR ``mission_id``
        leaves the cascade exhausted (empty mid8). Reading primary would expose a
        stale view, so the seam raises :class:`StatusReadPathNotFound` rather than
        silently falling back.
        """
        _write_primary_meta(
            tmp_path,
            SLUG,
            {
                "mission_slug": SLUG,
                "coordination_branch": COORD_BRANCH,
            },
        )

        with pytest.raises(StatusReadPathNotFound) as exc_info:
            resolve_handle_to_read_path(tmp_path, SLUG)

        assert exc_info.value.mission_slug == SLUG
        assert exc_info.value.mid8 == ""

    def test_require_exists_forwarded_raises_on_absence(
        self, tmp_path: Path
    ) -> None:
        """``require_exists=True`` forwards to the resolver: genuine absence RAISES.

        Load-bearing for WP04's equivalence-matrix re-point (coord-empty /
        coord-deleted must still RAISE). A canonical handle with NO directory on
        disk and ``require_exists=True`` must surface the typed error.
        """
        with pytest.raises(StatusReadPathNotFound):
            resolve_handle_to_read_path(tmp_path, HANDLE, require_exists=True)
