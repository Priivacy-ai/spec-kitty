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

from mission_runtime import (
    MissionArtifactKind,
    MissionTopology,
    classify_topology,
    is_primary_artifact_kind,
    routes_through_coordination,
)
from specify_cli.coordination.surface_resolver import (
    resolve_status_surface_with_anchor,
)
from specify_cli.lanes import (
    ExecutionLane,
    LanesManifest,
    write_lanes_json,
)
from specify_cli.migration.backfill_topology import (
    backfill_mission_topology,
    read_topology,
)
from specify_cli.missions._read_path_resolver import (
    MissionSelectorAmbiguous,
    StatusReadPathNotFound,
    primary_feature_dir_for_mission,
    read_primary_meta,
    resolve_handle_to_read_path,
    resolve_planning_read_dir,
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
    # ``stored_topology_from_meta`` is typed ``MissionTopology | None`` but mypy
    # widens its return to ``Any`` (the source module re-imports the enum locally);
    # the explicit ``isinstance`` narrows it back without a ``cast`` so this helper
    # stays type-clean (campsite #1970).
    stored = stored_topology_from_meta(primary_meta)
    if isinstance(stored, MissionTopology):
        return stored
    raw_branch = primary_meta.get("coordination_branch")
    branch = str(raw_branch) if isinstance(raw_branch, str) and raw_branch else None
    derived: MissionTopology = classify_topology(branch, has_lanes=False)
    return derived


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
    production-shaped 26-char ULID and asserts the projected ``MissionExecutionContext``
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
        IdentityFragment,
        routes_through_coordination,
    )
    from mission_runtime.resolution import resolve_context_for_mission

    # DoD-(a) THE WELD (FR-001b): pin the absolute per-topology surface placement to
    # a HARDCODED literal table, NOT ``routes_through_coordination(topology)`` (which
    # asserts the predicate against itself — a tautology). The grid is small and
    # stable, so the expectation is spelled out independently of the production
    # mapping. This is the over-collapse "everything→PRIMARY" mutant-killer that
    # MUST ship with the enum deletion.
    expected_routes_coord_by_topology = {
        MissionTopology.SINGLE_BRANCH: False,
        MissionTopology.LANES: False,
        MissionTopology.COORD: True,
        MissionTopology.LANES_WITH_COORD: True,
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
        destination_ref=CommitTarget(ref=coordination_branch or "feat/single-surface"),
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
    # The absolute per-topology surface pin (the WELD): COORD/LANES_WITH_COORD →
    # coordination, SINGLE_BRANCH/LANES → PRIMARY. Asserted via the topology
    # predicate, NOT a deleted per-ref enum.
    coord_cells = (MissionTopology.COORD, MissionTopology.LANES_WITH_COORD)
    assert (
        routes_through_coordination(topology)
        is expected_routes_coord_by_topology[topology]
    )
    # PRIMARY (flattened) cells share the target ref; coord cells route the coord ref.
    if topology in coord_cells:
        assert routes_through_coordination(topology) is True
        assert context.branch_ref.destination_ref.ref == COORD_BRANCH
    else:
        assert routes_through_coordination(topology) is False
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
    from mission_runtime import MissionArtifactKind
    from mission_runtime.resolution import ActionContextError, resolve_placement_only

    _build_ambiguous(tmp_path)
    with pytest.raises(ActionContextError) as excinfo:
        # The ambiguous-selector error fires before kind matters; any kind drives
        # the same boundary translation (write-surface-coherence WP02 / T031).
        resolve_placement_only(tmp_path, _AMBIG_MID8, kind=MissionArtifactKind.SPEC)
    # The translated boundary error must preserve the routing code (FR-005).
    assert excinfo.value.code == "MISSION_AMBIGUOUS_SELECTOR"


# ---------------------------------------------------------------------------
# WP01 (01KVRJ6P) — verification safety net
# ---------------------------------------------------------------------------
#
# Three additions gate every deletion/collapse downstream:
#
#   * T001 — differential cell: classify-on-read ≡ backfill-then-read, asserted
#     GREEN over the (topology × transient) matrix. The single-authority cleanup
#     mission deletes the perpetual re-inference arm; this cell proves the stored
#     ``topology`` an un-backfilled mission *would* derive on read is byte-for-byte
#     the SAME value a one-shot ``backfill_mission_topology`` persists. If the two
#     ever diverge, deleting the classify-on-read arm changes observable behaviour.
#
#   * DoD-(a) — absolute per-topology surface placement cell: an explicit value
#     table pinning SINGLE_BRANCH/LANES → PRIMARY (``routes_through_coordination``
#     False) and COORD/LANES_WITH_COORD → coordination (True). This is the ONLY
#     kill for the wrong-MAPPING mutant the leg-vs-leg differential gate cannot
#     catch (both legs could agree on the *wrong* surface). Complementary to T001,
#     never a replacement — keep BOTH.
#
#   * T002 — NFR-002 live RED repro: an un-backfilled flattened mission with a
#     stale coord husk resolves PRIMARY. RED on current code (the husk leaks, the
#     #2062 bug surviving on the ``topology is None`` legacy arm); xfail(strict)
#     until WP06 drains the legacy consults-coord-husk arm.

# T001 transient axis: the orthogonal provenance/declaration variations that MUST
# NOT change the derived topology. Each entry is a meta-fields patch applied on top
# of the per-topology base meta.
_TRANSIENTS: tuple[tuple[str, dict[str, object]], ...] = (
    ("no-provenance", {}),
    ("flattened-true", {"flattened": True}),
    ("flattened-false", {"flattened": False}),
)


def _write_lanes_manifest(feature_dir: Path, slug: str) -> None:
    """Persist a real ``lanes.json`` via the production seam (``write_lanes_json``).

    The topology classifier reads only *presence* of a parseable ``lanes.json``
    (``_has_lanes``), so a single minimal-but-valid manifest built through the
    canonical writer is the production-shaped lanes signal — not a hand-rolled file.
    """
    manifest = LanesManifest(
        version=1,
        mission_slug=slug,
        mission_id=MISSION_ID,
        mission_branch=COORD_BRANCH,
        target_branch="feat/single-surface",
        lanes=[
            ExecutionLane(
                lane_id="lane-a",
                wp_ids=("WP01",),
                write_scope=("src/foo.py",),
                predicted_surfaces=("core",),
                depends_on_lanes=(),
                parallel_group=0,
            )
        ],
        computed_at="2026-06-23T00:00:00+00:00",
        computed_from="dependency_graph+ownership",
    )
    write_lanes_json(feature_dir, manifest)


# (topology_enum, has_coord, has_lanes) — the four-cell topology axis built from
# the two orthogonal production signals (coordination_branch presence × lanes.json
# presence), the SAME pair ``classify_topology`` consumes.
_TOPOLOGY_AXIS: tuple[tuple[MissionTopology, bool, bool], ...] = (
    (MissionTopology.SINGLE_BRANCH, False, False),
    (MissionTopology.LANES, False, True),
    (MissionTopology.COORD, True, False),
    (MissionTopology.LANES_WITH_COORD, True, True),
)


def _build_unbackfilled_mission(
    feature_dir: Path,
    *,
    has_coord: bool,
    has_lanes: bool,
    transient: dict[str, object],
) -> None:
    """Materialise an UN-backfilled mission dir: NO ``topology`` key in meta.

    The fixture carries production-shaped identity (``MISSION_ID`` — a real 26-char
    ULID) and the orthogonal signals (``coordination_branch`` + ``lanes.json``) the
    classifier consumes, plus the transient provenance patch — but deliberately NO
    stored ``topology``, so ``read_topology`` exercises the classify-on-read arm.
    """
    fields: dict[str, object] = {"mission_id": MISSION_ID, **transient}
    if has_coord:
        fields["coordination_branch"] = COORD_BRANCH
    _write_meta(feature_dir, **fields)
    if has_lanes:
        _write_lanes_manifest(feature_dir, feature_dir.name)


@pytest.mark.parametrize(
    ("topology", "has_coord", "has_lanes"),
    [
        pytest.param(t, c, lanes, id=t.value)
        for (t, c, lanes) in _TOPOLOGY_AXIS
    ],
)
@pytest.mark.parametrize(
    "transient",
    [pytest.param(patch, id=name) for name, patch in _TRANSIENTS],
)
def test_classify_on_read_equals_backfill_then_read(
    tmp_path: Path,
    topology: MissionTopology,
    has_coord: bool,
    has_lanes: bool,
    transient: dict[str, object],
) -> None:
    """T001: classify-on-read ≡ backfill-then-read for every (topology × transient).

    The deletion-safety differential for the single-authority cleanup: the value an
    un-backfilled mission derives on read (``read_topology`` over a meta with NO
    ``topology`` key — the classify-on-read arm) MUST equal the value
    ``backfill_mission_topology`` persists and a subsequent read returns
    (backfill-then-read). Asserted GREEN today across the full matrix; a divergence
    here means deleting the classify-on-read arm downstream is NOT behaviour-neutral.

    Distinct fixtures per leg (one is mutated by the backfill write, one is not) so
    the persisting backfill cannot contaminate the pure-read leg.
    """
    # Leg A — classify-on-read: read the un-backfilled meta directly (no write).
    classify_dir = tmp_path / "kitty-specs" / "classify"
    _build_unbackfilled_mission(
        classify_dir, has_coord=has_coord, has_lanes=has_lanes, transient=transient
    )
    classify_on_read = read_topology(classify_dir)

    # Leg B — backfill-then-read: persist via the production migration, then read.
    backfill_dir = tmp_path / "kitty-specs" / "backfill"
    _build_unbackfilled_mission(
        backfill_dir, has_coord=has_coord, has_lanes=has_lanes, transient=transient
    )
    result = backfill_mission_topology(backfill_dir)
    backfill_then_read = read_topology(backfill_dir)

    # The two legs converge (differential equivalence) ...
    assert classify_on_read is backfill_then_read, (
        f"classify-on-read derived {classify_on_read} but backfill-then-read "
        f"derived {backfill_then_read} — the classify arm is NOT behaviour-neutral"
    )
    # ... AND both equal the expected cell (the absolute anchor, not pure leg-equality:
    # leg-vs-leg equality alone would pass even if BOTH derived the wrong topology).
    assert classify_on_read is topology
    # The backfill actually persisted the same value (idempotent migration contract).
    assert result.action == "wrote"
    assert result.topology == topology.value


def test_absolute_surface_placement_by_topology() -> None:
    """DoD-(a): pin PRIMARY-vs-coordination surface per topology by explicit table.

    The absolute companion to the leg-vs-leg differential gate: it spells out, with
    a HARDCODED expectation (not ``destination_kind_for_topology`` — that would be a
    tautology), which topology routes through coordination. This is the ONLY kill
    for the wrong-mapping mutant the differential gate cannot catch (both legs could
    agree on the same WRONG surface).

    ``routes_through_coordination`` is the stored-topology routing authority
    (FR-005 / FR-001b); a coord-less topology must return ``False`` and a
    coord-routing topology ``True``. The mapping topology → routes-through-coord is
    the contract:
      * SINGLE_BRANCH / LANES   → PRIMARY surface  (routes_through_coordination False)
      * COORD / LANES_WITH_COORD → coordination     (routes_through_coordination True)

    Negative control built in: PRIMARY-mapped cells assert ``False`` and
    coordination-mapped cells assert ``True`` — a single over-routing mutant
    (mapping a coord-less topology to coordination) fails the table, and a single
    under-routing mutant (mapping a coord topology to primary) fails it too.
    """
    expected_routes_through_coord: dict[MissionTopology, bool] = {
        MissionTopology.SINGLE_BRANCH: False,
        MissionTopology.LANES: False,
        MissionTopology.COORD: True,
        MissionTopology.LANES_WITH_COORD: True,
    }
    # Every topology member is pinned — a new enum member would KeyError here, an
    # intentional tripwire forcing the table to stay exhaustive.
    assert set(expected_routes_through_coord) == set(MissionTopology)

    for topology, routes in expected_routes_through_coord.items():
        assert routes_through_coordination(topology) is routes, (
            f"{topology.value} expected routes_through_coordination={routes} "
            "— surface-placement mapping mutant"
        )


# ---------------------------------------------------------------------------
# T002 — NFR-002 live RED repro (xfail strict, drains in WP06)
# ---------------------------------------------------------------------------


def _build_unbackfilled_flattened_with_husk(repo_root: Path) -> tuple[Path, Path]:
    """Materialise an UN-backfilled flattened mission + a stale coord husk on disk.

    Mirrors ``_build_topology(..., topology="flattened-stale-coord")`` EXCEPT the
    primary ``meta.json`` carries NO stored ``topology`` key — only the ``flattened``
    provenance flag and ``mission_id``. This is the precise un-backfilled shape that
    drives ``stored_topology_from_meta`` → ``None`` → the legacy probe-based
    consults-coord-husk arm (the #2062 leak path WP06 drains). Returns
    ``(primary_dir, husk_dir)``.
    """
    _init_repo(repo_root)
    primary = repo_root / "kitty-specs" / SLUG_WITH_MID8
    # NO ``topology`` key — the un-backfilled flattened shape (FR-005 / NFR-002).
    _write_meta(primary, mission_id=MISSION_ID, flattened=True)
    (primary / "status.events.jsonl").write_text(
        '{"wp_id":"WP01","to_lane":"approved"}\n', encoding="utf-8"
    )
    coord_root = repo_root / ".worktrees" / f"{SLUG_WITH_MID8}-coord"
    _git(repo_root, "worktree", "add", "-q", "-b", COORD_BRANCH, str(coord_root))
    husk = coord_root / "kitty-specs" / SLUG_WITH_MID8
    husk.mkdir(parents=True, exist_ok=True)
    _write_meta(husk, mission_id=MISSION_ID)
    (husk / "status.events.jsonl").write_text(
        '{"wp_id":"WP01","to_lane":"planned"}\n', encoding="utf-8"
    )
    return primary, husk


def test_unbackfilled_flattened_resolves_primary_not_husk(tmp_path: Path) -> None:
    """T002 (NFR-002): an un-backfilled flattened mission MUST resolve PRIMARY.

    Live RED→GREEN evidence — a static edit cannot satisfy it. Before WP06 the read
    path read NO stored ``topology`` (``stored_topology_from_meta`` → ``None``), fell
    into the legacy probe-based arm, found the materialized coord husk, and returned
    the STALE husk (the #2062 leak surviving on the un-backfilled path).

    WP06 (T015) drained that arm: the read-path BOUNDARY now ABSORBS the absent
    ``topology`` field into a concrete topology (``classify_from_meta`` →
    SINGLE_BRANCH for a flattened mission with no ``coordination_branch``), threading
    PRIMARY routing downstream — so the husk is structurally not consulted and this
    repro resolves PRIMARY (the strict-xfail was drained, not re-keyed). Asserts the
    OBSERVABLE resolved surface (the returned dir), never the internal call graph.
    """
    primary, husk = _build_unbackfilled_flattened_with_husk(tmp_path)
    resolved = resolve_handle_to_read_path(
        tmp_path, SLUG_WITH_MID8, require_exists=True
    ).resolve()

    # Negative control: prove the husk is genuinely a DIFFERENT, present directory —
    # otherwise "resolves primary" could pass vacuously if the husk never existed.
    assert husk.resolve().exists()
    assert husk.resolve() != primary.resolve()

    assert resolved == primary.resolve(), (
        f"un-backfilled flattened mission resolved {resolved} but must resolve the "
        f"PRIMARY dir {primary.resolve()} — the stale coord husk "
        f"{husk.resolve()} must NOT be consulted (#2062 / NFR-002)"
    )


def test_unbackfilled_flattened_repro_resolves_primary_after_wp06(
    tmp_path: Path,
) -> None:
    """T002 companion: the un-backfilled flattened mission resolves PRIMARY (post-WP06).

    The companion that moved as a PAIR with the strict-xfail drain above. Before WP06
    this asserted the RED behaviour (the husk leaked) and kept the xfail honest; WP06
    (T015) absorbs the absent ``topology`` field at the read boundary, so this now
    asserts the GREEN contract directly — an executable, non-marker proof that the
    flattened mission resolves the PRIMARY dir, NOT the stale coord husk. Negative
    control: the husk is a genuinely distinct, present directory, so "resolves
    primary" cannot pass vacuously.
    """
    primary, husk = _build_unbackfilled_flattened_with_husk(tmp_path)
    try:
        resolved = resolve_handle_to_read_path(
            tmp_path, SLUG_WITH_MID8, require_exists=True
        ).resolve()
    except StatusReadPathNotFound:  # pragma: no cover — defensive: not the fixed arm
        pytest.fail(
            "expected the un-backfilled flattened repro to resolve PRIMARY after "
            "WP06's boundary absorption, but it raised StatusReadPathNotFound"
        )
    # Negative control: the husk is a different, present dir (non-vacuous).
    assert husk.resolve().exists()
    assert husk.resolve() != primary.resolve()
    # POST-WP06 (GREEN): the boundary absorption routes the flattened mission to
    # PRIMARY; the stale coord husk is structurally not consulted (#2062 / NFR-002).
    assert resolved == primary.resolve(), (
        "post-WP06 the un-backfilled flattened mission must resolve the PRIMARY dir "
        f"{primary.resolve()} (boundary absorption), NOT the stale coord husk "
        f"{husk.resolve()} (#2062 / NFR-002)"
    )


# ---------------------------------------------------------------------------
# WP01 (retrospective-durable-home, FR-011 / #2136) — handle-safe PRIMARY read
# seam. The kind-aware read seam ``resolve_planning_read_dir`` feeds its
# PRIMARY-partition leg into the topology-BLIND primitive
# ``primary_feature_dir_for_mission``. A bare ``mid8`` / human slug does NOT name
# the on-disk ``<slug>-<mid8>`` dir, so the raw-handle compose DIVERGED (the
# #2136 bug). WP01 canonicalizes IN THE CALLER (mirroring the live exemplars),
# leaving the primitive blind. These cells prove the cure THROUGH the read seam.
# ---------------------------------------------------------------------------

# A PRIMARY-partition kind drives the ``is_primary_artifact_kind`` leg the bug
# lives on. ``SPEC`` is canonically PRIMARY-partition (mission_runtime.artifacts).


def _primary_kind() -> MissionArtifactKind:
    """The PRIMARY-partition ``MissionArtifactKind`` driving the seam's bug leg.

    Asserts the partition membership so a re-shuffle in ``mission_runtime.artifacts``
    (the FR-006 one-line move) that flips ``SPEC`` off the PRIMARY partition fails
    loudly here rather than silently routing the test onto the STATUS leg.
    """
    kind = MissionArtifactKind.SPEC
    assert is_primary_artifact_kind(kind), (
        "SPEC must be a PRIMARY-partition kind to exercise the PRIMARY leg of "
        "resolve_planning_read_dir (the #2136 bug leg)"
    )
    return kind


def _build_canonical_primary(repo_root: Path) -> Path:
    """Materialise a canonical ``kitty-specs/<slug>-<mid8>/`` PRIMARY dir.

    Production-shaped identity (real 26-char ULID, mid8 = first 8 lowercase). The
    dir name is the COMPOSED ``<slug>-<mid8>`` — so a bare ``mid8`` or bare human
    slug has a genuinely WRONG literal-compose target (``kitty-specs/<bare>``),
    making the divergence observable (the false-green guard in T011's notes).
    """
    _init_repo(repo_root)
    canonical_dir = repo_root / "kitty-specs" / SLUG_WITH_MID8
    _write_meta(canonical_dir, mission_id=MISSION_ID)
    return canonical_dir


def test_primary_read_seam_handle_equivalence(tmp_path: Path) -> None:
    """T011/T012 (FR-011): bare-mid8 ≡ bare-slug ≡ ``<slug>-<mid8>`` → SAME dir.

    Drives the PRE-EXISTING entry point ``resolve_planning_read_dir`` (the seam the
    #2136 bug lives in) on a PRIMARY-partition kind, three handle forms against ONE
    canonical ``<slug>-<mid8>`` primary dir:

    * the composed ``<slug>-<mid8>`` (the canonical anchor);
    * a bare lowercase ``mid8`` (``MID8`` — the canonical disambiguator alone);
    * a bare human slug (``MISSION_SLUG`` — no mid8 tail).

    RED on the pre-WP01 code: the PRIMARY leg passed the RAW handle to the
    topology-blind ``primary_feature_dir_for_mission``, so the bare forms composed
    ``kitty-specs/<bare>`` — a DIFFERENT dir than the composed anchor. GREEN after
    the caller-canonicalization: all three fold to the SAME canonical dir.

    Asserts the OBSERVABLE resolved dir (``Path.resolve()`` equality), never the
    internal call graph. The canonical anchor is pinned to the on-disk composed dir
    (not mere leg-equality) so a "both wrong but equal" mutant cannot pass.
    """
    canonical_dir = _build_canonical_primary(tmp_path)
    kind = _primary_kind()
    expected = canonical_dir.resolve()

    composed = resolve_planning_read_dir(tmp_path, SLUG_WITH_MID8, kind=kind).resolve()
    bare_mid8 = resolve_planning_read_dir(tmp_path, MID8, kind=kind).resolve()
    bare_slug = resolve_planning_read_dir(tmp_path, MISSION_SLUG, kind=kind).resolve()

    # Absolute anchor: the composed handle resolves the real on-disk canonical dir.
    assert composed == expected, (
        f"composed handle resolved {composed}, expected the canonical PRIMARY dir "
        f"{expected}"
    )
    # Equivalence: the bare forms fold to the SAME canonical dir (FR-011 / #2136).
    assert bare_mid8 == expected, (
        f"bare mid8 {MID8!r} resolved {bare_mid8} but must fold to the canonical "
        f"PRIMARY dir {expected} (handle-safe read seam — #2136)"
    )
    assert bare_slug == expected, (
        f"bare slug {MISSION_SLUG!r} resolved {bare_slug} but must fold to the "
        f"canonical PRIMARY dir {expected} (handle-safe read seam — #2136)"
    )


def test_primary_read_seam_ambiguous_handle_raises(tmp_path: Path) -> None:
    """T011 (FR-011 / C-009): an ambiguous handle raises, never silently picks.

    Two missions colliding on the same mid8 prefix → the bare mid8 is ambiguous.
    The PRIMARY leg's caller-canonicalization MUST propagate
    ``MissionSelectorAmbiguous`` (``MISSION_AMBIGUOUS_SELECTOR``) unchanged — the
    no-silent-fallback contract (WP07 regression class). A silent pick of either
    candidate dir is the regression this asserts against.
    """
    _build_ambiguous(tmp_path)
    kind = _primary_kind()

    with pytest.raises(MissionSelectorAmbiguous) as excinfo:
        resolve_planning_read_dir(tmp_path, _AMBIG_MID8, kind=kind)
    assert excinfo.value.error_code == "MISSION_AMBIGUOUS_SELECTOR"


def test_primary_read_seam_canonical_handle_is_noop(tmp_path: Path) -> None:
    """T013 (NFR-005): a canonical ``<slug>-<mid8>`` handle is a no-op.

    The ``meta.json``-present short-circuit leg of
    ``_canonicalize_bare_modern_handle`` returns the handle unchanged, so the
    canonical handle resolves to exactly the literal compose — byte-identical to the
    pre-WP01 behaviour for an already-canonical handle.
    """
    canonical_dir = _build_canonical_primary(tmp_path)
    kind = _primary_kind()

    resolved = resolve_planning_read_dir(tmp_path, SLUG_WITH_MID8, kind=kind).resolve()
    # No-op: the canonical handle resolves the literal composed dir — the SAME path
    # the blind primitive composes directly (the present-leg short-circuit).
    assert resolved == canonical_dir.resolve()
    assert resolved == primary_feature_dir_for_mission(tmp_path, SLUG_WITH_MID8).resolve()


def test_primary_read_seam_unresolvable_handle_is_byte_identical(tmp_path: Path) -> None:
    """T013 (NFR-005): an unresolvable handle behaves EXACTLY as the blind compose.

    An unresolvable handle (no matching mission, no ``meta.json``) hits the
    unresolvable leg of ``_canonicalize_bare_modern_handle`` → the handle is
    returned unchanged → literal compose, byte-identical to the pre-WP01 raw-handle
    behaviour AND to a direct call into the blind primitive.
    """
    _init_repo(tmp_path)  # no kitty-specs, no mission at all
    kind = _primary_kind()
    handle = "no-such-mission"

    resolved = resolve_planning_read_dir(tmp_path, handle, kind=kind).resolve()
    # Byte-identical to the blind primitive's literal compose (no-op fold).
    assert resolved == primary_feature_dir_for_mission(tmp_path, handle).resolve()


def test_primitive_stays_blind_under_bare_handle(tmp_path: Path) -> None:
    """T013 step 4 (NFR-005): the primitive STILL diverges for a bare handle.

    The cure lives in the CALLER, not the primitive. A direct call to the
    topology-blind ``primary_feature_dir_for_mission`` with a bare ``mid8`` STILL
    literal-composes the bare name (``kitty-specs/<mid8>``) — a DIFFERENT dir than
    the canonical ``<slug>-<mid8>``. This proves the primitive's blind contract is
    preserved (no canonicalization folded into its body — recursion-safety) and
    that the seam-level equivalence is genuinely the caller's doing.
    """
    canonical_dir = _build_canonical_primary(tmp_path)

    blind = primary_feature_dir_for_mission(tmp_path, MID8).resolve()
    # The blind primitive composes the bare name verbatim — it does NOT canonicalize.
    assert blind == (tmp_path / "kitty-specs" / MID8).resolve()
    # ... and that is a genuinely DIFFERENT dir than the canonical one (non-vacuous).
    assert blind != canonical_dir.resolve()
