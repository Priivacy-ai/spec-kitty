"""Mission read-path resolution (WP08 T037, FR-030).

Read-side CLI commands — ``spec-kitty agent tasks status``,
``agent context resolve``, ``agent decision verify`` — must locate
``status.events.jsonl`` / ``status.json`` / ``decisions/index.json``
regardless of the operator's current working directory.  The truth lives
in one of two places depending on mission topology:

* **New topology** (post-WP03): the coordination worktree at
  ``<repo_root>/.worktrees/<slug>-<mid8>-coord/kitty-specs/<slug>-<mid8>/``.
  All lane processes write through ``BookkeepingTransaction``, which
  commits to that worktree; lanes themselves do not carry the status
  files (sparse-checkout policy excludes them).
* **Legacy mission** (pre-WP03): no coord worktree exists.  The status
  files live in the primary checkout at
  ``<repo_root>/kitty-specs/<slug>[-<mid8>]/``.

The resolver returns the directory containing those files.  It does
**not** assert their presence — the caller decides whether absence is
an error (and surfaces ``STATUS_READ_PATH_NOT_FOUND`` accordingly).

Spec source: FR-030, SC-02.
"""

from __future__ import annotations

from specify_cli.core.constants import KITTY_SPECS_DIR
from collections.abc import Mapping
import enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mission_runtime import MissionArtifactKind, MissionTopology


STATUS_READ_PATH_NOT_FOUND_CODE = "STATUS_READ_PATH_NOT_FOUND"
MISSION_AMBIGUOUS_SELECTOR_CODE = "MISSION_AMBIGUOUS_SELECTOR"


class MissionSelectorAmbiguous(Exception):
    """A mission handle (mid8 / numeric prefix / human slug) matched more than
    one mission.

    Carries a stable ``error_code`` (``MISSION_AMBIGUOUS_SELECTOR``) so callers
    route on it without string parsing. This is the C-CTX-4 / C-009
    no-silent-fallback path: an ambiguous selector is an explicit, structured
    error — never a silent pick of a wrong-but-plausible mission directory.
    """

    error_code: str = MISSION_AMBIGUOUS_SELECTOR_CODE

    def __init__(self, *, handle: str, candidates: list[str]) -> None:
        self.handle = handle
        self.candidates = candidates
        super().__init__(
            f"Mission handle {handle!r} matches multiple missions: "
            f"{', '.join(candidates)}. Re-run with a more specific handle "
            f"(full slug or full mission_id)."
        )


class StatusReadPathNotFound(Exception):
    """Neither the coordination worktree nor the primary checkout carries
    the requested mission directory.

    Carries a stable ``error_code`` (``STATUS_READ_PATH_NOT_FOUND``) so
    callers can route on it without string parsing.
    """

    error_code: str = STATUS_READ_PATH_NOT_FOUND_CODE

    def __init__(
        self,
        *,
        repo_root: Path,
        mission_slug: str,
        mid8: str,
        coord_candidate: Path,
        primary_candidate: Path,
    ) -> None:
        self.repo_root = repo_root
        self.mission_slug = mission_slug
        self.mid8 = mid8
        self.coord_candidate = coord_candidate
        self.primary_candidate = primary_candidate
        super().__init__(
            f"Status read path not found for {mission_slug!r} "
            f"(mid8={mid8!r}): checked {coord_candidate} and "
            f"{primary_candidate}"
        )


def _declares_coordination_branch(path: Path) -> bool:
    """True when the primary ``meta.json`` declares a non-empty ``coordination_branch``.

    The narrowed legacy band-aid: FR-006 retires its **topology decision** role for
    any mission whose WP02 stored ``topology`` is present — the husk is then
    structurally not consulted. It survives ONLY on the un-backfilled legacy path
    (``topology is None``), where the read path still falls back to the historical
    declared-coord + materialized-husk fail-closed derivation exactly once
    (FR-003 shell contract).

    Reads via the canonical :func:`mission_metadata.load_meta` seam (FR-006 /
    NFR-004) with ``on_malformed="none"`` so a missing OR malformed/unreadable meta
    both degrade to ``None`` → ``False`` (the historical silent-degrade contract this
    band-aid always had — it must NEVER raise, since it is only the legacy-arm
    declared-coord signal, not the corrupt-meta typed path).
    """
    from specify_cli.mission_metadata import load_meta

    meta = load_meta(path, on_malformed="none")
    branch = meta.get("coordination_branch") if isinstance(meta, dict) else None
    return isinstance(branch, str) and bool(branch.strip())


def stored_topology_from_meta(meta: Mapping[str, object]) -> MissionTopology | None:
    """Extract the WP02 **stored** :class:`MissionTopology` from a primary-meta dict.

    PURE — operates on the already-read ``primary_meta`` mapping the read-path
    boundary (:func:`resolve_handle_to_read_path`) holds; it opens **no** file and
    runs no git (FR-006 / C-004). Returns ``None`` when the ``topology`` key is
    absent or carries an unrecognised value (un-backfilled legacy mission), so the
    caller falls back to the probe-based derivation exactly once (FR-003 shell
    contract). The stored value is authoritative when present.
    """
    from mission_runtime import MissionTopology

    raw = meta.get("topology")
    if not isinstance(raw, str):
        return None
    try:
        return MissionTopology(raw)
    except ValueError:
        return None


def classify_from_meta(
    meta: Mapping[str, object], feature_dir: Path
) -> MissionTopology | None:
    """Acquire a **concrete** :class:`MissionTopology` from an in-hand primary meta.

    The read-path BOUNDARY **absorbing** API (FR-004 / T015): it converts the
    optional :func:`stored_topology_from_meta` read into a concrete topology for any
    **readable** primary meta, so the downstream resolver chain is threaded a
    non-optional value and the ``topology is None`` husk-arms become structurally
    dead for that case (WP17 removes them).

    Precedence (the SAME single authority every leg uses — no parallel 2×2 grid):

    1. the WP02 **stored** ``topology`` is authoritative when present (read via the
       pure :func:`stored_topology_from_meta` seam);
    2. otherwise — the **absent-field** case (un-backfilled legacy / flattened
       mission with a *readable* meta) — the shape is classified ONCE via WP01's
       :func:`mission_runtime.classify_topology` SSOT from the ``coordination_branch``
       value already in the meta + the lanes signal on disk. The flattened mission
       (no ``coordination_branch``) therefore classifies to ``SINGLE_BRANCH`` /
       ``LANES`` → PRIMARY, NOT the stale-coord husk (the #2062 / NFR-002 close).

    **BOUNDARY DISCIPLINE (C-004)**: this absorbs ONLY the absent-``topology``-FIELD
    case. An **empty** ``meta`` (no readable primary ``meta.json`` at all — a genuine
    legacy mission, or a coord-only topology whose meta is not on this surface)
    returns ``None``: there is no ``coordination_branch`` signal to classify against,
    so the caller keeps the historical one-time probe-based husk derivation (FR-003
    shell contract). Absent-field-in-readable-meta ⇒ classify; absent/unreadable meta
    ⇒ ``None`` (legacy probe). The two stay DISTINCT paths.

    PURE except a single ``lanes.json`` ``Path.exists()``/read on the absent-field
    arm (the lanes signal WP01's classifier needs); the stored-value happy path
    touches no disk. The lanes axis never changes the coord-routing answer, so a
    corrupt ``lanes.json`` degrades to "no lanes" rather than failing the read.
    """
    from specify_cli.migration.backfill_topology import _derive_topology

    stored = stored_topology_from_meta(meta)
    if stored is not None:
        return stored
    if not meta:
        # No readable primary meta (legacy / coord-only): NOT the absent-FIELD case.
        # Without a coordination_branch signal there is nothing to classify, so defer
        # to the caller's historical probe-based husk derivation (C-004 / FR-003).
        return None
    # Absent ``topology`` field in a READABLE meta (un-backfilled legacy / flattened):
    # classify ONCE via WP01's single authority from the in-hand meta + the disk lanes
    # signal. ``_derive_topology`` reads ``coordination_branch`` from ``meta`` and
    # probes ``lanes.json`` under ``feature_dir`` — the SAME derivation
    # ``read_topology`` uses, kept pure (no write) here at the read boundary.
    #
    # ``_derive_topology`` is typed -> MissionTopology, but mypy widens it to ``Any``
    # through the late-import chain (``follow_imports=skip`` on ``specify_cli.*``);
    # bind explicitly so the return narrows back (the same pattern as
    # ``_compose_mission_dir``'s cast in this module).
    derived: MissionTopology = _derive_topology(dict(meta), feature_dir)
    return derived


def _compose_mission_dir(mission_slug: str, mid8: str) -> str:
    """Return ``<slug>-<mid8>`` but avoid double-suffixing.

    Delegates the ``<slug>-<mid8>`` grammar to the seam's VERBATIM coordination
    primitive (``lanes.branch_naming.coord_mission_dir_name``) so exactly ONE
    algorithm exists (FR-010). This is a READ path: ``mission_slug`` arrives
    VERBATIM from ``meta.json`` (including any legacy ``NNN-`` prefix), and the
    on-disk mission dir was created without stripping it — so the verbatim
    primitive (no ``NNN-`` strip) reconstructs the EXISTING dir, while the
    canonical, NNN-stripping ``mission_dir_name`` would drift to a path that never
    existed (#1589). The read-path's load-bearing empty-``mid8`` contract is
    preserved locally: a missing mid8 (legacy mission that never minted a
    ``mission_id``) returns the slug VERBATIM — the seam has no empty-mid8 form and
    would emit a spurious trailing ``-``, so the guard stays here.
    """
    from specify_cli.lanes.branch_naming import coord_mission_dir_name

    if not mid8:
        return mission_slug
    # coord_mission_dir_name is typed -> str; mypy loses the annotation
    # through the late import chain — the cast is correct (C-008 fix).
    return str(coord_mission_dir_name(mission_slug, mid8=mid8))


