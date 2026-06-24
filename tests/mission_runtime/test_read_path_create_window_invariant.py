"""WP06 / T023 — Create-window invariant (SC-005, #1718).

**The invariant (FR-005 / #1718 routing contract):**

  A mission whose primary ``meta.json`` DECLARES a ``coordination_branch`` but
  whose coordination WORKTREE HAS NOT YET BEEN CREATED ON DISK must still
  resolve to the PRIMARY checkout when read with a bare slug — even if the seam
  successfully derives a non-empty ``mid8`` from the declared identity.

  Formally: "a declared-but-unmaterialised coord + bare slug → read resolves
  PRIMARY, regardless of whether mid8 is provable."

**Why this matters (the #1718 trap):**

  The routing function to AVOID is ``resolve_status_surface_with_anchor``
  (``coordination.surface_resolver``).  When the coord worktree root is not
  yet on disk, ``resolve_status_surface_with_anchor`` composes and RETURNS
  the expected coord path anyway (it composes the expected coord path without
  checking for the directory on disk).  A read CLI that mistakenly routed through
  ``resolve_status_surface_with_anchor`` in the create-window would therefore
  return a non-existent coord path, causing every downstream status read
  (``status.events.jsonl``, ``decisions/index.json``) to fail with a
  "file not found" instead of reading the already-present primary data.

  ``resolve_handle_to_read_path`` is the CORRECT seam: its step 5 delegates to
  ``resolve_mission_read_path``, which selects the coord surface ONLY when the
  coord worktree directory EXISTS on disk.  Deriving a non-empty mid8 is
  ORTHOGONAL to the create-window→primary contract.

**Fixture design (NFR-005):**

  Primary dir name: ``<slug>-<mid8>`` (post-WP03 canonical form).  The seam
  computes the candidate primary path as ``kitty-specs/<slug>-<mid8>`` because
  ``_compose_mission_dir(slug, mid8)`` → ``<slug>-<mid8>``.  The coord worktree
  root (``.worktrees/<slug>-<mid8>-coord/``) is INTENTIONALLY ABSENT so the
  seam falls back to the primary.

  Why the primary dir name carries mid8: ``resolve_handle_to_read_path`` reads
  the bare-slug's meta from ``primary_feature_dir_for_mission(repo_root, handle)``
  = ``kitty-specs/<handle>`` (literal).  Then it derives ``mid8`` and calls
  ``resolve_mission_read_path(repo_root, handle, mid8)``.  Inside that function
  ``_compose_mission_dir(handle, mid8)`` = ``<handle>-<mid8>`` is used to
  build the primary candidate.  So the primary candidate path is
  ``kitty-specs/<bare-slug>-<mid8>/``, which must exist for a successful read.

**Mutation guard structure:**

  1. **Positive contract** — declared-but-unmaterialised coord + bare slug →
     ``resolve_handle_to_read_path`` returns the PRIMARY mission dir.
  2. **Mutation guard** — ``resolve_status_surface_with_anchor`` returns a
     non-existent (or wrong) path in the create-window, proving that
     substituting it for the correct seam would break the positive-contract test.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = [pytest.mark.fast]

# ---------------------------------------------------------------------------
# Realistic test constants (NFR-005)
# ---------------------------------------------------------------------------
_FULL_ULID: str = "01KVJPEQ3FHVK9MXW7ZB2CDNRT"
_MID8: str = _FULL_ULID[:8]                      # "01KVJPEQ"
_BARE_SLUG: str = "create-window-proof"
# Post-WP03 canonical dir name: <slug>-<mid8>
_MISSION_DIR: str = f"{_BARE_SLUG}-{_MID8}"
_COORD_BRANCH: str = f"kitty/mission-{_MISSION_DIR}"


# ---------------------------------------------------------------------------
# Fixture builder: declared-but-NOT-materialised coord topology
# ---------------------------------------------------------------------------

def _build_declared_unmaterialised_coord(repo_root: Path) -> tuple[Path, Path]:
    """Create a mission whose primary meta DECLARES a coord branch but the worktree is absent.

    The PRIMARY dir uses the BARE SLUG name (``<slug>``, not ``<slug>-<mid8>``).
    This mirrors the actual create-window: ``mission create`` writes the initial
    spec into ``kitty-specs/<slug>/``.  The coord worktree
    (``.worktrees/<slug>-<mid8>-coord/``) is materialised only on the first
    ``implement`` run, so in the window between create and implement the primary
    IS the canonical read surface.

    The seam ``resolve_handle_to_read_path(repo_root, bare_slug)`` reads:
    1. ``primary_feature_dir_for_mission(repo_root, bare_slug)`` → ``kitty-specs/<slug>``
    2. ``load_meta(primary_dir)`` → the meta with mission_id + mid8 + coordination_branch
    3. ``resolve_declared_mid8(meta, bare_slug)`` → ``_MID8`` (from meta.mid8 field)
    4. M5 fail-closed check: ``mid8 != "" and declares_coordination``
       → raises ``StatusReadPathNotFound`` (because primary declares coord) unless
       the coord worktree ROOT is absent (in which case step 5 handles it).
    5. ``resolve_mission_read_path(repo_root, bare_slug, mid8)``
       → ``_resolve_existing_for_slug`` checks coord root → ABSENT → checks
       primary candidate ``kitty-specs/<slug>-<mid8>`` → ABSENT →
       → ``_canonicalize_handle`` scans index → finds ``kitty-specs/<slug>`` dir
         but its meta slug is ``<slug>`` → priority-3 match → returns it
       → ``_resolve_existing_for_slug(repo_root, "<slug>", "")`` → primary is
         ``kitty-specs/<slug>`` → EXISTS (no coord check since mid8 reverts)

    Actually the simpler path: ``_resolve_existing_for_slug(repo_root, slug, mid8)``:
    - mid8 non-empty → compose coord candidate → absent → not returned
    - primary_candidate = ``kitty-specs/<slug>-<mid8>`` → absent
    - primary declares coord but coord root ABSENT → no fail-closed (coord worktree
      not materialised) → primary_candidate returned (even though absent)

    Then ``resolve_handle_to_read_path`` falls to ``_canonicalize_handle`` which
    finds the real dir ``kitty-specs/<slug>`` (not ``<slug>-<mid8>``) via the
    index (priority-3: slug match), then the existing bare-slug dir is returned
    directly (the backfill path in ``resolve_mission_read_path``).

    Net: ``resolved == kitty-specs/<slug>/`` (the bare-slug primary dir).

    Returns ``(primary_dir, coord_mission_path_that_does_not_exist)``.

    Layout:
      <repo_root>/
        kitty-specs/<slug>/           ← primary dir (EXISTS; bare slug name)
          meta.json                   ← declares coordination_branch + mission_id
          status.events.jsonl        ← status data lives here in the create window
        .worktrees/<slug>-<mid8>-coord/  ← DOES NOT EXIST (not yet materialised)
    """
    primary_dir = repo_root / "kitty-specs" / _BARE_SLUG
    primary_dir.mkdir(parents=True)
    meta = {
        "mission_id": _FULL_ULID,
        "mission_slug": _BARE_SLUG,
        "mid8": _MID8,
        "coordination_branch": _COORD_BRANCH,
        "mission_type": "software-dev",
    }
    (primary_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    # Status data lives in the primary during the create window.
    (primary_dir / "status.events.jsonl").write_text("", encoding="utf-8")

    # Coord worktree root is INTENTIONALLY absent.
    coord_root = repo_root / ".worktrees" / f"{_MISSION_DIR}-coord"
    coord_mission_path = coord_root / "kitty-specs" / _MISSION_DIR
    assert not coord_root.exists(), "Test setup error: coord root must not exist"

    return primary_dir, coord_mission_path


# ---------------------------------------------------------------------------
# T023 — Positive contract: bare slug + declared-unmaterialised coord → PRIMARY
# ---------------------------------------------------------------------------

class TestCreateWindowInvariant:
    """T023: declared-but-unmaterialised coord + bare slug resolves PRIMARY.

    The seam ``resolve_handle_to_read_path`` derives a non-empty mid8 from the
    declared ``mission_id`` (via ``resolve_declared_mid8`` → tier-2 ``resolve_mid8``
    — this is the WP01/WP03 improvement).  Even though mid8 is non-empty, the
    topology resolver (``resolve_mission_read_path``) MUST return the primary dir
    because the coord worktree root DOES NOT EXIST on disk.
    """

    def test_bare_slug_declared_unmaterialised_resolves_primary(
        self, tmp_path: Path
    ) -> None:
        """Core invariant: bare slug + declared-but-not-on-disk coord → PRIMARY dir."""
        from specify_cli.missions._read_path_resolver import resolve_handle_to_read_path

        primary_dir, coord_path = _build_declared_unmaterialised_coord(tmp_path)

        # The bare slug resolves to the primary because coord worktree is absent.
        # The seam reads meta from kitty-specs/<bare-slug> (which doesn't exist),
        # falls back through _canonicalize_handle scanning the index, finds
        # kitty-specs/<slug>-<mid8>/, derives mid8, then checks the coord root
        # (.worktrees/<slug>-<mid8>-coord/) — absent — so returns the primary.
        resolved = resolve_handle_to_read_path(tmp_path, _BARE_SLUG)

        # Must resolve to PRIMARY (the coord worktree is not on disk).
        assert resolved == primary_dir, (
            f"Create-window invariant violated: bare slug resolved {resolved!r} "
            f"instead of primary {primary_dir!r}. "
            f"Coord path (must NOT be returned): {coord_path!r}"
        )

        # Confirm the coord path was NOT returned.
        assert resolved != coord_path, (
            f"Seam returned the coord path {coord_path!r} even though the coord "
            f"worktree is not materialised on disk — #1718 regression."
        )

        # Confirm the coord path does not exist (structural sanity).
        assert not coord_path.exists(), "Test setup error: coord path must not exist"

    def test_mid8_is_provable_yet_primary_is_returned(
        self, tmp_path: Path
    ) -> None:
        """Provability of mid8 is ORTHOGONAL to the create-window→primary contract.

        The seam DOES derive a non-empty mid8 (mid8 lives in the primary meta).
        But it MUST still return the primary dir because the coord worktree root
        is absent.  This test makes that orthogonality explicit.
        """
        from specify_cli.missions._read_path_resolver import resolve_handle_to_read_path
        from specify_cli.coordination.surface_resolver import resolve_declared_mid8

        primary_dir, coord_path = _build_declared_unmaterialised_coord(tmp_path)

        # Step 1: confirm mid8 IS provable from the meta.
        meta = json.loads((primary_dir / "meta.json").read_text(encoding="utf-8"))
        derived_mid8 = resolve_declared_mid8(meta, _BARE_SLUG)
        assert derived_mid8 == _MID8, (
            f"Mid8 not derived from meta — test setup error. Got {derived_mid8!r}"
        )

        # Step 2: despite a provable mid8, the seam returns the PRIMARY dir
        # (not the coord path) because the coord worktree is absent on disk.
        resolved = resolve_handle_to_read_path(tmp_path, _BARE_SLUG)
        assert resolved == primary_dir, (
            f"Seam returned {resolved!r} instead of primary {primary_dir!r} "
            f"even though mid8={derived_mid8!r} is provable and coord is absent."
        )
        assert resolved.exists(), (
            f"Seam returned a non-existent path {resolved!r}; primary must exist."
        )


# ---------------------------------------------------------------------------
# T023 — Mutation guard: resolve_status_surface_with_anchor fails the contract
# ---------------------------------------------------------------------------

class TestCreateWindowMutationGuard:
    """Mutation guard: if the seam used ``resolve_status_surface_with_anchor``
    instead of ``resolve_mission_read_path``, the positive-contract test above
    would FAIL.

    ``resolve_status_surface_with_anchor`` is the historically-buggy (#1718) path:
    when the coord worktree root is not materialised, it COMPOSES and RETURNS the
    expected coord path (a non-existent path) instead of falling back to primary.
    The FR-005 contract is that the coord surface is selected ONLY when it exists.

    Encoding strategy: this test verifies that ``resolve_status_surface_with_anchor``
    behaves DIFFERENTLY from the correct seam in the create-window (either raises,
    or returns a non-existent / incorrect path).  Any assertion on the correct seam
    (``resolved == primary_dir`` and ``resolved.exists()``) would FAIL when the
    wrong function is substituted — that is the mutation guard's bite.
    """

    def test_surface_with_anchor_does_not_return_primary_in_create_window(
        self, tmp_path: Path
    ) -> None:
        """Demonstrate that ``resolve_status_surface_with_anchor`` returns a different
        result than the correct seam in the create-window.

        This is the NEGATIVE side of the mutation guard: it shows what the WRONG
        code path does, proving that substituting it for the correct seam would
        cause the positive-contract test to fail.
        """
        from specify_cli.coordination.surface_resolver import (
            resolve_status_surface_with_anchor,
        )

        primary_dir, coord_mission_path = _build_declared_unmaterialised_coord(tmp_path)

        # The correct seam's create-window contract is BOTH ``== primary_dir`` AND
        # ``.exists()``.  ``resolve_status_surface_with_anchor`` is the wrong path;
        # it must DIVERGE from that contract in one of two observable ways:
        #   (a) it RAISES (the correct seam is graceful — returns the primary), OR
        #   (b) it RETURNS a result that is NOT ``(== primary_dir AND .exists())``.
        # Both legs are POSITIVE divergence assertions — neither may pass vacuously.
        try:
            surface = resolve_status_surface_with_anchor(tmp_path, _BARE_SLUG)
        except Exception:
            # Leg (a): raising IS divergence from the graceful-primary contract.
            # This affirmatively records the wrong path — not a silent vacuous pass.
            pass
        else:
            # Leg (b): a returned result must FAIL the correct seam's contract.
            wrong_result = surface.surface_path.parent
            satisfies_correct_contract = (
                wrong_result == primary_dir and wrong_result.exists()
            )
            assert not satisfies_correct_contract, (
                f"resolve_status_surface_with_anchor unexpectedly satisfied the "
                f"correct seam's create-window contract (== primary AND exists) — "
                f"mutation guard compromised.  Got: {wrong_result!r}, "
                f"primary: {primary_dir!r}"
            )

    def test_correct_seam_returns_existing_primary(self, tmp_path: Path) -> None:
        """The CORRECT seam (``resolve_handle_to_read_path``) returns the primary
        dir, which EXISTS.  This is the assertion that would FAIL if the seam were
        replaced with ``resolve_status_surface_with_anchor``."""
        from specify_cli.missions._read_path_resolver import resolve_handle_to_read_path

        primary_dir, coord_path = _build_declared_unmaterialised_coord(tmp_path)

        resolved = resolve_handle_to_read_path(tmp_path, _BARE_SLUG)

        # Must exist (the correct seam returns the existing primary).
        assert resolved.exists(), (
            f"Seam returned a non-existent path {resolved!r} — "
            f"would indicate the coord path was composed instead of primary."
        )
        # Must equal the primary dir.
        assert resolved == primary_dir, (
            f"Seam returned {resolved!r} instead of existing primary {primary_dir!r}."
        )
        # The wrong path (coord) must NOT be returned.
        assert resolved != coord_path, (
            f"Seam returned the coord path {coord_path!r} — #1718 regression."
        )


# ---------------------------------------------------------------------------
# T025 (WP07 / NFR-001 / #1718) — Create→first-write boundary: reads resolve
# to PRIMARY; materialisation triggers only at the COMMIT boundary.
# ---------------------------------------------------------------------------


class TestCreateWindowCommitBoundaryNFR001:
    """T025: NFR-001 (#1718) — materialisation happens at the commit boundary only.

    The create-to-first-write window is defined as:
      - ``mission create`` writes initial artifacts to PRIMARY (kitty-specs/<slug>/).
      - No coord worktree exists on disk yet.
      - A read operation MUST resolve to the PRIMARY checkout.
      - A commit operation IS the commit boundary — materialisation occurs HERE,
        not at read time.

    This extension of T023 (create-window invariant) adds:
    1. **Read-resolves-primary** assertion (preserved from T023): during the create
       window, ``resolve_handle_to_read_path`` returns the primary dir (not coord).
    2. **Commit-boundary materialisation** assertion: the first commit AFTER the
       create window materialises the coord worktree; a read BEFORE the commit does
       not materialise it.

    The mutation guard (``resolve_status_surface_with_anchor`` vs the correct seam)
    is tested in ``TestCreateWindowMutationGuard`` above; the NFR-001 extension is
    orthogonal — it tests WHEN materialisation occurs, not WHICH seam is used.
    """

    def test_read_resolves_primary_before_commit_boundary(
        self, tmp_path: Path
    ) -> None:
        """NFR-001: in the create window, reads resolve to PRIMARY (materialisation not triggered).

        Layout:
          kitty-specs/<slug>/                  (exists - primary, create window)
          .worktrees/<slug>-<mid8>-coord/      (ABSENT - not yet committed to)

        The read seam must return the primary dir without creating the coord worktree.
        """
        from specify_cli.missions._read_path_resolver import resolve_handle_to_read_path

        primary_dir, coord_path = _build_declared_unmaterialised_coord(tmp_path)

        # Coord worktree must be absent BEFORE the read.
        coord_root = tmp_path / ".worktrees" / f"{_MISSION_DIR}-coord"
        assert not coord_root.exists(), "Precondition: coord worktree absent before read."

        # Read during create window.
        resolved = resolve_handle_to_read_path(tmp_path, _BARE_SLUG)

        # NFR-001 assertion 1: read returns PRIMARY (not coord).
        assert resolved == primary_dir, (
            f"NFR-001 (#1718): read in create window returned {resolved!r} "
            f"instead of primary {primary_dir!r}."
        )

        # NFR-001 assertion 2: coord worktree was NOT materialised by the read.
        assert not coord_root.exists(), (
            "NFR-001 (#1718): read operation materialised the coord worktree - "
            "materialisation must only occur at the COMMIT boundary, not at read time."
        )

    def test_materialisation_occurs_at_commit_boundary_not_read_time(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """NFR-001: commit_for_mission IS the commit boundary - materialisation occurs here.

        We use a spy on CoordinationWorkspace.resolve to confirm:
        1. Reading (resolve_handle_to_read_path) does NOT call CoordinationWorkspace.resolve.
        2. Committing (commit_for_mission) DOES call CoordinationWorkspace.resolve.
        """
        from specify_cli.missions._read_path_resolver import resolve_handle_to_read_path
        from specify_cli.coordination import workspace as ws_module
        from mission_runtime import MissionArtifactKind
        from specify_cli.coordination.commit_router import commit_for_mission
        from specify_cli.git.protection_policy import ProtectionPolicy
        from mission_runtime import CommitTarget
        from unittest.mock import patch

        primary_dir, coord_path = _build_declared_unmaterialised_coord(tmp_path)

        # Spy on CoordinationWorkspace.resolve.
        materialise_calls: list[tuple[str, ...]] = []
        _real_resolve = ws_module.CoordinationWorkspace.resolve

        def _spy_resolve(repo_root: object, slug: object, mid8: object) -> object:
            materialise_calls.append((str(repo_root), str(slug), str(mid8)))
            return _real_resolve(repo_root, slug, mid8)

        monkeypatch.setattr(
            ws_module.CoordinationWorkspace, "resolve", staticmethod(_spy_resolve)
        )
        monkeypatch.delenv("SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS", raising=False)

        # Phase 1: READ in create window - must NOT materialise.
        resolved = resolve_handle_to_read_path(tmp_path, _BARE_SLUG)
        assert resolved == primary_dir, f"Read returned {resolved!r}, expected primary."
        calls_after_read = len(materialise_calls)
        assert calls_after_read == 0, (
            f"NFR-001: CoordinationWorkspace.resolve called {calls_after_read} time(s) "
            f"during a READ in the create window - materialisation must NOT happen at read time."
        )

        # Phase 2: CREATE a spec artifact in the primary dir.
        spec_path = primary_dir / "spec.md"
        spec_path.write_text("# Spec\n\nFirst write.\n", encoding="utf-8")

        # Stub the kind-aware resolver to return COORDINATION so commit_for_mission
        # actually tries to materialise (the coord path on a protected primary). A
        # COORD kind (ANALYSIS_REPORT) is used because write-surface-coherence WP02
        # routes primary kinds straight to the primary surface (no materialisation);
        # the materialisation-at-commit-boundary invariant lives on the coord path.
        _coord_branch = f"kitty/mission-{_MISSION_DIR}"
        report_path = primary_dir / "analysis-report.md"
        report_path.write_text("# Analysis\n\nFirst write.\n", encoding="utf-8")

        with patch(
            "specify_cli.coordination.commit_router.resolve_placement_only",
            lambda _root, _slug, *, kind: CommitTarget(ref=_coord_branch),
        ), patch(
            "specify_cli.coordination.commit_router._resolve_primary_target_branch",
            lambda _root, _slug: "main",
        ), patch(
            "specify_cli.coordination.commit_router._resolve_mid8",
            lambda _root, _slug: _MID8,
        ):
            # Phase 2: COMMIT boundary - materialisation MUST occur here.
            policy = ProtectionPolicy.resolve(tmp_path)
            commit_for_mission(
                repo_root=tmp_path,
                mission_slug=_BARE_SLUG,
                files=(report_path,),
                message="analysis: first write",
                policy=policy,
                kind=MissionArtifactKind.ANALYSIS_REPORT,
            )

        calls_after_commit = len(materialise_calls)
        assert calls_after_commit > 0, (
            "NFR-001: CoordinationWorkspace.resolve was NEVER called during commit_for_mission. "
            "Materialisation must occur at the commit boundary (not at read time)."
        )
