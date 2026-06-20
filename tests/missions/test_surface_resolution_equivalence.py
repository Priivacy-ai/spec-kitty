"""Differential equivalence test — the C-004 deletion safety gate (FR-002, NFR-003).

This module feeds the **same** ``(topology, handle)`` matrix to EVERY
mission-surface resolution entry point and asserts each entry point returns an
**identical resolved directory** OR an **identical typed error** (same class AND
same ``error_code``). It is the gate that protects the C-004 strangler: no
duplicate resolver may be deleted (WP06/WP07) until the relevant matrix cells
are green — and the strict-xfail markers below turn any *premature* green
(a delete-before-equivalence) into a suite failure.

Entry points compared (read each before asserting over it):

* ``missions._read_path_resolver.resolve_mission_read_path`` (require_exists=True)
* ``coordination.surface_resolver.resolve_status_surface_with_anchor`` (``.read_dir``)
* ``status.aggregate.MissionStatus.load`` (``.read_dir`` / ``_resolve_read_dir``)
* ``mission_runtime.resolution`` boundary (ambiguous-handle translation probe)

``primary_feature_dir_for_mission`` is the FR-009 divergence companion to
``resolve_mission_read_path``; the ``coord-fresh|bare-slug`` cell is exactly the
``<slug>-<mid8>`` divergence column (the resolver is mid8-blind for a bare slug
while the surface/aggregate prefer the coord worktree).

Assertion discipline (a too-lenient assertion VOIDS the whole gate):

* dirs:   ``resolved_a.resolve() == resolved_b.resolve()`` — path equality, NOT
          "both non-None" / truthiness.
* errors: ``type(exc_a) is type(exc_b) and exc_a.error_code == exc_b.error_code``
          — same class AND same code, NOT "both raise something".
* No ``pytest.skip(...)`` anywhere in the module — a skip would hide a
  divergence. Initially-RED cells use ``@pytest.mark.xfail(strict=True, ...)``.

Cell → closing-WP map (the docstring authority WP06's DoD greps against):

============================  ====================  ======================================
Cell (topology | handle)      Today                 Closing WP / FR
============================  ====================  ======================================
no-coord | bare-slug          GREEN (agree, dir)    — (already equivalent)
no-coord | <slug>-<mid8>      GREEN (agree, dir)    — (already equivalent)
no-coord create→first-write   GREEN (agree, dir)    — (primary authoritative; WP04 T016)
coord-fresh | bare-slug       RED  (resolver mid8-  WP03 / FR-009 (unify the mid8-composing
                              blind → primary; sur-  ``<slug>-<mid8>`` read path)
                              face/agg → coord)
coord-fresh | <slug>-<mid8>   GREEN (agree, coord)  — (already equivalent)
coord-behind | bare-slug      RED  (folds into       WP03 / FR-009 (coord-behind folds into
                              coord-fresh/bare:       coord-fresh; same mid8-blind bare-slug
                              resolver mid8-blind →   divergence — unify the read path)
                              primary; surface/agg
                              → coord)
coord-behind | <slug>-<mid8>  GREEN (agree, coord —  — (folds into coord-fresh; already
                              folds into coord-fresh) equivalent — live-probed 2026-06-19)
coord-empty | bare-slug       RED  (resolver →      WP06 / FR-006 (coord-empty hard-fail)
                              primary; surface →
                              SRPNF; agg → Coord-
                              AuthorityUnavailable)
coord-empty | <slug>-<mid8>   RED  (resolver+sur →  WP06 / FR-006 (+ aggregate error-type
                              SRPNF; agg → Coord-    convergence)
                              AuthorityUnavailable)
coord-deleted | bare-slug     RED  (resolver →      WP06 / FR-006 + FR-005 (coord-deleted
                              primary; surface →     hard-fail; typed-error convergence)
                              CoordinationBranch-
                              Deleted; agg → Coord-
                              AuthorityUnavailable)
coord-deleted | <slug>-<mid8> RED  (same as above)  WP06 / FR-006 + FR-005
ambiguous-mid8                GREEN (agree, MISSION  — (already equivalent across resolver,
                              _AMBIGUOUS_SELECTOR)   surface, aggregate)
ambiguous-mid8 @ runtime      GREEN (WP05 landed:    — (closed by WP05/FR-005; xfail drained at
boundary                      ActionContextError,    the WP06 collapse, 2026-06-20)
                              MISSION_AMBIGUOUS_
                              SELECTOR preserved)
============================  ====================  ======================================

NOTE (WP06 drain, 2026-06-20): the "Closing WP / FR" column above records the
ORIGINAL plan. The actual WP06 outcome for the six coord-empty/coord-deleted/
coord-fresh-bare/coord-behind-bare RED cells is a **documented out-of-scope
allowlist** (NOT a literal drain) — see the ``_XFAIL_*_OUT_OF_SCOPE`` constants
and the "WP06 collapse gate (drain outcome)" paragraph below for the authoritative,
per-class rationale.

WP06 collapse gate (drain outcome, 2026-06-20): WP06 collapsed the surface to
the sole authority, migrated the #1900 status_transition predicates, and shipped
the FR-006 coord-empty two-path hard-fail. It drained the cells that genuinely
close at the collapse (the WP05 ``runtime-boundary`` XPASS — WP05 landed). The
SIX remaining RED cells are **documented out-of-scope strict-xfails**, NOT a
blanket drain — see ``_XFAIL_READPATH_MID8_OUT_OF_SCOPE`` (the four #1918 bare-slug
read_path mid8-blindness cells), ``_XFAIL_COORD_EMPTY_SEAM_OUT_OF_SCOPE`` (the
coord-empty/slug-mid8 multi-seam split: a WP06-introduced surface/read_path
subclass split at a stable error_code, plus the WP04 ``CoordAuthorityUnavailable``
no-error_code aggregate seam), and ``_XFAIL_COORD_DELETED_SEAM_OUT_OF_SCOPE`` (the
coord-deleted/slug-mid8 multi-way divergence: read_path → primary directory, surface
→ ``CoordinationBranchDeleted``, aggregate → ``CoordAuthorityUnavailable``). Each
remaining
``xfail`` therefore names exactly why the collapse does not close it and where it
must close — the allowlist + rationale is the auditable record, replacing the
``rg "xfail" → 0`` literal drain for these two genuinely-deferred classes.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from specify_cli.coordination.surface_resolver import (
    resolve_status_surface_with_anchor,
)
from specify_cli.missions._read_path_resolver import resolve_mission_read_path
from specify_cli.status.aggregate import MissionStatus

pytestmark = pytest.mark.git_repo

# Production-shaped identity: a real 26-char ULID (Mission Identity Model 083+),
# NOT a toy slug. ``mid8`` is the first 8 chars, the canonical disambiguator.
MISSION_ID = "01KTDVHZKGCHCW6HQ4V577PNES"
MID8 = MISSION_ID[:8]
MISSION_SLUG = "single-surface-resolver"
SLUG_WITH_MID8 = f"{MISSION_SLUG}-{MID8}"
COORD_BRANCH = f"kitty/mission-{SLUG_WITH_MID8}"

# Two missions that collide on the same mid8 prefix (the ambiguous-selector row).
_AMBIG_MID8 = "01KTAMBG"
_AMBIG_ID_A = _AMBIG_MID8 + "0AAAAAAAAAAAAAAAAA"  # 26-char ULID-shaped
_AMBIG_ID_B = _AMBIG_MID8 + "0BBBBBBBBBBBBBBBBB"


# ---------------------------------------------------------------------------
# Outcome: the normalized differential observation (dir-or-typed-error)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Outcome:
    """A single entry point's observed result for one matrix cell.

    Exactly one of ``directory`` / (``error_type``, ``error_code``) is set. The
    equality used by the gate is the spelled-out shape from the module docstring
    — NEVER truthiness:

    * dirs agree iff their ``Path.resolve()`` values are equal;
    * errors agree iff the exception class is identical AND the ``error_code``
      string is identical.
    """

    directory: Path | None
    error_type: type[BaseException] | None
    error_code: str | None

    @classmethod
    def from_dir(cls, directory: Path) -> Outcome:
        return cls(directory=directory.resolve(), error_type=None, error_code=None)

    @classmethod
    def from_error(cls, exc: BaseException) -> Outcome:
        # ``error_code`` is the stable routing key the typed errors carry
        # (STATUS_READ_PATH_NOT_FOUND, MISSION_AMBIGUOUS_SELECTOR, ...). Errors
        # without one (e.g. CoordAuthorityUnavailable today) compare on type +
        # the sentinel below, so a type-only divergence is still a divergence.
        code = getattr(exc, "error_code", None)
        return cls(
            directory=None,
            error_type=type(exc),
            error_code=str(code) if code is not None else None,
        )

    @property
    def is_dir(self) -> bool:
        return self.directory is not None


def _observe(resolve: Callable[[], Path]) -> Outcome:
    """Run one entry point, capturing either its resolved dir or its exception.

    Any exception is captured (never swallowed): the gate's job is to compare the
    EXACT typed error across entry points, so the broad capture is intentional
    and the captured exception's type + ``error_code`` are asserted on.
    """
    try:
        resolved = resolve()
    except BaseException as exc:  # noqa: BLE001 — capture-and-compare is the gate
        return Outcome.from_error(exc)
    return Outcome.from_dir(resolved)


def _assert_equivalent(left: Outcome, right: Outcome, *, lhs: str, rhs: str) -> None:
    """Assert two entry points agree using the EXACT gate shapes.

    A too-lenient assertion (truthiness / "both non-None") would void the entire
    C-004 deletion gate, so the comparison is spelled out:

    * both dirs → ``Path.resolve()`` equality;
    * both errors → identical class AND identical ``error_code``;
    * one dir + one error → an unconditional divergence (the gate fires).
    """
    if left.is_dir and right.is_dir:
        assert left.directory == right.directory, (
            f"{lhs} resolved {left.directory} but {rhs} resolved {right.directory} "
            "— directory divergence (C-004 gate)"
        )
        return
    if not left.is_dir and not right.is_dir:
        assert left.error_type is right.error_type and left.error_code == right.error_code, (
            f"{lhs} raised {left.error_type}/{left.error_code} but {rhs} raised "
            f"{right.error_type}/{right.error_code} — typed-error divergence (C-004 gate)"
        )
        return
    raise AssertionError(
        f"{lhs} produced {'dir' if left.is_dir else 'error'} "
        f"({left.directory or f'{left.error_type}/{left.error_code}'}) but {rhs} "
        f"produced {'dir' if right.is_dir else 'error'} "
        f"({right.directory or f'{right.error_type}/{right.error_code}'}) "
        "— dir-vs-error divergence (C-004 gate)"
    )


# ---------------------------------------------------------------------------
# Fixtures — realistic on-disk shapes (real git repo, real worktree layout)
# ---------------------------------------------------------------------------


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(repo_root: Path) -> None:
    """Initialise a real git repo with one commit (the worktree registry needs it)."""
    _git(repo_root, "init", "-q")
    _git(repo_root, "config", "user.email", "gate@example.test")
    _git(repo_root, "config", "user.name", "Equivalence Gate")
    _git(repo_root, "commit", "--allow-empty", "-qm", "init")


def _write_meta(feature_dir: Path, **fields: object) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(json.dumps(fields), encoding="utf-8")


def _coord_dir_slug(slug: str) -> str:
    """The on-disk coord dir slug: always carries the mid8 (post-WP03 grammar)."""
    return slug if slug.endswith(MID8) else SLUG_WITH_MID8


def _build_topology(repo_root: Path, *, topology: str, slug: str) -> None:
    """Materialise the realistic on-disk shape for one (topology, handle) cell.

    Layouts (per data-model.md):

    * ``no-coord``      — primary ``kitty-specs/<slug>/`` with meta, no coord branch.
    * ``coord-fresh``   — coord branch in git + ``.worktrees/<slug>-<mid8>-coord/``
      worktree dir populated with the mission dir + meta.
    * ``coord-behind``  — same populated coord worktree as ``coord-fresh``, but the
      primary checkout is ahead/diverged (an extra committed primary state). Per
      data-model.md the canonical cascade still prefers the coord surface, so the
      resolution outcome folds into ``coord-fresh`` (probed live, 2026-06-19).
    * ``coord-empty``   — coord branch in git + coord worktree root materialised but
      EMPTY (no mission dir).
    * ``coord-deleted`` — primary declares ``coordination_branch`` but the branch was
      never created (deleted from git) and no coord worktree exists.
    """
    _init_repo(repo_root)
    primary_fields: dict[str, object] = {"mission_id": MISSION_ID}
    if topology != "no-coord":
        primary_fields["coordination_branch"] = COORD_BRANCH
    _write_meta(repo_root / "kitty-specs" / slug, **primary_fields)

    coord_slug = _coord_dir_slug(slug)
    coord_root = repo_root / ".worktrees" / f"{coord_slug}-coord"
    coord_feature_dir = coord_root / "kitty-specs" / coord_slug

    if topology == "coord-fresh":
        _git(repo_root, "branch", COORD_BRANCH)
        _write_meta(coord_feature_dir, **primary_fields)
    elif topology == "coord-behind":
        # Same populated coord worktree as coord-fresh, but the PRIMARY checkout is
        # ahead/diverged: commit the primary state so it advances past the coord
        # branch point. The canonical cascade still prefers the coord surface, so
        # this folds into coord-fresh (probed live 2026-06-19).
        _git(repo_root, "branch", COORD_BRANCH)
        _write_meta(coord_feature_dir, **primary_fields)
        _git(repo_root, "add", "-A")
        _git(repo_root, "commit", "-qm", "primary ahead of coord (diverged)")
    elif topology == "coord-empty":
        _git(repo_root, "branch", COORD_BRANCH)
        coord_root.mkdir(parents=True)  # materialised, no mission dir
    elif topology == "coord-deleted":
        pass  # branch never created → declared-but-gone; no coord worktree


# ---------------------------------------------------------------------------
# Entry-point adapters — one closure per resolver, identical (slug, mid8) input
# ---------------------------------------------------------------------------


def _entry_points(repo_root: Path, slug: str, mid8: str) -> dict[str, Callable[[], Path]]:
    """Return the named resolution entry points to compare for one cell."""
    return {
        "resolve_mission_read_path": lambda: resolve_mission_read_path(
            repo_root, slug, mid8, require_exists=True
        ),
        "resolve_status_surface_with_anchor": lambda: (
            resolve_status_surface_with_anchor(repo_root, slug).read_dir
        ),
        "MissionStatus.load": lambda: MissionStatus.load(repo_root, slug).read_dir,
    }


def _observe_all(repo_root: Path, slug: str, mid8: str) -> dict[str, Outcome]:
    return {name: _observe(fn) for name, fn in _entry_points(repo_root, slug, mid8).items()}


# ---------------------------------------------------------------------------
# T005 / T007 — the (topology × handle) matrix
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# WP06 documented out-of-scope divergence reasons (the T026 allowlist).
# ---------------------------------------------------------------------------
#
# WP06 collapsed the surface resolver to the sole selection authority, migrated
# the #1900 status_transition predicates, and implemented the FR-006 coord-empty
# two-path hard-fail. Two divergence classes remain RED and are EXPLICITLY
# out of WP06's owned scope (`coordination/surface_resolver.py`,
# `coordination/status_transition.py`) — they are documented strict-xfails, NOT a
# blanket ``rg xfail → 0`` drain. Each names exactly why the collapse does not
# close it and where it must close.
#
# (1) ``resolve_mission_read_path`` is mid8-BLIND for a bare slug: it derives
#     mid8 from the slug (empty for a bare slug), so it cannot reach the coord
#     surface a bare ``--mission <slug>`` names. Closing this needs the #1918
#     ``resolve_declared_mid8`` / ``_mid8_from_primary_meta`` cascade *inside
#     read_path* (read primary meta → derive mid8). That is OUT OF SCOPE (spec
#     #1918): the surface already derives mid8 via its own cascade, but read_path
#     CANNOT simply route through the surface — read_path's #1718 create-window
#     contract (``test_read_path_resolver_transitional``: declared-but-
#     unmaterialized coord → PRIMARY) differs from the surface's (composed coord
#     path), so a blind re-route would regress #1718. Affects the bare-slug
#     coord-* cells.
#
# (2) The aggregate keeps its ``CoordAuthorityUnavailable`` single-seam contract
#     (WP04/FR-015–FR-023): ``MissionStatus.load`` translates the surface's
#     fail-closed signal to ONE boundary exception for EVERY handle form — a
#     contract separately tested in 3 non-owned files
#     (``test_aggregate_surface_resolution``,
#     ``test_mission_status_aggregate``, ``test_handle_equivalence_matrix``),
#     exported as public API, and caught by the ``agent status`` CLI. The matrix
#     compares ``type(a) is type(b)`` (an assertion WP06 may not weaken — only
#     xfail markers are editable here), so the aggregate's distinct type cannot
#     converge without regressing WP04's boundary or editing the gate body. OUT
#     OF SCOPE for WP06; tracked for a follow-on that owns the aggregate seam.
#     Affects the slug-mid8 coord-empty/coord-deleted cells (where read_path +
#     surface already agree on the error_code and ONLY the aggregate diverges).
#
# FR-006 (the coord-empty two-path message) IS delivered by WP06 in the surface
# (``CoordinationWorktreeEmpty``) and mutation-verified in
# ``tests/coordination/test_surface_resolver_collapse.py`` — independent of this
# matrix's type-identity gate.
_XFAIL_READPATH_MID8_OUT_OF_SCOPE = (
    "out-of-scope (#1918): resolve_mission_read_path is mid8-blind for a bare "
    "slug → resolves primary while surface/aggregate derive mid8 from meta and "
    "reach coord. Closing needs the #1918 resolve_declared_mid8 cascade inside "
    "read_path (a blind route-through would regress the #1718 create-window "
    "contract). Documented WP06 allowlist; NOT drained."
)
# coord-empty/slug-mid8 — observed (2026-06-20, all three entry points run live):
#   resolve_mission_read_path          -> StatusReadPathNotFound    / STATUS_READ_PATH_NOT_FOUND
#   resolve_status_surface_with_anchor -> CoordinationWorktreeEmpty / STATUS_READ_PATH_NOT_FOUND
#   MissionStatus.load                 -> CoordAuthorityUnavailable / None
_XFAIL_COORD_EMPTY_SEAM_OUT_OF_SCOPE = (
    "out-of-scope multi-seam (coord-empty/slug-mid8): surface raises the WP06 "
    "CoordinationWorktreeEmpty carve-out (code STATUS_READ_PATH_NOT_FOUND) while "
    "read_path raises bare StatusReadPathNotFound — SAME error_code, DIFFERENT "
    "class: a WP06-introduced subclass split that the type()-is gate flags, "
    "trading exact type identity for a richer FR-006 two-path diagnostic at a "
    "stable error_code. MissionStatus.load (aggregate) raises "
    "CoordAuthorityUnavailable, which carries NO error_code — WP04's approved "
    "public single-seam contract (CLI + 3 non-owned tests), un-editable here. "
    "Class convergence (FR-005) is not in WP06's requirement_refs. See ADR "
    "2026-06-19-1 §'Known scope boundary'. Documented WP06 allowlist; NOT drained."
)
# coord-deleted/slug-mid8 — observed (2026-06-20, all three entry points run live):
#   resolve_mission_read_path          -> <PRIMARY DIRECTORY>       / (dir, no error)
#   resolve_status_surface_with_anchor -> CoordinationBranchDeleted / COORDINATION_BRANCH_DELETED
#   MissionStatus.load                 -> CoordAuthorityUnavailable / None
_XFAIL_COORD_DELETED_SEAM_OUT_OF_SCOPE = (
    "out-of-scope multi-way divergence (coord-deleted/slug-mid8): read_path "
    "resolves to PRIMARY (a directory, NOT an error) — the coord-deleted "
    "read_path gap needs the #1918 mid8 cascade / FR-005 typed-error convergence "
    "(neither in WP06's requirement_refs; a blind route-through the surface would "
    "regress the #1718 create-window contract). surface raises "
    "CoordinationBranchDeleted (COORDINATION_BRANCH_DELETED); aggregate raises "
    "CoordAuthorityUnavailable (no error_code, WP04's approved single-seam "
    "contract, un-editable here). NOT an aggregate-only divergence. See ADR "
    "2026-06-19-1 §'Known scope boundary'. Documented WP06 allowlist; NOT drained."
)

# (test_id, topology, slug, mid8, xfail_reason | None). ``xfail_reason is None``
# means the cell is expected GREEN today (all entry points agree); a non-None
# reason marks an initially-RED divergence and names the WP/FR that closes it.
_MATRIX: list[tuple[str, str, str, str, str | None]] = [
    ("no-coord/bare", "no-coord", MISSION_SLUG, "", None),
    ("no-coord/slug-mid8", "no-coord", SLUG_WITH_MID8, MID8, None),
    (
        "coord-fresh/bare",
        "coord-fresh",
        MISSION_SLUG,
        "",
        _XFAIL_READPATH_MID8_OUT_OF_SCOPE,
    ),
    ("coord-fresh/slug-mid8", "coord-fresh", SLUG_WITH_MID8, MID8, None),
    (
        "coord-behind/bare",
        "coord-behind",
        MISSION_SLUG,
        "",
        _XFAIL_READPATH_MID8_OUT_OF_SCOPE,
    ),
    ("coord-behind/slug-mid8", "coord-behind", SLUG_WITH_MID8, MID8, None),
    (
        "coord-empty/bare",
        "coord-empty",
        MISSION_SLUG,
        "",
        # Two independent out-of-scope divergences in this cell: read_path is
        # mid8-blind for a bare slug (the #1918 cascade), AND the aggregate keeps
        # its CoordAuthorityUnavailable single-seam contract.
        _XFAIL_READPATH_MID8_OUT_OF_SCOPE,
    ),
    (
        "coord-empty/slug-mid8",
        "coord-empty",
        SLUG_WITH_MID8,
        MID8,
        _XFAIL_COORD_EMPTY_SEAM_OUT_OF_SCOPE,
    ),
    (
        "coord-deleted/bare",
        "coord-deleted",
        MISSION_SLUG,
        "",
        _XFAIL_READPATH_MID8_OUT_OF_SCOPE,
    ),
    (
        "coord-deleted/slug-mid8",
        "coord-deleted",
        SLUG_WITH_MID8,
        MID8,
        _XFAIL_COORD_DELETED_SEAM_OUT_OF_SCOPE,
    ),
]


def _apply_xfail(
    params: list[tuple[str, str, str, str, str | None]],
) -> list[object]:
    """Wrap each matrix row in ``pytest.param`` with strict-xfail on RED cells.

    ``strict=True`` is mandatory: a cell marked xfail that *unexpectedly passes*
    (XPASS) FAILS the suite — catching a premature green / a delete-before-
    equivalence regression (the gate's whole point).
    """
    cases: list[object] = []
    for test_id, topology, slug, mid8, xfail_reason in params:
        marks = (
            (pytest.mark.xfail(strict=True, reason=xfail_reason),)
            if xfail_reason is not None
            else ()
        )
        cases.append(
            pytest.param(topology, slug, mid8, id=test_id, marks=marks)
        )
    return cases


@pytest.mark.parametrize(("topology", "slug", "mid8"), _apply_xfail(_MATRIX))
def test_entry_points_agree_per_cell(
    tmp_path: Path, topology: str, slug: str, mid8: str
) -> None:
    """T006: every entry point agrees on the dir OR the typed error for the cell.

    Asserts the exact gate shapes via :func:`_assert_equivalent`: dir equality is
    ``Path.resolve()`` equality; error equality is identical class AND identical
    ``error_code``. Pairwise against the surface resolver (the canonical selection
    authority per data-model.md), so a single divergent entry point fails the cell.
    """
    _build_topology(tmp_path, topology=topology, slug=slug)
    outcomes = _observe_all(tmp_path, slug, mid8)

    canonical_name = "resolve_status_surface_with_anchor"
    canonical = outcomes[canonical_name]
    for name, observed in outcomes.items():
        if name == canonical_name:
            continue
        _assert_equivalent(canonical, observed, lhs=canonical_name, rhs=name)


# ---------------------------------------------------------------------------
# T007 — ambiguous-mid8 handle class (no silent first-match, FR-008)
# ---------------------------------------------------------------------------


def _build_ambiguous(repo_root: Path) -> None:
    """Two missions sharing a mid8 prefix → an ambiguous bare-mid8 handle."""
    _init_repo(repo_root)
    _write_meta(repo_root / "kitty-specs" / "alpha-surface", mission_id=_AMBIG_ID_A)
    _write_meta(repo_root / "kitty-specs" / "beta-surface", mission_id=_AMBIG_ID_B)


def test_ambiguous_mid8_handle_agrees(tmp_path: Path) -> None:
    """T007: a bare ambiguous mid8 raises the SAME typed error everywhere.

    FR-008 — no silent first-match. The resolver, surface, and aggregate must all
    raise ``MissionSelectorAmbiguous`` (``error_code == MISSION_AMBIGUOUS_SELECTOR``);
    a single entry point that silently picks a candidate is a divergence.
    """
    _build_ambiguous(tmp_path)
    outcomes = _observe_all(tmp_path, _AMBIG_MID8, "")

    canonical_name = "resolve_status_surface_with_anchor"
    canonical = outcomes[canonical_name]
    # The handle is genuinely ambiguous: the canonical authority MUST error.
    assert not canonical.is_dir, (
        "ambiguous mid8 must not resolve to a directory (FR-008 no silent first-match)"
    )
    assert canonical.error_code == "MISSION_AMBIGUOUS_SELECTOR"
    for name, observed in outcomes.items():
        if name == canonical_name:
            continue
        _assert_equivalent(canonical, observed, lhs=canonical_name, rhs=name)


# ---------------------------------------------------------------------------
# T007 — no-coord create→first-write window (→ primary, NOT a hard-fail)
# ---------------------------------------------------------------------------


def test_create_first_write_window_resolves_primary(tmp_path: Path) -> None:
    """T007: the create→first-write window resolves to PRIMARY, not a hard-fail.

    Distinct from ``coord-empty`` (WP04 T016 contract): primary has the spec dir +
    meta but NO ``coordination_branch`` declaration yet, so the primary checkout is
    authoritative and every entry point agrees on the primary dir. This must NOT be
    confused with the coord-empty hard-fail — a regression that hard-failed here
    would break first-write.
    """
    _init_repo(tmp_path)
    _write_meta(tmp_path / "kitty-specs" / SLUG_WITH_MID8, mission_id=MISSION_ID)
    outcomes = _observe_all(tmp_path, SLUG_WITH_MID8, MID8)

    canonical_name = "resolve_status_surface_with_anchor"
    canonical = outcomes[canonical_name]
    expected_primary = (tmp_path / "kitty-specs" / SLUG_WITH_MID8).resolve()
    assert canonical.directory == expected_primary, (
        "create→first-write window must resolve to the primary checkout (WP04 T016)"
    )
    for name, observed in outcomes.items():
        if name == canonical_name:
            continue
        _assert_equivalent(canonical, observed, lhs=canonical_name, rhs=name)


# ---------------------------------------------------------------------------
# T007 — mission_runtime boundary: typed-error preservation (FR-005)
# ---------------------------------------------------------------------------


def test_runtime_boundary_translates_ambiguous_selector(tmp_path: Path) -> None:
    """T007: the mission_runtime boundary surfaces a translated typed error.

    FR-005 — typed errors must survive caller flattening. The
    ``mission_runtime.resolution`` boundary catches ``StatusReadPathNotFound`` and
    re-raises ``ActionContextError`` (preserving the code), AND (since WP05/FR-005,
    merged into this lane) also translates ``MissionSelectorAmbiguous`` →
    ``ActionContextError`` preserving ``MISSION_AMBIGUOUS_SELECTOR``. The former
    strict-xfail (WP05 closer) is drained here at the WP06 collapse: WP05 landed,
    so the cell is GREEN.
    """
    from mission_runtime.resolution import ActionContextError, resolve_placement_only

    _build_ambiguous(tmp_path)
    with pytest.raises(ActionContextError) as excinfo:
        resolve_placement_only(tmp_path, _AMBIG_MID8)
    # The translated boundary error must preserve the routing code (FR-005).
    assert excinfo.value.code == "MISSION_AMBIGUOUS_SELECTOR"