def coord_feature_dir(repo_root: Path, mission_slug: str, mid8: str) -> Path:
    """Compose the coordination-worktree mission dir (paula C1, single grammar).

    The ONE place that builds
    ``CoordinationWorkspace.worktree_path / KITTY_SPECS_DIR / <slug>-<mid8>`` so the
    coord-candidate compose is no longer hand-built across the read path (FR-001 /
    NFR-004). Both read-path probe sites (:func:`_resolve_existing_for_slug`,
    :func:`_resolve_not_found`) route through it; WP04 adopts it for the
    ``surface_resolver.py`` sites that still hand-build the same join.

    Pure-path: no filesystem touch, no git. ``mid8`` must be non-empty — a coord
    topology is only addressable once the disambiguator is known (an empty
    ``mid8`` has no coord worktree to compose); callers gate on ``mid8`` before
    reaching here.
    """
    # Late import breaks the import cycle: ``coordination.__init__`` eagerly
    # imports ``surface_resolver``, which imports ``_compose_mission_dir`` from
    # this module. A module-level import would deadlock whenever this resolver is
    # the first entry point into the coordination package.
    from specify_cli.coordination.workspace import CoordinationWorkspace

    # ``worktree_path`` is typed -> Path, but mypy widens it to ``Any`` through
    # the late-import chain (``follow_imports=skip`` on ``specify_cli.*``); bind
    # explicitly so the join's return narrows back to ``Path`` (the same pattern
    # as ``_compose_mission_dir``'s cast in this module).
    coord_root: Path = CoordinationWorkspace.worktree_path(repo_root, mission_slug, mid8)
    feature_dir: Path = (
        coord_root / KITTY_SPECS_DIR / _compose_mission_dir(mission_slug, mid8)
    )
    return feature_dir


class CoordState(enum.Enum):
    """The coordination-worktree topology state for a mission (paula C2).

    Discriminates the four read-path coord conditions a single probe must
    distinguish, so the read path stops re-deriving them inline (the probe was
    duplicated 3×):

    * ``MATERIALIZED`` — coord worktree root AND its mission dir both exist; the
      coord surface is the authoritative read.
    * ``EMPTY`` — coord worktree root exists but its mission dir is absent
      (#1716 / FR-006): a fail-closed condition, never a silent primary fallback.
    * ``UNMATERIALIZED`` — neither the coord root nor a *deleted* branch: the
      declared-but-not-yet-created window (``mission create`` → first coord
      materialization), where the primary checkout stays authoritative.
    * ``DELETED`` — the coord root is absent AND the declared coordination branch
      has been deleted from git (#1889 row R3 / #1848): data-loss, fail closed
      LOUDLY.

    ``NONE`` is reserved for the no-mid8 case (no coord topology to probe).
    """

    NONE = "none"
    MATERIALIZED = "materialized"
    EMPTY = "empty"
    UNMATERIALIZED = "unmaterialized"
    DELETED = "deleted"


def probe_coord_state(
    repo_root: Path,
    mission_slug: str,
    mid8: str,
    *,
    coordination_branch: str | None = None,
) -> CoordState:
    """Classify the coordination-worktree topology state (paula C2 shared probe).

    The single probe body the read path uses instead of re-deriving the coord
    root/mission-dir/branch checks inline. WP04 (coord-empty) and WP05
    (coord-deleted) adopt THIS body rather than adding a 4th copy.

    The git/``DELETED`` arm reuses the existing
    :func:`surface_resolver._coord_branch_exists` (one ``git rev-parse``) VERBATIM
    — it is the only signal that splits a not-yet-materialized coord (branch
    still present) from a DELETED one (alphonso §3.3); it is NOT collapsed away.
    The ``DELETED`` verdict is only reachable when a ``coordination_branch`` is
    supplied (the read path supplies it from the primary ``meta.json``); without
    it the absent-coord case stays ``UNMATERIALIZED`` (no branch to interrogate).

    Pure-path except the single ``git rev-parse`` on the absent-coord +
    branch-supplied path; ``MATERIALIZED`` / ``EMPTY`` / ``UNMATERIALIZED`` touch
    only ``Path.exists()``.
    """
    if not mid8:
        return CoordState.NONE
    feature_dir = coord_feature_dir(repo_root, mission_slug, mid8)
    coord_root = feature_dir.parent.parent
    if coord_root.exists():
        return CoordState.MATERIALIZED if feature_dir.exists() else CoordState.EMPTY
    # Coord root absent. A supplied branch lets us split UNMATERIALIZED (branch
    # still in git) from DELETED (branch gone) — the single git rev-parse arm.
    if coordination_branch is not None:
        from specify_cli.coordination.surface_resolver import _coord_branch_exists

        if not _coord_branch_exists(repo_root, coordination_branch):
            return CoordState.DELETED
    return CoordState.UNMATERIALIZED


def compose_meta_json_path(base: Path, mission_slug: str) -> Path:
    """Return ``base / KITTY_SPECS_DIR / <slug-mid8-dir> / meta.json``.

    Centralises mission ``meta.json`` path construction so callers outside
    semantic-constructor files do not need to build the path inline.
    """
    from specify_cli.lanes.branch_naming import mid8_from_slug

    dir_name = _compose_mission_dir(mission_slug, mid8_from_slug(mission_slug))
    meta_path: Path = base / KITTY_SPECS_DIR / dir_name / "meta.json"
    return meta_path


def _resolve_existing_for_slug(
    repo_root: Path,
    mission_slug: str,
    mid8: str,
    *,
    topology: MissionTopology | None = None,
) -> Path | None:
    """Return the on-disk mission directory for a *literal* slug, or ``None``.

    The surface decision is driven by the **stored** :class:`MissionTopology`
    (FR-006 / C-004 — the structural #2062 read-leg close), NOT by an on-disk
    ``stat`` of a ``-coord`` worktree. A mission whose stored topology is
    ``SINGLE_BRANCH`` / ``LANES`` resolves PRIMARY **regardless** of a stale
    ``-coord`` husk on disk — the husk is structurally not consulted, so a prior
    flatten that left a husk cannot re-open #2062. Only a coord-routing stored
    topology (``COORD`` / ``LANES_WITH_COORD``) consults the materialized coord
    worktree as the authoritative read.

    The ``topology`` arrives as a PARAMETER (read ONCE from ``primary_meta`` at the
    :func:`resolve_handle_to_read_path` boundary); this helper stays **PURE-PATH**
    — it opens no ``meta.json`` / ``load_meta`` / disk read for topology (only
    ``Path.exists()`` stats). When ``topology`` is ``None`` — now reached ONLY for a
    corrupt/unreadable primary meta (C-004), since every boundary absorbs the absent
    ``topology`` FIELD into a concrete shape (WP06/WP17) — the helper falls back ONCE
    to the historical probe-based coord-existence derivation (FR-003 shell contract).

    Returns ``None`` when neither candidate exists OR when the legacy fail-closed
    condition holds (no stored topology, coord worktree materialised + the
    coord dir absent) — in that case the caller's main path re-raises
    :class:`StatusReadPathNotFound` rather than handing back a stale primary view
    (#1718). Pure-path: no git, no subprocess.
    """
    mission_dir_name = _compose_mission_dir(mission_slug, mid8)
    primary_candidate: Path = repo_root / KITTY_SPECS_DIR / mission_dir_name

    # FR-006 (structural #2062 read-leg): a stored coord-less topology resolves
    # PRIMARY before any on-disk husk probe can fire — the husk is not the
    # deciding signal. When the primary dir is absent the caller falls through to
    # the not-found / canonicalization path with the same stored-topology gate.
    # FR-005: the coord-routing decision flows through the ONE canonical predicate
    # (``routes_through_coordination``); ``topology`` is already non-``None`` here
    # (a concrete value the boundary absorbed), so no second local predicate exists.
    from mission_runtime import routes_through_coordination

    if topology is not None and not routes_through_coordination(topology):
        return primary_candidate if primary_candidate.exists() else None

    # Coord-routing stored topology, OR an un-backfilled legacy mission (topology
    # is None → the one-time probe-based fallback): the materialized coord
    # worktree is the authoritative read.
    coord_worktree_materialized = False
    has_coord_candidate = bool(mid8)
    if mid8:
        # Shared probe (paula C2): MATERIALIZED → the coord mission dir IS the
        # read; EMPTY → coord root exists but the dir does not (defer to the
        # caller's fail-closed path).
        coord_state = probe_coord_state(repo_root, mission_slug, mid8)
        coord_worktree_materialized = coord_state in (
            CoordState.MATERIALIZED,
            CoordState.EMPTY,
        )
        if coord_state is CoordState.MATERIALIZED:
            return coord_feature_dir(repo_root, mission_slug, mid8)
    if primary_candidate.exists():
        if (
            topology is None
            and has_coord_candidate
            and coord_worktree_materialized
            and _declares_coordination_branch(primary_candidate)
        ):
            # Corrupt-meta fail-closed (C-004): ``topology is None`` is now reached
            # ONLY for a corrupt/unreadable primary meta (WP06/WP17 absorb the absent
            # FIELD into a concrete shape at every boundary). Without a classifiable
            # topology we cannot decide PRIMARY-vs-coord, so we defer to the caller's
            # StatusReadPathNotFound path on the historical probe-derived signal. With
            # a concrete stored topology the husk is never the deciding signal, so
            # this arm is bypassed entirely.
            return None
        return primary_candidate
    return None


