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
import json
from pathlib import Path


STATUS_READ_PATH_NOT_FOUND_CODE = "STATUS_READ_PATH_NOT_FOUND"
MISSION_AMBIGUOUS_SELECTOR_CODE = "MISSION_AMBIGUOUS_SELECTOR"
FEATURE_CONTEXT_UNRESOLVED_CODE = "FEATURE_CONTEXT_UNRESOLVED"


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
    meta_path = path / "meta.json"
    if not meta_path.exists():
        return False
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    branch = meta.get("coordination_branch") if isinstance(meta, dict) else None
    return isinstance(branch, str) and bool(branch.strip())


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
    repo_root: Path, mission_slug: str, mid8: str
) -> Path | None:
    """Return the on-disk mission directory for a *literal* slug, or ``None``.

    Applies the topology priority (coord worktree → primary checkout) using only
    filesystem stats, returning the first candidate that *safely* exists.

    Returns ``None`` when neither candidate exists OR when the fail-closed
    condition holds (coord worktree materialised + primary declares
    ``coordination_branch`` but the coord dir is absent) — in that case the
    caller's main path re-raises :class:`StatusReadPathNotFound` rather than
    handing back a stale primary view (#1718). Pure-path: no git, no subprocess.
    """
    mission_dir_name = _compose_mission_dir(mission_slug, mid8)
    coord_worktree_materialized = False
    has_coord_candidate = False
    if mid8:
        from specify_cli.coordination.workspace import CoordinationWorkspace

        coord_root: Path = CoordinationWorkspace.worktree_path(
            repo_root, mission_slug, mid8
        )
        coord_worktree_materialized = coord_root.exists()
        has_coord_candidate = True
        coord_candidate: Path = coord_root / KITTY_SPECS_DIR / mission_dir_name
        if coord_candidate.exists():
            return coord_candidate
    primary_candidate: Path = repo_root / KITTY_SPECS_DIR / mission_dir_name
    if primary_candidate.exists():
        if (
            has_coord_candidate
            and coord_worktree_materialized
            and _declares_coordination_branch(primary_candidate)
        ):
            # Fail-closed: defer to the caller's StatusReadPathNotFound path.
            return None
        return primary_candidate
    return None


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


