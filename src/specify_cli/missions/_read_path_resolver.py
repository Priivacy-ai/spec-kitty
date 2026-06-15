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
    return coord_mission_dir_name(mission_slug, mid8=mid8)


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
        StatusReadPathNotFound: When ``require_exists`` is ``True`` and
            neither the coord worktree nor the primary checkout carries
            the mission directory.
        MissionSelectorAmbiguous: When ``mission_slug`` is a handle (mid8 /
            numeric prefix / human slug) that matches more than one mission
            (C-CTX-4 / C-009 — structured error, never a silent wrong path).
    """
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


def candidate_feature_dir_for_mission(repo_root: Path, mission_slug: str) -> Path:
    """Return the topology-aware mission-dir candidate without requiring it exist.

    This is the **single read primitive** (C-005 / FR-002): it delegates to
    :func:`resolve_mission_read_path`, deriving ``mid8`` once from the slug. The
    historical duplicate in :mod:`specify_cli.missions.feature_dir_resolver`
    re-exports this function (C-004 strangler: the canonical logic moved here;
    callers keep their import site until they are converted in later WPs).

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
    """
    from specify_cli.core.paths import get_main_repo_root

    primary_dir: Path = get_main_repo_root(repo_root) / KITTY_SPECS_DIR / mission_slug
    return primary_dir


__all__ = [
    "MissionSelectorAmbiguous",
    "StatusReadPathNotFound",
    "candidate_feature_dir_for_mission",
    "primary_feature_dir_for_mission",
    "resolve_mission_read_path",
]