def _canonicalize_bare_modern_handle(repo_root: Path, handle: str) -> str:
    """Rewrite a bare human slug to its composed ``<slug>-<mid8>`` dir name.

    The shared FR-004 bare-human-slug fold: when the operator typed a bare human
    slug whose on-disk primary dir actually carries the canonical
    ``<slug>-<mid8>`` name (e.g. a mission addressed before any coord worktree
    materialized), the literal-slug compose misses the real directory and the
    stored topology / declared-coord signals are lost — the bare-slug read leg
    would then leak a stale ``-coord`` husk. Both the existence-gated resolver
    (:func:`_resolve_mission_read_path`, feeding the surface leg via
    :func:`candidate_feature_dir_for_mission`) and the guarded seam
    (:func:`resolve_handle_to_read_path`) canonicalize through THIS one fold so
    every read leg converges on the composed name (the SAME bare-modern primitive
    the aggregate's ``_find_meta_path`` consumes — NFR-004).

    Returns the composed dir name when (a) the literal primary dir lacks
    ``meta.json``, (b) the identity resolver resolves the handle to NOTHING (so
    bare-modern is a genuine last resort — it never overrides a resolvable handle),
    AND (c) :func:`resolve_bare_modern_mission_dir_name` finds exactly one composed
    primary dir whose name carries a valid mid8 tail; otherwise the ``handle`` is
    returned unchanged.

    **No-silent-fallback (C-CTX-4 / C-009):** an *ambiguous* handle (one the
    identity resolver matches to >1 mission) propagates
    :class:`MissionSelectorAmbiguous` from :func:`_canonicalize_handle` — it is
    NEVER silently collapsed onto one composed candidate. The identity-resolver
    probe runs FIRST precisely so a numeric-prefix / bare-mid8 handle that the
    bare-modern glob would coincidentally match to a single composed dir cannot
    mask a genuine ambiguity (regression guarded by
    ``test_handle_equivalence_matrix``). Pure-path except the identity resolver's
    own lookup (no extra git here).

    Raises:
        MissionSelectorAmbiguous: When the handle matches more than one mission
            (propagated from :func:`_canonicalize_handle` — no silent pick).
    """
    literal_primary = primary_feature_dir_for_mission(repo_root, handle)
    if (literal_primary / "meta.json").exists():
        return handle
    # The identity resolver runs FIRST: it RAISES MissionSelectorAmbiguous for an
    # ambiguous handle (no silent pick) and returns a tuple for a resolvable one —
    # in both cases bare-modern must not override. Only a genuinely-unresolvable
    # handle (``None``) is a candidate for the bare-human-slug fold.
    if _canonicalize_handle(repo_root, handle) is not None:
        return handle
    bare_dir_name = resolve_bare_modern_mission_dir_name(repo_root, handle)
    return bare_dir_name if bare_dir_name is not None else handle


def _canonicalize_handle(
    repo_root: Path, handle: str
) -> tuple[str, str, Path] | None:
    """Resolve a mission *handle* to its canonical ``(slug, mid8, feature_dir)``.

    A *handle* is whatever the operator typed into ``--mission``: a full
    ``mission_id`` (ULID), an 8-char ``mid8`` prefix, a numeric prefix
    (``083``), a human slug (``foo-bar``), or the canonical ``<slug>-<mid8>``
    directory name. This is the single place where the mid8/ULID/numeric →
    canonical-slug disambiguation happens for the read path, so every read-path
    caller resolves a ``--mission <mid8>`` identically to ``--mission
    <full-slug>`` (F-001 / F-003 / F-004).

    The already-resolved ``feature_dir`` is carried alongside the canonical
    pair (parse, don't re-derive): for backfilled missions whose directory name
    lacks the ``-<mid8>`` suffix, recomposing ``<slug>-<mid8>`` double-suffixes
    and misses the real directory the resolver already located.

    Returns ``None`` when the handle resolves to no identity-bearing mission
    (e.g. a brand-new scaffold whose ``meta.json`` has no ``mission_id`` yet, or
    a legacy mission) so the caller falls back to literal-slug path composition
    without changing pre-existing behaviour (C-004 strangler: additive only).

    Raises:
        MissionSelectorAmbiguous: When the handle matches more than one mission
            (C-CTX-4 / C-009 no-silent-fallback).
    """
    # Late import: ``context.mission_resolver`` pulls in heavier modules and we
    # must not pay that cost on the pure-path happy path (canonical slug already
    # points at an existing directory — handled by the caller before this runs).
    from specify_cli.context.mission_resolver import (
        AmbiguousHandleError,
        MissionNotFoundError,
        resolve_mission,
    )

    try:
        resolved = resolve_mission(handle, repo_root)
    except AmbiguousHandleError as exc:
        raise MissionSelectorAmbiguous(
            handle=handle,
            candidates=[c.mission_slug for c in exc.candidates],
        ) from exc
    except MissionNotFoundError:
        return None
    return resolved.mission_slug, resolved.mid8, resolved.feature_dir


def _resolve_mission_read_path(
    repo_root: Path,
    mission_slug: str,
    mid8: str,
    *,
    require_exists: bool = False,
    coordination_branch: str | None = None,
    topology: MissionTopology | None = None,
) -> Path:
    """Return the directory containing this mission's status read surface.

    Priority:

    1. Coordination worktree (new topology) — chosen when its directory
       exists on disk.  This is the canonical reader path for any
       mission whose ``meta.json`` carries ``coordination_branch``.
    2. Primary checkout view — chosen when no coord worktree exists.
       This serves legacy missions and the transitional window between
       ``mission create`` and the first coord-worktree materialisation.

    The function is **pure-path on the happy path**: it does not touch
    git, does not spawn subprocesses, and does not invoke any heavy
    lookup that would meaningfully extend the cost of a status read.
    It performs at most one filesystem stat per candidate.

    Args:
        repo_root: Absolute repository root (primary checkout).
        mission_slug: Mission slug, either bare human form or
            ``<human>-<mid8>`` (post-WP03).  The resolver normalises.
        mid8: 8-character mission disambiguator; may be empty for
            legacy missions that never minted a ``mission_id``.
        require_exists: When ``True``, raise
            :class:`StatusReadPathNotFound` if neither candidate exists
            on disk.  Defaults to ``False`` so the caller can decide
            how to render the diagnostic.
        topology: The WP02 **stored** :class:`MissionTopology`, read ONCE from
            ``primary_meta`` at the :func:`resolve_handle_to_read_path` boundary
            and threaded down (FR-006). A coord-less stored topology resolves
            PRIMARY regardless of a stale ``-coord`` husk; ``None`` falls back to
            the legacy probe-based derivation once.

    Returns:
        Absolute path to the mission directory containing
        ``status.events.jsonl`` / ``status.json``.

    Raises:
        ValueError: When ``mission_slug`` is not a safe path segment
            (traversal guard — FR-001 / NFR-002).
        StatusReadPathNotFound: When ``require_exists`` is ``True`` and
            neither the coord worktree nor the primary checkout carries
            the mission directory.
        MissionSelectorAmbiguous: When ``mission_slug`` is a handle (mid8 /
            numeric prefix / human slug) that matches more than one mission
            (C-CTX-4 / C-009 — structured error, never a silent wrong path).
    """
    # Guard FIRST — before any path composition (NFR-002 / FR-001).
    # Function-local import: ``core.paths`` → ``_read_path_resolver`` is safe
    # (no cycle), but the existing ``get_main_repo_root`` import at ~:413 also
    # uses a local import as a deliberate cycle-break pattern; matching that
    # style keeps the two primitives consistent.
    from specify_cli.core.paths import assert_safe_path_segment
    from specify_cli.lanes.branch_naming import mid8_from_slug

    assert_safe_path_segment(mission_slug)

    # Bare human slug → composed ``<slug>-<mid8>`` dir name (#2050 read mirror,
    # FR-004): a bare slug whose on-disk primary dir carries the canonical
    # ``<slug>-<mid8>`` name is rewritten ONCE through the shared bare-modern fold
    # so the surface leg (via ``candidate_feature_dir_for_mission``) and the guarded
    # seam converge on the composed name. When the slug is rewritten, re-derive the
    # mid8 from the composed name so the empty bare-slug mid8 does not persist.
    canonical_bare = _canonicalize_bare_modern_handle(repo_root, mission_slug)
    if canonical_bare != mission_slug:
        mission_slug = canonical_bare
        if not mid8:
            mid8 = mid8_from_slug(mission_slug)

    # First attempt: treat ``mission_slug`` as a literal directory name. This is
    # the pure-path happy path — when the canonical ``<slug>-<mid8>`` directory
    # exists we never touch the (heavier) handle resolver.
    literal = _resolve_existing_for_slug(
        repo_root, mission_slug, mid8, topology=topology
    )
    if literal is not None:
        return literal

    # Nothing on disk for the literal slug. The slug may actually be a *handle*
    # the operator typed (a bare mid8 like ``01KTPKST``, a full ULID, a numeric
    # prefix, or a human slug). Resolve it canonically so ``--mission <mid8>``
    # locates the same directory as ``--mission <full-slug>`` (F-001/F-003/F-004).
    # Ambiguity raises MissionSelectorAmbiguous (no silent fallback, C-CTX-4).
    canonical = _canonicalize_handle(repo_root, mission_slug)
    if canonical is not None:
        canonical_slug, canonical_mid8, canonical_dir = canonical
        if (canonical_slug, canonical_mid8) != (mission_slug, mid8):
            resolved = _resolve_existing_for_slug(
                repo_root, canonical_slug, canonical_mid8, topology=topology
            )
            if resolved is not None:
                return resolved
        if (
            _compose_mission_dir(canonical_slug, canonical_mid8) != canonical_dir.name
            and canonical_dir.exists()
        ):
            # Backfilled mission: the directory name lacks the ``-<mid8>``
            # suffix, so the recomposed ``<slug>-<mid8>`` candidate above
            # double-suffixes and misses. The handle resolver already located
            # the real directory — trust it (parse, don't re-derive). When the
            # composed name MATCHES the directory name, ``canonical_dir`` is
            # the same primary candidate ``_resolve_existing_for_slug`` just
            # evaluated, so returning it here would bypass the fail-closed
            # coord check — fall through to the diagnostic path instead.
            return canonical_dir
        mission_slug, mid8 = canonical_slug, canonical_mid8

    # Neither the literal slug nor a canonical handle resolved to an existing
    # directory. Fall through to the diagnostic / not-found path below using the
    # best-known (possibly canonicalised) slug + mid8. ``coordination_branch`` (when
    # the caller read it from the primary ``meta.json``) lets the fail-closed tail
    # split UNMATERIALIZED from DELETED (WP05 / T022).
    return _resolve_not_found(
        repo_root,
        mission_slug,
        mid8,
        require_exists=require_exists,
        coordination_branch=coordination_branch,
        topology=topology,
    )