def resolve_mission_read_path(
    repo_root: Path,
    mission_slug: str,
    mid8: str,
    *,
    require_exists: bool = False,
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

    assert_safe_path_segment(mission_slug)

    # First attempt: treat ``mission_slug`` as a literal directory name. This is
    # the pure-path happy path — when the canonical ``<slug>-<mid8>`` directory
    # exists we never touch the (heavier) handle resolver.
    literal = _resolve_existing_for_slug(repo_root, mission_slug, mid8)
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
                repo_root, canonical_slug, canonical_mid8
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
    # best-known (possibly canonicalised) slug + mid8.
    return _resolve_not_found(
        repo_root, mission_slug, mid8, require_exists=require_exists
    )


def _resolve_not_found(
    repo_root: Path,
    mission_slug: str,
    mid8: str,
    *,
    require_exists: bool,
) -> Path:
    """Handle the not-found / fail-closed / diagnostic tail of resolution.

    ``_resolve_existing_for_slug`` has already returned any *safely-existing*
    directory; reaching here means either (a) nothing exists for the (possibly
    canonicalised) slug, or (b) the fail-closed condition held (coord worktree
    materialised + primary declares ``coordination_branch`` but the coord dir is
    absent — #1718). Recompute the candidate paths for an actionable diagnostic.
    """
    mission_dir_name = _compose_mission_dir(mission_slug, mid8)
    primary_candidate: Path = repo_root / KITTY_SPECS_DIR / mission_dir_name
    coord_candidate: Path = primary_candidate
    coord_worktree_materialized = False
    if mid8:
        # Lazy import breaks the import cycle: ``coordination.__init__`` eagerly
        # imports ``surface_resolver``, which imports ``_compose_mission_dir``
        # from this module. A module-level import here would deadlock whenever
        # this resolver is the first entry point into the coordination package.
        from specify_cli.coordination.workspace import CoordinationWorkspace

        coord_root: Path = CoordinationWorkspace.worktree_path(
            repo_root, mission_slug, mid8
        )
        coord_worktree_materialized = coord_root.exists()
        coord_candidate = coord_root / KITTY_SPECS_DIR / mission_dir_name

    # Fail-closed: primary exists but declares a coord branch whose materialised
    # worktree lacks the mission dir — reading primary would expose stale status.
    fail_closed = (
        primary_candidate.exists()
        and bool(mid8)
        and coord_worktree_materialized
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
    5. Return :func:`resolve_mission_read_path` — the **existence-gated** topology
       resolver.

    ROUTING INVARIANT (FR-005, #1718 trap — binding): step 5 routes through
    :func:`resolve_mission_read_path`, which selects the coord surface ONLY when
    the coord worktree directory EXISTS on disk. It MUST NOT route through
    ``resolve_status_surface_with_anchor`` (or any composing surface): that
    composes and returns the coord path for an *unmaterialised* coord, so a
    declared-but-not-yet-created coord (the ``mission create`` → first
    coord-materialisation window) would regress to a non-existent coord path
    instead of the correct PRIMARY read. Deriving a non-empty ``mid8`` is
    ORTHOGONAL to the create-window→primary contract — a declared-but-unmaterialised
    coord with a perfectly good ``mid8`` still resolves PRIMARY because no worktree
    dir is on disk.

    ``require_exists`` is forwarded UNCHANGED to :func:`resolve_mission_read_path`
    (load-bearing for WP04's equivalence-matrix re-point: with
    ``require_exists=True`` the coord-empty / coord-deleted cells must still RAISE
    :class:`StatusReadPathNotFound`).

    Args:
        repo_root: Absolute repository root (primary checkout).
        handle: Mission handle — bare slug, ``<slug>-<mid8>``, full ``mission_id``,
            bare ``mid8``, or numeric prefix.
        require_exists: Forwarded to :func:`resolve_mission_read_path`; when
            ``True``, a genuine absence raises :class:`StatusReadPathNotFound`.

    Returns:
        Absolute path to the mission directory containing the status read surface.

    Raises:
        ValueError: When ``handle`` is not a safe path segment (traversal guard).
        StatusReadPathNotFound: Coord-declared topology with an unprovable
            identity (fail-closed gate), or — when ``require_exists`` is ``True`` —
            a genuine absence.
        MissionSelectorAmbiguous: When ``handle`` matches more than one mission
            (propagated unchanged — no silent first-match, C-CTX-4 / C-009).
    """
    from specify_cli.coordination.surface_resolver import resolve_declared_mid8
    from specify_cli.core.paths import assert_safe_path_segment

    # 1. Guard FIRST — before any KITTY_SPECS_DIR join / primary-meta probe.
    assert_safe_path_segment(handle)

    # 2-3. Primary-meta probe → the ONE sanctioned mid8 cascade (returns "" on
    #      exhaustion; the raise decision is the topology gate below).
    primary_meta, declares_coordination = read_primary_meta(repo_root, handle)
    mid8 = resolve_declared_mid8(primary_meta, handle)

    # 4. M5 fail-closed: a coord-declared topology with an unprovable identity
    #    must not silently read a stale primary view.
    if not mid8 and declares_coordination:
        primary_candidate = primary_feature_dir_for_mission(repo_root, handle)
        raise StatusReadPathNotFound(
            repo_root=repo_root,
            mission_slug=handle,
            mid8="",
            coord_candidate=primary_candidate,
            primary_candidate=primary_candidate,
        )

    # 5. Existence-gated topology resolver — NEVER resolve_status_surface_with_anchor
    #    (#1718: that composes the coord path for an unmaterialised coord). The
    #    require_exists flag is forwarded unchanged (WP04 depends on it).
    return resolve_mission_read_path(
        repo_root, handle, mid8, require_exists=require_exists
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
    :func:`resolve_mission_read_path`, deriving ``mid8`` once from the slug. The
    historical ``missions.feature_dir_resolver`` shim that re-exported this
    function was retired in WP07 (FR-007); every caller now imports it from this
    canonical module directly.

    Because it routes through :func:`resolve_mission_read_path`, a bare ``mid8``
    handle (e.g. ``01KTPKST``) resolves to the same directory as the full slug
    (F-001/F-003/F-004) for every one of the 30+ callers, not just the read-side
    CLI commands.

    Like the historical implementation it never raises ``StatusReadPathNotFound``
    on a missing directory — it returns the best-known primary candidate so the
    caller can render its own diagnostic. It DOES propagate
    :class:`MissionSelectorAmbiguous` (C-CTX-4 / C-009 — an ambiguous selector is
    a structured error, never a silent wrong-but-plausible directory).
    """
    from specify_cli.lanes.branch_naming import mid8_from_slug

    return resolve_mission_read_path(
        repo_root, mission_slug, mid8_from_slug(mission_slug)
    )


def primary_feature_dir_for_mission(repo_root: Path, mission_slug: str) -> Path:
    """Return the PRIMARY-checkout mission dir, deliberately topology-blind.

    The inverse companion of :func:`candidate_feature_dir_for_mission`: it does
    **NOT** route through :func:`resolve_mission_read_path`, because the
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
    coord-aware path primitive (:func:`resolve_mission_read_path`), so
    coordination topology is honoured exactly once.

    Relocated here from the retired ``missions.feature_dir_resolver`` shim
    (WP07/FR-007). The late imports keep importing this module from pulling in
    heavier modules during cold ``spec-kitty next`` startup.
    """
    from specify_cli.lanes.branch_naming import mid8_from_slug

    feature_dir: Path = resolve_mission_read_path(
        repo_root, mission_slug, mid8_from_slug(mission_slug)
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


__all__ = [
    "MissionSelectorAmbiguous",
    "StatusReadPathNotFound",
    "candidate_feature_dir_for_mission",
    "primary_feature_dir_for_mission",
    "resolve_bare_modern_mission_dir_name",
    "resolve_feature_dir_for_mission",
    "resolve_feature_dir_for_slug",
    "resolve_handle_to_read_path",
    "resolve_mission_read_path",
    "resolve_surface_dir_or_typed_error",
]
