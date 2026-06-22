"""Differential equivalence test — the C-004 deletion safety gate (FR-002, NFR-003).

This module feeds the **same** ``(topology, handle)`` matrix to EVERY
mission-surface resolution entry point and asserts each entry point returns an
**identical resolved directory** OR an **identical typed error** (same class AND
same ``error_code``). It is the gate that protects the C-004 strangler: no
duplicate resolver may be deleted (WP06/WP07) until the relevant matrix cells
are green — and the strict-xfail markers below turn any *premature* green
(a delete-before-equivalence) into a suite failure.

Entry points compared (read each before asserting over it):

* ``missions._read_path_resolver.resolve_handle_to_read_path`` (``require_exists=True``)
  — the WP04 re-point: ``_entry_points`` calls ``resolve_handle_to_read_path``
  (the mid8-deriving seam) under the ``"resolve_mission_read_path"`` cell label,
  NOT the mid8-blind ``resolve_mission_read_path`` primitive.  The
  ``require_exists=True`` contract makes a missing surface raise rather than
  return a composed-but-absent path — do NOT "correct" this leg back to the
  primitive, which would silently un-flip the matrix cells.
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
coord-empty | bare-slug       GREEN (WP04 Option B:  — (drained by WP04 / FR-003; all legs
                              all → primary +        agree on primary; read_path is mid8-
                              loud warning)          blind for the bare slug → primary)
coord-empty | <slug>-<mid8>   RED  (surface+agg →    WP05 / FR-004 (read-path fold under
                              primary; read_path →   require_exists=True closes the last
                              SRPNF fail-closed)      leg — see the xfail reason)
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

NOTE (2026-06-21): the "Closing WP / FR" column above records the ORIGINAL plan
(prior-mission WP06 framing). The authoritative, current per-cell disposition is
the ``_XFAIL_*_OUT_OF_SCOPE`` constants plus the "WP04 coord-empty Option B"
paragraph below.

WP04 coord-empty Option B (01KVN754, 2026-06-21): WP04 applied the operator-
decided Option B in the canonical surface — a materialized-but-empty coordination
worktree no longer raises; ``resolve_status_surface_with_anchor`` returns the
PRIMARY checkout and emits a loud ``logging.WARNING``. The aggregate inherits
primary with no code change. This drains ``coord-empty/bare`` (all three legs
agree on primary: the bare-slug read_path leg is mid8-blind, so it also resolves
primary). ``coord-empty/slug-mid8`` does NOT fully drain in WP04: the read_path
leg (``resolve_handle_to_read_path``, ``require_exists=True``) derives mid8,
probes the EMPTY coord worktree, and STILL fails closed with
``StatusReadPathNotFound`` (the #1718 stale-surface guard in WP01-owned
``missions/_read_path_resolver.py`` — WP01 deliberately forwards
``require_exists`` so that raise is load-bearing). That cell carries
``_XFAIL_COORD_EMPTY_SEAM_OUT_OF_SCOPE`` and closes in WP05 when the read-path
leg adopts the same ``probe_coord_state`` fold under ``require_exists=True``.

The remaining RED cells are **documented out-of-scope strict-xfails**, NOT a
blanket drain — see ``_XFAIL_COORD_EMPTY_SEAM_OUT_OF_SCOPE`` (the coord-empty/
slug-mid8 read-path leg, above; closes in WP05) and
``_XFAIL_COORD_DELETED_SEAM_OUT_OF_SCOPE`` (the coord-deleted/slug-mid8 multi-way
divergence: read_path → primary directory, surface → ``CoordinationBranchDeleted``,
aggregate → ``CoordAuthorityUnavailable``; closes in WP05). The
``coord-*/bare`` aggregate cells carry
``_XFAIL_BARE_AGGREGATE_COORD_AUTHORITY_OUT_OF_SCOPE`` (only ``coord-deleted/bare``
still references it after WP04; WP05 deletes the shared constant last). Each
remaining ``xfail`` names exactly why the collapse does not close it and where it
must close — the allowlist + rationale is the auditable record.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from mission_runtime import MissionTopology, classify_topology
from specify_cli.coordination.surface_resolver import (
    resolve_status_surface_with_anchor,
)
from specify_cli.missions._read_path_resolver import (
    read_primary_meta,
    resolve_handle_to_read_path,
    stored_topology_from_meta,
)
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


def _stored_topology(repo_root: Path, slug: str) -> MissionTopology:
    """Read the WP02 **stored** topology the read-path boundary consumes.

    The surface-resolver leg (WP03-owned) takes ``topology`` as an explicit
    argument; the read-path leg reads it from ``primary_meta`` internally. To prove
    cross-leg CONVERGENCE the test must feed the surface leg the SAME stored value
    the read path uses — so it reads it here via the canonical extractor
    (:func:`stored_topology_from_meta`) from the primary meta, mirroring the
    boundary read (FR-010b).
    """
    primary_meta, _ = read_primary_meta(repo_root, slug)
    stored = stored_topology_from_meta(primary_meta)
    # Un-backfilled fixtures fall back to the value-classification the boundary uses.
    if stored is not None:
        return stored
    raw_branch = primary_meta.get("coordination_branch")
    branch = str(raw_branch) if isinstance(raw_branch, str) and raw_branch else None
    return classify_topology(branch, has_lanes=False)


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
    * ``flattened-stale-coord`` — the #2062 structural repro (quickstart R1 /
      spec.md FR-005). The mission was flattened mid-flight: the primary
      ``meta.json`` carries the WP02 **stored** ``topology: single_branch`` + a
      ``flattened: true`` provenance flag and NO ``coordination_branch`` (per the
      spec's R1 model), yet a MATERIALIZED-but-stale
      ``.worktrees/<slug>-<mid8>-coord/`` mission dir lingers on disk with a
      DIVERGENT (planned) status. The STORED topology drives every read leg to
      PRIMARY — the husk is structurally not consulted, so a stale ``-coord`` dir
      cannot re-open #2062. The on-disk primary dir always carries the composed
      ``<slug>-<mid8>`` name so the bare-human-slug handle resolves through
      :func:`resolve_bare_modern_mission_dir_name` (FR-004 bare-slug fold).
    """
    _init_repo(repo_root)
    primary_fields: dict[str, object] = {"mission_id": MISSION_ID}
    if topology not in ("no-coord", "flattened-stale-coord"):
        primary_fields["coordination_branch"] = COORD_BRANCH

    if topology == "flattened-stale-coord":
        # The primary dir ALWAYS carries the composed name so every handle form
        # (composed / bare-mid8 / ULID / bare-human-slug) resolves the same dir.
        composed_primary = repo_root / "kitty-specs" / SLUG_WITH_MID8
        _write_meta(
            composed_primary,
            mission_id=MISSION_ID,
            topology=MissionTopology.SINGLE_BRANCH.value,
            flattened=True,
        )
        (composed_primary / "status.events.jsonl").write_text(
            '{"wp_id":"WP01","to_lane":"approved"}\n', encoding="utf-8"
        )
        # Stale husk: a REAL registered ``-coord`` worktree carrying its OWN
        # ``meta.json`` (EVERY ``git worktree add`` checkout has one) + a DIVERGENT
        # (planned) status. The husk's meta is the detail that fires the surface
        # resolver's ``.worktrees`` short-circuit; OMITTING it (the earlier fixture)
        # silently masked the #2062 leak so the gate could never catch it (WP08
        # debbie BLOCKER). A real ``git worktree add`` registers the worktree, so the
        # registry-authority legs see it as a genuine coord worktree, not a husk
        # ``UNREGISTERED`` shape — proving the STORED topology (not on-disk shape) is
        # what re-anchors every leg to PRIMARY.
        coord_root = repo_root / ".worktrees" / f"{SLUG_WITH_MID8}-coord"
        _git(repo_root, "worktree", "add", "-q", "-b", COORD_BRANCH, str(coord_root))
        husk = coord_root / "kitty-specs" / SLUG_WITH_MID8
        husk.mkdir(parents=True, exist_ok=True)
        _write_meta(husk, mission_id=MISSION_ID)
        (husk / "status.events.jsonl").write_text(
            '{"wp_id":"WP01","to_lane":"planned"}\n', encoding="utf-8"
        )
        return

    coord_slug = _coord_dir_slug(slug)
    coord_root = repo_root / ".worktrees" / f"{coord_slug}-coord"
    coord_feature_dir = coord_root / "kitty-specs" / coord_slug

    _write_meta(repo_root / "kitty-specs" / slug, **primary_fields)

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
    """Return the named resolution entry points to compare for one cell.

    The ``resolve_status_surface_with_anchor`` leg is fed the SAME WP02 stored
    topology the read-path leg reads internally (FR-010b cross-leg convergence):
    the surface resolver (WP03-owned) decides the PRIMARY-vs-coordination shape
    from the stored value, so threading it here proves both legs converge on
    PRIMARY for a flattened-stale-coord mission rather than diverging on the husk.
    """
    return {
        "resolve_mission_read_path": lambda: resolve_handle_to_read_path(
            repo_root, slug, require_exists=True
        ),
        "resolve_status_surface_with_anchor": lambda: (
            resolve_status_surface_with_anchor(
                repo_root, slug, _stored_topology(repo_root, slug)
            ).read_dir
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
#     surface a bare ``--mission <slug>`` names. Closing this needs the #2046
#     ``resolve_declared_mid8`` / ``_mid8_from_primary_meta`` cascade *inside
#     read_path* (read primary meta → derive mid8). That is OUT OF SCOPE (spec
#     #2046): the surface already derives mid8 via its own cascade, but read_path
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
# WP05 (01KVN754, 2026-06-21) — the final convergence drains the last three RED
# cells to 13/0 (terminal). The coord-empty/slug-mid8 read-path leg adopts WP01's
# ``probe_coord_state`` under ``require_exists=True`` (returns PRIMARY for EMPTY,
# matching the surface's Option B), and BOTH coord-deleted cells converge on
# ``CoordinationBranchDeleted`` / ``COORDINATION_BRANCH_DELETED`` across read_path,
# surface, AND aggregate (the aggregate now propagates the deleted-branch type
# verbatim via a more-specific ``except`` ahead of the SRPNF re-wrap). The three
# ``_XFAIL_*_OUT_OF_SCOPE`` constants that documented those divergences are deleted
# with their cells — no RED cell remains, so no out-of-scope allowlist is needed.

# (test_id, topology, slug, mid8, xfail_reason | None). ``xfail_reason is None``
# means the cell is expected GREEN today (all entry points agree); a non-None
# reason marks an initially-RED divergence and names the WP/FR that closes it.
_MATRIX: list[tuple[str, str, str, str, str | None]] = [
    ("no-coord/bare", "no-coord", MISSION_SLUG, "", None),
    ("no-coord/slug-mid8", "no-coord", SLUG_WITH_MID8, MID8, None),
    ("coord-fresh/bare", "coord-fresh", MISSION_SLUG, "", None),
    ("coord-fresh/slug-mid8", "coord-fresh", SLUG_WITH_MID8, MID8, None),
    ("coord-behind/bare", "coord-behind", MISSION_SLUG, "", None),
    ("coord-behind/slug-mid8", "coord-behind", SLUG_WITH_MID8, MID8, None),
    (
        "coord-empty/bare",
        "coord-empty",
        MISSION_SLUG,
        "",
        # WP04 (Option B, 01KVN754): coord-empty no longer hard-fails — the surface
        # returns PRIMARY + a loud warning, the aggregate inherits PRIMARY (no code
        # change), and the bare-slug read_path leg is mid8-blind so it ALSO resolves
        # PRIMARY. All three legs now agree on the primary dir → the cell is GREEN.
        None,
    ),
    (
        "coord-empty/slug-mid8",
        "coord-empty",
        SLUG_WITH_MID8,
        MID8,
        # WP05 (T022): the read-path leg adopts WP01's ``probe_coord_state`` under
        # ``require_exists=True`` and returns PRIMARY for the EMPTY state — matching
        # the surface's Option B primary fallback and the aggregate's inherited
        # primary. All three legs now agree on the primary dir → GREEN.
        None,
    ),
    (
        "coord-deleted/bare",
        "coord-deleted",
        MISSION_SLUG,
        "",
        # WP05 (T022/T023): the read-path leg derives mid8 from the primary meta and
        # hard-fails ``CoordinationBranchDeleted``; the aggregate now propagates the
        # same type verbatim (more-specific ``except`` ahead of the SRPNF re-wrap).
        # All three legs converge on ``COORDINATION_BRANCH_DELETED`` → GREEN.
        None,
    ),
    (
        "coord-deleted/slug-mid8",
        "coord-deleted",
        SLUG_WITH_MID8,
        MID8,
        # WP05 (T022/T023): same convergence as coord-deleted/bare — read_path,
        # surface, and aggregate all raise ``CoordinationBranchDeleted`` /
        # ``COORDINATION_BRANCH_DELETED``. GREEN.
        None,
    ),
    # WP04 (T023, FR-005/#2062 read leg) — the flattened-stale-coord topology ×
    # EVERY handle form. The mission was flattened mid-flight (stored
    # ``topology: single_branch``, NO ``coordination_branch``) but a stale ``-coord``
    # husk lingers on disk. The stored topology drives all three read legs
    # (read_path, surface, aggregate) to the PRIMARY dir regardless of the husk —
    # the structural #2062 read-leg close. GREEN (not xfail) once T020/T021 land.
    (
        "flattened-stale-coord/slug-mid8",
        "flattened-stale-coord",
        SLUG_WITH_MID8,
        MID8,
        None,
    ),
    (
        "flattened-stale-coord/bare-mid8",
        "flattened-stale-coord",
        MID8,
        MID8,
        None,
    ),
    (
        "flattened-stale-coord/full-ulid",
        "flattened-stale-coord",
        MISSION_ID,
        MID8,
        None,
    ),
    (
        "flattened-stale-coord/bare-human-slug",
        "flattened-stale-coord",
        MISSION_SLUG,
        "",
        None,
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


# ---------------------------------------------------------------------------
# T022 — PURE stored-topology cell (FR-010a, NFR-005): zero FS/git fixtures
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("topology", list(MissionTopology))
def test_pure_stored_topology_projects_surface_placement(
    topology: MissionTopology,
) -> None:
    """T022: ``resolve_context_for_mission`` projects PRIMARY vs coordination by topology.

    The ADDITIVE pure cell (FR-010a): it feeds WP03's pure resolver
    ``resolve_context_for_mission`` for ALL FOUR ``MissionTopology`` values with a
    production-shaped 26-char ULID and asserts the projected ``ExecutionContext``
    surface placement — ``SINGLE_BRANCH`` / ``LANES`` → PRIMARY (``FLATTENED`` ref,
    ``routes_through_coordination`` False); ``COORD`` / ``LANES_WITH_COORD`` →
    coordination placement. ZERO FS/git fixtures (no ``tmp_path`` meta, no repo
    init, no ``load_meta`` monkeypatch): the resolver is PURE (it mirrors quickstart
    R0). This ADDS a proof; it does NOT replace the on-disk flattened-stale-coord
    row (T023), whose canonical authority is the live surface resolver.
    """
    from mission_runtime import (
        BranchRefFragment,
        CommitTarget,
        CommitTargetKind,
        IdentityFragment,
        routes_through_coordination,
    )
    from mission_runtime.resolution import resolve_context_for_mission

    # renata SHOULD-FIX: pin the expected placement ``kind`` per cell to a HARDCODED
    # literal, NOT ``destination_kind_for_topology(topology)`` (which asserts the
    # resolver against the very helper it calls — a tautology that stays green if
    # both drift together). The grid is small and stable, so the expectation is
    # spelled out independently of the production mapping.
    expected_kind_by_topology = {
        MissionTopology.SINGLE_BRANCH: CommitTargetKind.FLATTENED,
        MissionTopology.LANES: CommitTargetKind.FLATTENED,
        MissionTopology.COORD: CommitTargetKind.COORDINATION,
        MissionTopology.LANES_WITH_COORD: CommitTargetKind.COORDINATION,
    }

    coordination_branch = (
        COORD_BRANCH
        if topology in (MissionTopology.COORD, MissionTopology.LANES_WITH_COORD)
        else None
    )
    identity = IdentityFragment.derive(
        mission_id=MISSION_ID, mission_slug=MISSION_SLUG
    )
    branch_ref = BranchRefFragment(
        target_branch="feat/single-surface",
        coordination_branch=coordination_branch,
        destination_ref=CommitTarget(
            ref=coordination_branch or "feat/single-surface",
            kind=CommitTargetKind.PRIMARY,
        ),
    )
    context = resolve_context_for_mission(
        MISSION_ID,
        topology,
        action="specify",
        mission_slug=MISSION_SLUG,
        feature_dir=f"kitty-specs/{SLUG_WITH_MID8}",
        target_branch="feat/single-surface",
        identity=identity,
        branch_ref=branch_ref,
    )

    assert context.branch_ref is not None
    assert (
        context.branch_ref.destination_ref.kind
        is expected_kind_by_topology[topology]
    )
    # The per-ref routing authority agrees with the topology classification.
    coord_cells = (MissionTopology.COORD, MissionTopology.LANES_WITH_COORD)
    assert routes_through_coordination(context.branch_ref.destination_ref) is (
        topology in coord_cells
    )
    # PRIMARY (flattened) cells share the target ref; coord cells route the coord ref.
    if topology in coord_cells:
        assert context.branch_ref.destination_ref.kind is CommitTargetKind.COORDINATION
        assert context.branch_ref.destination_ref.ref == COORD_BRANCH
    else:
        assert context.branch_ref.destination_ref.kind is CommitTargetKind.FLATTENED
        assert context.branch_ref.destination_ref.ref == "feat/single-surface"


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