def _resolve_not_found(
    repo_root: Path,
    mission_slug: str,
    mid8: str,
    *,
    require_exists: bool,
    coordination_branch: str | None = None,
    topology: MissionTopology | None = None,
) -> Path:
    """Handle the not-found / fail-closed / diagnostic tail of resolution.

    ``_resolve_existing_for_slug`` has already returned any *safely-existing*
    directory; reaching here means either (a) nothing exists for the (possibly
    canonicalised) slug, or (b) the coord worktree root is materialised but its
    mission dir is absent (the EMPTY state) / the declared coord branch has been
    DELETED from git. The read-path coord discriminator (WP05 / T022) folds those
    last two conditions onto WP01's shared :func:`probe_coord_state` so the read
    path converges with the canonical surface for the whole fail-closed family:

    * ``DELETED`` (coord root absent AND the declared ``coordination_branch`` is
      gone from git) — data loss; hard-fail :class:`CoordinationBranchDeleted`
      (``COORDINATION_BRANCH_DELETED``), the same loud verdict the surface raises
      (#1848 / FR-005). The branch signal is required, so ``DELETED`` is only
      reachable when ``coordination_branch`` is supplied by
      :func:`resolve_handle_to_read_path` (which read it from the primary
      ``meta.json``).
    * ``EMPTY`` (coord root materialised, mission dir absent — #1716) — adopt
      WP04's Option B: the PRIMARY checkout is authoritative, so return the
      primary candidate instead of failing closed. This inverts the historical
      #1718 stale-surface guard for the materialised-but-empty case and drains
      the read-path leg of the ``coord-empty`` equivalence cells. The surface
      already returns PRIMARY here (with a loud warning); the read path now
      agrees.
    * ``UNMATERIALIZED`` / ``NONE`` — the declared-but-not-yet-created window
      (#1718): the primary checkout stays authoritative, so a genuine absence
      under ``require_exists`` still raises :class:`StatusReadPathNotFound`.

    FR-006 (structural #2062): when the **stored** ``topology`` is coord-less
    (``SINGLE_BRANCH`` / ``LANES``) the husk-derived arms below (the DELETED
    hard-fail, the EMPTY probe, the legacy fail-closed band-aid) are structurally
    not consulted — the primary checkout is authoritative, so a stale ``-coord``
    husk cannot re-open #2062. A genuine absence under ``require_exists`` still
    raises.
    """
    mission_dir_name = _compose_mission_dir(mission_slug, mid8)
    primary_candidate: Path = repo_root / KITTY_SPECS_DIR / mission_dir_name

    # FR-006 (structural #2062 read-leg): a stored coord-less topology never
    # consults the on-disk coord husk — the primary checkout is authoritative.
    # FR-005: routed through the ONE canonical ``routes_through_coordination``
    # predicate (the absorbed boundary topology is already concrete here).
    from mission_runtime import routes_through_coordination

    if topology is not None and not routes_through_coordination(topology):
        if require_exists and not primary_candidate.exists():
            raise StatusReadPathNotFound(
                repo_root=repo_root,
                mission_slug=mission_slug,
                mid8=mid8 or "",
                coord_candidate=primary_candidate,
                primary_candidate=primary_candidate,
            )
        return primary_candidate

    coord_candidate: Path = primary_candidate
    coord_state = CoordState.NONE
    if mid8:
        # Shared compose + probe (paula C1/C2 + WP05 fold): build the coord
        # candidate via the single grammar and classify the topology state. The
        # branch (when supplied) splits UNMATERIALIZED from DELETED via the single
        # ``git rev-parse`` arm inside the probe — no 4th copy of the check.
        coord_candidate = coord_feature_dir(repo_root, mission_slug, mid8)
        coord_state = probe_coord_state(
            repo_root,
            mission_slug,
            mid8,
            coordination_branch=coordination_branch,
        )

    # #1848 / FR-005 (DELETED): a declared coord branch deleted from git carries
    # unmerged status — data loss, never a silent primary fallback. Hard-fail with
    # the SAME loud, distinct error the canonical surface raises so all legs
    # converge on ``CoordinationBranchDeleted`` / ``COORDINATION_BRANCH_DELETED``.
    # Only reachable when a ``coordination_branch`` was supplied (the git arm splits
    # UNMATERIALIZED from DELETED), which only ``resolve_handle_to_read_path`` does —
    # the lenient ``candidate_feature_dir_for_mission`` path supplies no branch, so
    # its behaviour is unchanged.
    if coord_state is CoordState.DELETED and coordination_branch is not None:
        # Late import breaks the cycle: ``coordination.surface_resolver`` imports
        # ``_compose_mission_dir`` / ``probe_coord_state`` from THIS module, so a
        # module-level import would deadlock when this resolver is the first entry
        # into the coordination package.
        from specify_cli.coordination.surface_resolver import (
            CoordinationBranchDeleted,
        )

        raise CoordinationBranchDeleted(
            repo_root=repo_root,
            mission_slug=mission_slug,
            mid8=mid8 or "",
            coordination_branch=coordination_branch,
            coord_candidate=coord_candidate,
            primary_candidate=primary_candidate,
        )

    # WP05 Option B (EMPTY) under the EXISTENCE-gated read: a materialised coord
    # root with no mission dir → PRIMARY is authoritative (the loud warning lives at
    # the surface). This inverts the #1718 stale-surface guard for the
    # materialised-but-empty case ONLY for ``require_exists=True`` — the contract the
    # equivalence gate and ``resolve_handle_to_read_path`` exercise. The lenient,
    # non-gated path keeps the historical fail-closed raise below so existing
    # ``candidate_feature_dir_for_mission`` callers (e.g. the ``mission run``
    # boundary's raw-passthrough on ``StatusReadPathNotFound``) are unchanged.
    if (
        require_exists
        and coord_state is CoordState.EMPTY
        and primary_candidate.exists()
    ):
        return primary_candidate

    # Fail-closed: primary exists but declares a coord branch whose materialised
    # worktree lacks the mission dir — reading primary would expose stale status.
    # (Preserves the historical non-gated behaviour for ``require_exists=False``.)
    # FR-006 / C-004: ``topology is None`` is now reached ONLY for a corrupt/
    # unreadable primary meta (every boundary absorbs the absent FIELD into a
    # concrete shape — WP06/WP17), so only THAT corrupt-meta arm still consults the
    # ``_declares_coordination_branch`` husk read; a concrete stored topology has
    # ALREADY decided the shape, so the husk is not the deciding signal.
    fail_closed = (
        topology is None
        and primary_candidate.exists()
        and bool(mid8)
        and coord_state is CoordState.EMPTY
        and _declares_coordination_branch(primary_candidate)
    )
    if fail_closed or require_exists:
        raise StatusReadPathNotFound(
            repo_root=repo_root,
            mission_slug=mission_slug,
            mid8=mid8 or "",
            coord_candidate=coord_candidate,
            primary_candidate=primary_candidate,
        )

    # Default: return the primary candidate so the caller can render its
    # own diagnostic (e.g. "Mission directory not found: <path>").
    return primary_candidate


def read_primary_meta(
    repo_root: Path, handle: str
) -> tuple[dict[str, object], bool]:
    """Return ``(primary_meta, declares_coordination)`` from the primary mission meta.

    Shared read-side primitive (FR-001): ``meta.json`` lives on the **primary
    checkout** (the coordination worktree's sparse policy excludes it), so the
    canonical identity is read there before the topology-aware read path is
    resolved. The primary dir is constructed via the sanctioned
    :func:`primary_feature_dir_for_mission` path primitive (it owns
    ``KITTY_SPECS_DIR`` assembly — ``test_no_raw_mission_spec_paths``).

    The returned ``primary_meta`` is the raw meta dict (empty when no primary meta
    exists — legacy mission, or a coord-only topology whose meta is not on this
    surface). It is fed verbatim to the shared :func:`resolve_declared_mid8`
    cascade, which treats an absent ``mid8`` / ``mission_id`` as "identity
    unproven" and DECLINES (returns ``""``) rather than seeding an empty identity
    (FR-011 / M3). The caller's ``declares_coordination`` topology gate then
    decides fail-closed vs. primary-read.

    Lifted from the orchestrator prototype ``orchestrator_api/commands.py``
    (≈:251) so the seam and the orchestrator share ONE primitive (NFR-004) rather
    than two parallel cascades.
    """
    from specify_cli.mission_metadata import load_meta

    primary_dir = primary_feature_dir_for_mission(repo_root, handle)
    meta = load_meta(primary_dir) or {}
    if not meta:
        # Non-composed handle (bare ``mid8``, full ULID, numeric prefix): the raw
        # handle does NOT name the on-disk ``<slug>-<mid8>`` directory, so the
        # topology-blind compose above misses the primary meta. Canonicalize the
        # handle to locate the real primary dir and re-read.  Without this, a
        # coord-topology mission addressed by a non-composed ``--mission`` handle
        # yields empty meta → ``coordination_branch`` is never learned → the
        # caller's coord gates (the M5 fail-closed gate AND the DELETED hard-fail)
        # are silently skipped and the leg leaks a STALE PRIMARY read of a mission
        # whose coord branch is gone (#1848 data-loss DIVERGENCE from the surface
        # leg, which canonicalizes first). Paid only on the raw-miss path, so the
        # composed-handle happy path keeps its pure-path cost.
        canonical = _canonicalize_handle(repo_root, handle)
        if canonical is not None:
            _, _, canonical_dir = canonical
            meta = load_meta(canonical_dir) or {}
    branch = meta.get("coordination_branch")
    declares_coordination = isinstance(branch, str) and bool(branch.strip())
    return meta, declares_coordination


def resolve_handle_to_read_path(
    repo_root: Path,
    handle: str,
    *,
    require_exists: bool = False,
) -> Path:
    """Resolve a mission *handle* to its topology-aware read-surface directory.

    THE single guarded read-side seam (IC-01; FR-001, FR-004, FR-005-invariant),
    lifted from the working orchestrator prototype
    (``orchestrator_api/commands.py:_resolve_mission_dir`` + ``_read_primary_meta``).
    Every read-side migration consumes this so exactly ONE definition exists
    (NFR-004).

    Body (the prototype pattern, in order):

    1. ``assert_safe_path_segment(handle)`` — the traversal guard fires FIRST,
       before any ``KITTY_SPECS_DIR`` join (FR-004 / NFR-002).
    2. Read the primary ``meta.json`` (:func:`read_primary_meta`) to learn the
       declared identity and whether the topology declares a coordination branch.
    3. ``resolve_declared_mid8(meta, handle)`` — the ONE sanctioned mid8 cascade
       (NFR-005): ``meta.mid8`` → ``resolve_mid8(meta.mission_id)`` →
       ``mid8_from_slug(handle)``. Returns ``""`` on exhaustion (no raise).
    4. Fail-closed coord-declared gate (M5): a coord topology whose primary
       declares ``coordination_branch`` while identity CANNOT be proven (empty
       ``mid8``) cannot be addressed against the coord worktree; reading primary
       would expose stale status, so raise the typed read-path error rather than
       silently fall back.
    5. Return :func:`_resolve_mission_read_path` — the **existence-gated** topology
       resolver.

    ROUTING INVARIANT (FR-005, #1718 trap — binding): step 5 routes through
    :func:`_resolve_mission_read_path`, which selects the coord surface ONLY when
    the coord worktree directory EXISTS on disk. It MUST NOT route through
    ``resolve_status_surface_with_anchor`` (or any composing surface): that
    composes and returns the coord path for an *unmaterialised* coord, so a
    declared-but-not-yet-created coord (the ``mission create`` → first
    coord-materialisation window) would regress to a non-existent coord path
    instead of the correct PRIMARY read. Deriving a non-empty ``mid8`` is
    ORTHOGONAL to the create-window→primary contract — a declared-but-unmaterialised
    coord with a perfectly good ``mid8`` still resolves PRIMARY because no worktree
    dir is on disk.

    ``require_exists`` is forwarded UNCHANGED to :func:`_resolve_mission_read_path`.
    Under ``require_exists=True`` the read-path leg adopts WP01's
    :func:`probe_coord_state` discriminator for the whole coord fail-closed family
    (WP05 / T022): ``DELETED`` hard-fails :class:`CoordinationBranchDeleted`
    (converging with the surface), ``EMPTY`` returns PRIMARY (WP04 Option B), and
    ``UNMATERIALIZED`` keeps the #1718 create-window primary read.

    Args:
        repo_root: Absolute repository root (primary checkout).
        handle: Mission handle — bare slug, ``<slug>-<mid8>``, full ``mission_id``,
            bare ``mid8``, or numeric prefix.
        require_exists: Forwarded to :func:`_resolve_mission_read_path`; when
            ``True``, a genuine absence raises :class:`StatusReadPathNotFound`.

    Returns:
        Absolute path to the mission directory containing the status read surface.

    Raises:
        ValueError: When ``handle`` is not a safe path segment (traversal guard).
        StatusReadPathNotFound: Coord-declared topology with an unprovable
            identity (fail-closed gate), or — when ``require_exists`` is ``True`` —
            a genuine absence.
        CoordinationBranchDeleted: When ``require_exists`` is ``True`` and the
            declared ``coordination_branch`` has been DELETED from git while the
            coord worktree is absent (#1848 data-loss — never a silent stale
            primary read; converges with the canonical surface).
        MissionSelectorAmbiguous: When ``handle`` matches more than one mission
            (propagated unchanged — no silent first-match, C-CTX-4 / C-009).
    """
    from specify_cli.coordination.surface_resolver import resolve_declared_mid8
    from specify_cli.core.paths import assert_safe_path_segment

    # 1. Guard FIRST — before any KITTY_SPECS_DIR join / primary-meta probe.
    assert_safe_path_segment(handle)

    # 1b. Bare human slug → composed ``<slug>-<mid8>`` dir name (#2050 read mirror,
    #     FR-004 bare-human-slug quirk): when the operator typed a bare human slug
    #     whose on-disk primary dir carries the canonical ``<slug>-<mid8>`` name,
    #     the downstream literal-slug compose AND the primary-meta probe would miss
    #     the real dir (so the stored topology would be lost and the husk leak back).
    #     Canonicalize the handle ONCE here (the SAME bare-modern primitive the
    #     aggregate's ``_find_meta_path`` uses — NFR-004) so every downstream leg
    #     (primary-meta probe, mid8 cascade, topology read, existence-gated
    #     resolver) operates on the composed name.
    handle = _canonicalize_bare_modern_handle(repo_root, handle)

    # 2-3. Primary-meta probe → the ONE sanctioned mid8 cascade (returns "" on
    #      exhaustion; the raise decision is the topology gate below).
    primary_meta, declares_coordination = read_primary_meta(repo_root, handle)
    mid8 = resolve_declared_mid8(primary_meta, handle)

    # FR-004 (T015 — the read-path BOUNDARY absorption): acquire a **concrete**,
    # non-optional :class:`MissionTopology` from the SAME ``primary_meta`` dict
    # already in hand (no second meta.json read). The stored ``topology`` is
    # authoritative when present; the absent-field case (un-backfilled legacy /
    # flattened mission) is ABSORBED — classified ONCE via WP01's single authority
    # from ``coordination_branch`` + the lanes signal — so the downstream resolver
    # chain is threaded a concrete value and the ``topology is None`` husk-arms are
    # structurally dead (WP17 removes them). A flattened mission (no
    # ``coordination_branch``) classifies to SINGLE_BRANCH/LANES → PRIMARY, NOT the
    # stale-coord husk (the #2062 / NFR-002 close, extended to un-backfilled
    # missions). C-004 boundary discipline: only the absent FIELD is absorbed here;
    # the corrupt/unreadable-meta arm stays the callers' separate typed path.
    stored_topology = classify_from_meta(
        primary_meta, primary_feature_dir_for_mission(repo_root, handle)
    )
    # A concrete coord-routing topology consults the coord husk; an absorbed
    # coord-less topology resolves PRIMARY (the #2062 close). ``None`` is the
    # absent/unreadable-meta legacy arm — preserve the historical husk-consulting
    # probe fallback (C-004 / FR-003). FR-005: the coord-routing decision flows
    # through the ONE canonical ``routes_through_coordination`` predicate (None-
    # guarded here, since the legacy ``None`` arm is the corrupt-meta fallback, not
    # a stored coord-routing classification).
    from mission_runtime import routes_through_coordination

    consults_coord_husk = stored_topology is None or routes_through_coordination(
        stored_topology
    )

    # 4. M5 fail-closed: a coord-declared topology with an unprovable identity
    #    must not silently read a stale primary view. FR-006: only a stored
    #    coord-routing topology (or un-backfilled legacy) consults the declared-
    #    coord signal; a stored coord-less topology resolves PRIMARY, so a residual
    #    ``coordination_branch`` husk does not fail it closed (the husk is
    #    structurally not consulted — #2062 cannot re-open).
    if not mid8 and declares_coordination and consults_coord_husk:
        primary_candidate = primary_feature_dir_for_mission(repo_root, handle)
        raise StatusReadPathNotFound(
            repo_root=repo_root,
            mission_slug=handle,
            mid8="",
            coord_candidate=primary_candidate,
            primary_candidate=primary_candidate,
        )

    raw_coord_branch = primary_meta.get("coordination_branch")
    coordination_branch = (
        str(raw_coord_branch).strip()
        if isinstance(raw_coord_branch, str) and raw_coord_branch.strip()
        else None
    )

    # 4b. DELETED hard-fail (WP05 / T022, FR-005): the coord worktree is absent AND
    #     the declared coordination branch has been DELETED from git. Probe the
    #     shared discriminator BEFORE the existence-gated resolver — for a
    #     coord-deleted topology the PRIMARY mission dir still exists on disk, so
    #     :func:`_resolve_mission_read_path` would otherwise hand back that stale
    #     primary view before the fail-closed tail runs. Hard-fail with the SAME
    #     loud, distinct error the canonical surface raises so every leg converges
    #     on ``CoordinationBranchDeleted`` / ``COORDINATION_BRANCH_DELETED`` — never
    #     a silent stale-primary read of a mission whose coord branch (carrying
    #     unmerged status) is gone (#1848 data-loss carve-out). Gated on
    #     ``require_exists`` so the lenient ``candidate_feature_dir_for_mission``
    #     diagnostic path keeps its primary-candidate return.
    if (
        require_exists
        and mid8
        and coordination_branch is not None
        and consults_coord_husk
    ):
        from specify_cli.coordination.surface_resolver import (
            CoordinationBranchDeleted,
        )

        if (
            probe_coord_state(
                repo_root, handle, mid8, coordination_branch=coordination_branch
            )
            is CoordState.DELETED
        ):
            composed_coord = coord_feature_dir(repo_root, handle, mid8)
            raise CoordinationBranchDeleted(
                repo_root=repo_root,
                mission_slug=handle,
                mid8=mid8,
                coordination_branch=coordination_branch,
                coord_candidate=composed_coord,
                primary_candidate=primary_feature_dir_for_mission(repo_root, handle),
            )

    # 5. Existence-gated topology resolver — NEVER resolve_status_surface_with_anchor
    #    (#1718: that composes the coord path for an unmaterialised coord). The
    #    require_exists flag is forwarded unchanged (WP04 depends on it). The
    #    declared ``coordination_branch`` is threaded down so the EMPTY fail-closed
    #    tail can adopt Option B (PRIMARY) and the DELETED tail can hard-fail when a
    #    direct ``_resolve_mission_read_path`` caller supplies the branch (WP05 /
    #    T022 — converges with the surface).
    return _resolve_mission_read_path(
        repo_root,
        handle,
        mid8,
        require_exists=require_exists,
        coordination_branch=coordination_branch,
        topology=stored_topology,
    )


def resolve_surface_dir_or_typed_error(
    repo_root: Path,
    mission_slug: str,
    *,
    on_missing_meta: Path,
) -> Path:
    """Resolve the authoritative status-surface DIRECTORY, or raise the typed error.

    The single **resolve-dir-or-typed-error delegator** (FR-009/T4): wraps the
    canonical :func:`resolve_status_surface` so the two historically-duplicated
    wrappers — ``status.aggregate.MissionStatus._resolve_read_dir`` (WP04) and
    ``mission_runtime.resolution._resolve_status_surface_dir`` (WP05) — collapse
    onto ONE resolution body. Both wrappers re-point here in their owning WPs.

    Reconciled fallback / exception policy (the two old wrappers DIFFERED; this
    is the chosen union, documented per the WP03 DoD):

    * **Surface fail-closed** — ``resolve_status_surface`` raises
      :class:`StatusReadPathNotFound` (coord worktree materialised but its
      mission dir is absent, #1718/#1589): this is propagated UNCHANGED. Each
      caller translates it to its own boundary type (aggregate →
      ``CoordAuthorityUnavailable``; mission_runtime → ``ActionContextError``)
      — the delegator does NOT pick one translation, because the typed-error
      convergence is WP06's job (the equivalence matrix's ``coord-empty`` /
      ``coord-deleted`` cells stay RED until then). Propagating the raw
      ``StatusReadPathNotFound`` keeps the ``error_code`` intact for either
      translation.
    * **Meta absent / malformed** — ``resolve_status_surface`` raises
      :class:`FileNotFoundError` (no ``meta.json`` yet: the create→first-write
      window) or :class:`ValueError` (malformed slug/meta). The UNION of the two
      old wrappers caught both; this delegator catches both and returns the
      caller-supplied ``on_missing_meta`` directory. The two old wrappers
      differed only in HOW they spelled that primary fallback (aggregate passed
      a pre-computed ``primary_candidate``; mission_runtime recomputed
      ``candidate_feature_dir_for_mission``) — the ``on_missing_meta`` parameter
      lets each caller keep its own spelling while sharing this body.
    * **Success** — returns ``surface.parent`` (the directory containing
      ``status.events.jsonl``), the value both old wrappers returned.

    The unmaterialised-coord gate that ``aggregate._resolve_read_dir`` applies
    (``is_under_worktrees_segment(dir) and not dir.exists()`` →
    ``primary_candidate``) is intentionally NOT folded in here: it is a second,
    aggregate-specific authority decision layered ON TOP of resolution, so it
    stays at the aggregate call site (WP04) where ``on_missing_meta`` already
    carries the primary candidate.

    Args:
        repo_root: Absolute repository root (primary checkout).
        mission_slug: Mission slug or handle (resolved by the surface authority).
        on_missing_meta: Directory to return when no identity-bearing
            ``meta.json`` exists yet (the primary checkout is authoritative in
            the create→first-write window).

    Returns:
        Absolute path to the mission directory containing the status surface.

    Raises:
        StatusReadPathNotFound: When the surface authority fails closed (coord
            worktree materialised without its mission dir). Propagated unchanged
            so each caller applies its own typed-error translation.
        MissionSelectorAmbiguous: When ``mission_slug`` is an ambiguous handle
            (propagated unchanged — no silent first-match, C-CTX-4 / C-009).
    """
    from specify_cli.coordination.surface_resolver import resolve_status_surface

    try:
        surface: Path = resolve_status_surface(repo_root, mission_slug)
    except (FileNotFoundError, ValueError):
        return on_missing_meta
    return surface.parent


def candidate_feature_dir_for_mission(repo_root: Path, mission_slug: str) -> Path:
    """Return the topology-aware mission-dir candidate without requiring it exist.

    This is the **single read primitive** (C-005 / FR-002): it delegates to
    :func:`_resolve_mission_read_path`, deriving ``mid8`` once from the slug. The
    historical ``missions.feature_dir_resolver`` shim that re-exported this
    function was retired in WP07 (FR-007); every caller now imports it from this
    canonical module directly.

    Because it routes through :func:`_resolve_mission_read_path`, a bare ``mid8``
    handle (e.g. ``01KTPKST``) resolves to the same directory as the full slug
    (F-001/F-003/F-004) for every one of the 30+ callers, not just the read-side
    CLI commands.

    FR-006 (structural #2062 — the surface/aggregate read-leg close): this
    primitive feeds the canonical surface resolver
    (:func:`coordination.surface_resolver.resolve_status_surface_with_anchor`)
    AND the aggregate's ``MissionStatus._find_meta_path``. Both legs are the ones
    ``agent status`` / kanban / dep-gate / review-claim actually use. So this
    primitive reads the WP02 **stored** ``topology`` from the primary ``meta.json``
    ONCE (via the SAME :func:`read_primary_meta` / :func:`stored_topology_from_meta`
    seam the guarded :func:`resolve_handle_to_read_path` leg uses — NOT a fresh
    ``coordination_branch is None`` re-inference) and threads it into the
    existence-gated resolver. A mission whose stored topology is coord-less
    (``SINGLE_BRANCH`` / ``LANES``) therefore resolves PRIMARY **regardless** of a
    stale, registered, meta-bearing ``-coord`` husk on disk — the husk is
    structurally not consulted, so a prior flatten that left a husk cannot re-open
    #2062 on these legs. A coord-routing stored topology (or an un-backfilled
    legacy mission, ``topology is None``) keeps its historical husk-consulting
    behaviour (C-006), so a genuine coord mission still reads the coord worktree.

    Like the historical implementation it never raises ``StatusReadPathNotFound``
    on a missing directory — it returns the best-known primary candidate so the
    caller can render its own diagnostic. It DOES propagate
    :class:`MissionSelectorAmbiguous` (C-CTX-4 / C-009 — an ambiguous selector is
    a structured error, never a silent wrong-but-plausible directory).
    """
    from specify_cli.lanes.branch_naming import mid8_from_slug

    # FR-006: read the WP02 stored topology ONCE from primary meta so a coord-less
    # mission resolves PRIMARY before any on-disk husk probe can land on the
    # registered ``-coord`` husk (the surface/aggregate read-leg #2062 close). This
    # mirrors how :func:`resolve_handle_to_read_path` already reads it. T015 absorbs
    # the absent ``topology`` FIELD into a concrete value at this boundary too, so a
    # flattened mission resolves PRIMARY even un-backfilled (FR-004). The read stays
    # resilient: a malformed/unreadable meta → ``None`` → the legacy probe fallback
    # (the C-004 corrupt-meta path), preserving the historical contract that this
    # primitive never raised on a bad ``meta.json`` (the diagnostic belongs to each
    # caller, not to dir resolution).
    stored_topology = _stored_topology_best_effort(repo_root, mission_slug)

    return _resolve_mission_read_path(
        repo_root,
        mission_slug,
        mid8_from_slug(mission_slug),
        topology=stored_topology,
    )


def _stored_topology_best_effort(
    repo_root: Path, mission_slug: str
) -> MissionTopology | None:
    """Read the WP02 **stored** topology from primary meta, degrading on error.

    The resilient topology read for :func:`candidate_feature_dir_for_mission` (the
    surface/aggregate read primitive): it canonicalizes the handle through the SAME
    bare-modern fold first (so the bare-human-slug whose on-disk primary dir carries
    the composed ``<slug>-<mid8>`` name lands on the real dir for EVERY handle form,
    rather than a bare-slug miss that would lose the stored topology and leak the
    husk), then reads the stored ``topology`` via the canonical
    :func:`read_primary_meta` / :func:`stored_topology_from_meta` seam.

    T015 (FR-004): the **absent** ``topology`` field is ABSORBED into a concrete
    topology here via :func:`classify_from_meta` (the read-path boundary discipline)
    — a flattened mission classifies SINGLE_BRANCH/LANES → PRIMARY even un-backfilled,
    so the surface/aggregate leg no longer leaks the husk on the legacy arm.

    A malformed / unreadable ``meta.json`` (where the meta cannot be READ at all) is
    mapped to ``None`` (the C-004 corrupt-meta path — the historical probe-based husk
    derivation runs once), NOT a raise: this primitive must preserve its historical
    contract of never raising on a bad meta, leaving the malformed-meta diagnostic to
    each caller. ``ValueError`` is the malformed-JSON signal
    :func:`mission_metadata.load_meta` emits; ``OSError`` covers an unreadable file.
    The absent FIELD (classify) and the corrupt META (degrade to ``None``) stay
    DISTINCT paths (C-004). :class:`MissionSelectorAmbiguous` is NOT caught — an
    ambiguous handle must propagate as the structured no-silent-fallback error
    (C-CTX-4 / C-009).
    """
    try:
        canonical_handle = _canonicalize_bare_modern_handle(repo_root, mission_slug)
        primary_meta, _ = read_primary_meta(repo_root, canonical_handle)
    except (ValueError, OSError):
        return None
    primary_dir = primary_feature_dir_for_mission(repo_root, canonical_handle)
    return classify_from_meta(primary_meta, primary_dir)


def primary_feature_dir_for_mission(repo_root: Path, mission_slug: str) -> Path:
    """Return the PRIMARY-checkout mission dir, deliberately topology-blind.

    The inverse companion of :func:`candidate_feature_dir_for_mission`: it does
    **NOT** route through :func:`_resolve_mission_read_path`, because the
    topology-aware resolver selects the coordination worktree once one exists —
    which is exactly the surface that lacks ``meta.json`` (it lives on the
    primary checkout). Callers that must read primary-anchored metadata
    (e.g. ``finalize-tasks`` resolving the merge target, mission 01KTRC04
    FR-003) use this so the read is CWD/topology-invariant — the SAME anchoring
    ``mission_runtime.resolve_placement_only`` uses.

    Lives here (a sanctioned path-constructor module) so the construction stays
    inside the blessed owners of ``KITTY_SPECS_DIR`` path assembly enforced by
    ``tests/architectural/test_no_raw_mission_spec_paths.py``.

    Raises:
        ValueError: When ``mission_slug`` is not a safe path segment
            (traversal guard — FR-001 / NFR-002).
    """
    # Function-local import: ``core.paths`` is a dependency of this module
    # (already imported at module-top for ``get_main_repo_root`` in the
    # ``get_feature_target_branch`` helper in paths.py). Using a local import
    # here matches the existing ``get_main_repo_root`` local-import pattern
    # at this call site, keeping both primitives consistent (T003).
    from specify_cli.core.paths import assert_safe_path_segment, get_main_repo_root

    assert_safe_path_segment(mission_slug)
    primary_dir: Path = get_main_repo_root(repo_root) / KITTY_SPECS_DIR / mission_slug
    return primary_dir


def _canonicalize_primary_read_handle(repo_root: Path, handle: str) -> str:
    """Fold a mission *handle* to its canonical on-disk dir NAME for a PRIMARY read.

    The caller-side companion that keeps :func:`primary_feature_dir_for_mission`
    handle-blind (FR-011 / #2136). A PRIMARY-partition read of
    :func:`resolve_planning_read_dir` must land on the durable
    ``kitty-specs/<slug>-<mid8>/`` home for EVERY handle form the operator may type,
    but the topology-blind primitive composes the literal name verbatim — so a bare
    ``mid8`` / full ULID / numeric prefix / bare human slug would diverge onto a
    wrong literal dir.

    This composes the TWO existing read-path canonicalizers (NO parallel resolver —
    C-006), mirroring the live :func:`_resolve_mission_read_path` cascade:

    1. :func:`_canonicalize_bare_modern_handle` rewrites a bare *human slug* whose
       on-disk dir actually carries the composed ``<slug>-<mid8>`` name (the FR-004
       bare-human-slug fold). When it already embeds a ``mid8`` (the present-leg /
       unresolvable-leg short-circuits) the handle is returned unchanged.
    2. :func:`_canonicalize_handle` resolves the *identity* forms (bare ``mid8`` /
       ULID / numeric prefix) to the canonical ``(slug, mid8, feature_dir)`` and
       carries the already-located directory — so its NAME is the canonical dir name
       (parse, don't re-derive: a backfilled dir whose name lacks the ``-<mid8>``
       tail would double-suffix on recompose).

    Returns the canonical dir name when an identity form resolves, otherwise the
    bare-modern-folded handle (unchanged for an already-canonical or genuinely
    unresolvable handle — the back-compat no-op leg, NFR-005).

    Raises:
        MissionSelectorAmbiguous: When the handle matches more than one mission —
            propagated unchanged from :func:`_canonicalize_handle`; NEVER a silent
            pick (C-006 / C-009 / WP07 no-silent-fallback).
    """
    bare_folded = _canonicalize_bare_modern_handle(repo_root, handle)
    if bare_folded != handle:
        # A bare *human slug* was folded to its composed ``<slug>-<mid8>`` dir name.
        return bare_folded
    # Identity forms (bare mid8 / ULID / numeric prefix): the resolver carries the
    # already-located dir, so its NAME is the canonical dir name (parse, don't
    # re-derive). An ambiguous handle RAISES here (no silent pick).
    resolved = _canonicalize_handle(repo_root, handle)
    if resolved is not None:
        _, _, canonical_dir = resolved
        return canonical_dir.name
    # Genuinely unresolvable (no matching mission, no meta) — the back-compat no-op
    # leg: literal compose, byte-identical to the pre-FR-011 behaviour (NFR-005).
    return bare_folded


def resolve_planning_read_dir(
    repo_root: Path,
    mission_slug: str,
    *,
    kind: MissionArtifactKind,
) -> Path:
    """Resolve a mission dir for a *read* of one artifact ``kind`` (per-kind split).

    The kind-aware read seam (FR-006 / INV-4-5, WP04 — the #2062 stale-coord
    read-side close). After WP01 re-partitioned the planning + identity kinds onto
    the PRIMARY surface for BOTH read and write (INV-5 full symmetry), a planning
    artifact (``spec.md`` / ``tasks.md`` / ``tasks/WP*.md`` / ``data-model.md`` /
    ...) of a coordination-topology mission physically lives on the PRIMARY feature
    dir. The kind-blind lenient resolver
    (:func:`candidate_feature_dir_for_mission`) returns ONE dir by topology — for a
    coord-topology mission it returns the materialized ``-coord`` husk, where a
    stale pre-mission copy would SHADOW the real primary planning truth.

    This seam splits the read by the artifact's partition — the SAME single
    authority the write side uses, queried through the package-root public
    predicate :func:`mission_runtime.is_primary_artifact_kind` (NO parallel
    classification, NO private-submodule import — shared-package-boundary /
    C-006 / NFR-004):

    * a **PRIMARY-partition** kind (``is_primary_artifact_kind`` True) resolves
      PRIMARY regardless of topology, via the topology-blind
      :func:`primary_feature_dir_for_mission` primitive — mirroring the write-side
      INV-5 symmetry, so a stale ``-coord`` husk can never shadow it (#2062 close);
    * every other (STATUS-partition) kind keeps the topology-aware seam
      (:func:`candidate_feature_dir_for_mission`) and ALL its C-005 KEEP transients
      (#1718 create-window, #1848 coord-deleted) — the append-only event log stays
      on coordination for coord-topology missions (C-001), so a STATUS read still
      resolves the coord worktree.

    The classification is the single partition the write side already owns;
    flipping a kind across the partition is a one-line move in
    ``mission_runtime.artifacts`` (NFR-004), never a code change here.

    Args:
        repo_root: Absolute repository root (primary checkout).
        mission_slug: Mission slug or handle (resolved by the underlying primitive).
        kind: The artifact kind being READ — decides the partition.

    Returns:
        Absolute mission directory for that kind's read surface.

    Raises:
        ValueError: When ``mission_slug`` is not a safe path segment (traversal
            guard — propagated from the underlying primitive).
        MissionSelectorAmbiguous: When ``mission_slug`` is an ambiguous handle —
            propagated unchanged from the PRIMARY-leg caller-canonicalization
            (:func:`_canonicalize_primary_read_handle`, FR-011) or, for a
            STATUS-partition kind, from the topology-aware seam. No silent pick.
    """
    # Single partition authority (C-006 / NFR-004): the SAME partition the write
    # side keys on, queried through the package-root public predicate (NOT the
    # private ``_PRIMARY_ARTIFACT_KINDS`` submodule symbol — shared-package-boundary,
    # tests/architectural/test_mission_runtime_surface.py). Late import keeps the
    # read-path module's cold-start cost low and breaks any import cycle through
    # ``mission_runtime``.
    from mission_runtime import is_primary_artifact_kind

    if is_primary_artifact_kind(kind):
        # PRIMARY-partition read → topology-blind primary dir (INV-5 symmetry).
        # Caller-canonicalization (FR-011 / #2136): a bare ``mid8`` / human slug
        # does NOT name the on-disk ``<slug>-<mid8>`` dir, so passing the RAW handle
        # to the topology-blind primitive would literal-compose a DIVERGENT dir.
        # Fold the handle to its canonical dir NAME HERE — mirroring the live
        # caller-canonicalization exemplars ``:1204``/``:1208`` and ``:820`` — and
        # pass the canonical NAME DOWN to the blind compose. The primitive
        # ``primary_feature_dir_for_mission`` STAYS handle-blind by contract: folding
        # canonicalization into ITS body recurses forever (the shared canonicalizers
        # call the primitive). An ambiguous handle propagates ``MissionSelectorAmbiguous``
        # unchanged from :func:`_canonicalize_handle` — no silent pick (C-006 / C-009).
        canonical = _canonicalize_primary_read_handle(repo_root, mission_slug)
        return primary_feature_dir_for_mission(repo_root, canonical)
    # STATUS-partition read → topology-aware seam (C-001 / C-005 transients intact).
    return candidate_feature_dir_for_mission(repo_root, mission_slug)


def resolve_bare_modern_mission_dir_name(
    repo_root: Path, mission_slug: str
) -> str | None:
    """Resolve a *bare* modern slug to its on-disk ``<slug>-<mid8>`` dir NAME.

    The canonical home for the "bare human slug names a composed primary dir"
    resolution (#2050 read-side mirror). The operator may type a bare human slug
    (``demo-feature``) for a mission whose on-disk primary directory carries the
    canonical ``<slug>-<mid8>`` name (``demo-feature-01ABCDEF``) — e.g. before the
    coord worktree is materialized, when only the composed primary dir exists.
    The identity resolver (:func:`context.mission_resolver.resolve_mission`) keys
    on the directory NAME and so cannot map a bare slug onto a composed dir name;
    this primitive bridges that gap by scanning ``kitty-specs/<slug>-*/meta.json``
    for the single directory whose name carries a valid mid8 tail.

    Returns ``None`` when the handle already embeds a mid8 (not a bare slug), when
    ``kitty-specs/`` is absent, or when zero / multiple composed dirs match (the
    ambiguous case is deliberately declined here — a no-silent-pick contract; the
    caller keeps its existing behaviour). Pure-path: no git, one ``glob``.

    Shared seam (NFR-004): both ``status.aggregate.MissionStatus._find_meta_path``
    and the ``agent status`` CLI helper consume this one definition rather than
    re-implementing the glob.
    """
    from specify_cli.lanes.branch_naming import mid8_from_slug

    # A handle that already embeds a mid8 is NOT a bare slug — decline so the
    # caller's literal/canonical resolution stays authoritative.
    if mid8_from_slug(mission_slug):
        return None

    specs_dir = repo_root / KITTY_SPECS_DIR
    if not specs_dir.is_dir():
        return None

    matches: list[str] = [
        meta_path.parent.name
        for meta_path in sorted(specs_dir.glob(f"{mission_slug}-*/meta.json"))
        if mid8_from_slug(meta_path.parent.name)
    ]
    if len(matches) != 1:
        return None
    # ``Path.name`` is typed ``str``; the annotation above re-narrows the value
    # mypy widens to ``Any`` through the comprehension so this return is a plain
    # ``str`` (matches the ``_compose_mission_dir`` cast pattern in this module).
    return str(matches[0])


def resolve_feature_dir_for_slug(repo_root: Path, mission_slug: str) -> Path:
    """Resolve a mission directory **without** asserting it exists.

    This is the canonical, topology-aware, dir-only resolver for callers that
    already hold a mission slug and only need the read-side directory path —
    never raises on a missing directory (unlike
    :func:`resolve_feature_dir_for_mission`). It delegates to the single
    coord-aware path primitive (:func:`_resolve_mission_read_path`), so
    coordination topology is honoured exactly once.

    Relocated here from the retired ``missions.feature_dir_resolver`` shim
    (WP07/FR-007). The late imports keep importing this module from pulling in
    heavier modules during cold ``spec-kitty next`` startup.

    read-surface-ssot-closeout-01KWZV91/WP09 (FR-001, NFR-001): the last four
    production call sites (``materialize.py``, ``research.py``,
    ``validate_encoding.py``, ``workspace/context.py``) were routed onto
    ``placement_seam(...).read_dir(kind)`` — the kind-aware seam, not this
    kind-blind primitive. This function stays a genuine, still-exercised
    coord-aware primitive (dozens of tests call it directly to prove the
    coord-vs-primary split — see ``tests/retrospective/``,
    ``tests/integration/test_coord_loop_*``,
    ``tests/architectural/test_gate_read_literal_ban.py``), so it is NOT
    deleted — only dropped from ``__all__`` (below) since it no longer has a
    cross-module ``src/`` importer (the symbol-level dead-code gate,
    ``tests/architectural/test_no_dead_symbols.py``, requires one for an
    exported name). Direct qualified imports (``from ... import
    resolve_feature_dir_for_slug``) are unaffected by ``__all__`` membership.

    FR-004 (T015 boundary absorption, WP17): like
    :func:`candidate_feature_dir_for_mission`, this leg reads the WP02 stored
    topology ONCE and threads it down so the absent-``topology``-field case is
    ABSORBED to a concrete shape — a flattened mission resolves PRIMARY even
    un-backfilled, and the resolver's ``topology is None`` arm is reached ONLY for a
    corrupt/unreadable meta (the C-004 legacy probe fallback), never for a readable
    no-topology meta. The read stays resilient (the best-effort reader degrades a
    malformed meta to ``None``), preserving the never-raise contract.
    """
    from specify_cli.lanes.branch_naming import mid8_from_slug

    feature_dir: Path = _resolve_mission_read_path(
        repo_root,
        mission_slug,
        mid8_from_slug(mission_slug),
        topology=_stored_topology_best_effort(repo_root, mission_slug),
    )
    return feature_dir


def resolve_feature_dir_for_mission(
    repo_root: Path,
    mission_slug: str,
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> Path:
    """Resolve a mission directory through ``resolve_action_context``.

    Relocated here from the retired ``missions.feature_dir_resolver`` shim
    (WP07/FR-007). The late import of ``mission_runtime`` keeps the
    ``spec-kitty next`` query startup path light.
    """
    from mission_runtime import resolve_action_context

    context = resolve_action_context(
        repo_root=repo_root,
        action="tasks",
        feature=mission_slug,
        cwd=cwd,
        env=env,
    )
    return Path(context.feature_dir)


# ``coord_feature_dir``, ``probe_coord_state`` and ``CoordState`` are the WP01
# shared compose/probe helpers (paula C1/C2). They are exported because the
# coord-empty/coord-deleted convergence wired cross-module importers for them
# (``coordination.surface_resolver`` imports all three) — the symbol-level
# dead-code gate (``test_no_dead_symbols``) requires an ``__all__`` entry to have
# a cross-module caller, which now holds.
# ``resolve_feature_dir_for_slug`` is deliberately NOT exported here
# (read-surface-ssot-closeout-01KWZV91/WP09): its last cross-module ``src/``
# callers were routed onto ``placement_seam(...).read_dir(kind)`` (the
# kind-aware seam), so it no longer has a runtime importer outside this
# module — the symbol-level dead-code gate
# (``tests/architectural/test_no_dead_symbols.py``) requires one for any
# ``__all__`` member. The function itself is kept (not deleted): it remains a
# genuine coord-aware primitive that many tests import directly by qualified
# name (unaffected by ``__all__``) to exercise the coord-vs-primary split.
__all__ = [
    "CoordState",
    "MissionSelectorAmbiguous",
    "StatusReadPathNotFound",
    "candidate_feature_dir_for_mission",
    "coord_feature_dir",
    "primary_feature_dir_for_mission",
    "probe_coord_state",
    "resolve_bare_modern_mission_dir_name",
    "resolve_planning_read_dir",
    "resolve_feature_dir_for_mission",
    "resolve_handle_to_read_path",
    "resolve_surface_dir_or_typed_error",
]
