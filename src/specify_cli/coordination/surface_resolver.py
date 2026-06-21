"""Canonical status-surface resolver for Spec Kitty missions.

This module is the **sole** canonical authority for coord-vs-primary
status-surface selection (FR-001 / FR-007). Every mission-surface read routes
through :func:`resolve_status_surface_with_anchor` — directly, or via the
blessed ``resolve_surface_dir_or_typed_error`` delegator (aggregate /
``mission_runtime``) — so no secondary fallback or parallel resolution
mechanism survives outside this seam. ``coordination/status_transition.py``'s
former path-shape topology predicates (the #1900 5th selection site) now
delegate to :func:`classify_worktree_topology` / :func:`is_registered_coord_worktree`
here; the C-002 topology-ratchet allowlist entry that reserved them is drained
(tests/architectural/test_topology_resolution_boundary.py). Any contributor
reaching for a parallel resolution path should treat this constraint as
load-bearing (NFR-003 compliance boundary).

The coord-empty case (a materialized-but-empty coordination worktree) is now an
operator-decided **loud primary fallback** (Option B; FR-001 / FR-003 / #1716):
the resolver falls back to the primary checkout and proceeds, emitting a single
``logging.WARNING`` (:data:`_COORD_EMPTY_FALLBACK_WARNING`) that names the
stale-surface risk AND both operator recovery paths — flatten (drop
``coordination_branch`` from ``meta.json``) OR ``spec-kitty agent worktree
repair --mission <slug>``. It NEVER silently degrades: the warning makes the
fallback observable so an operator or orchestrating agent can intervene. The
decision is recorded in
``architecture/3.x/adr/2026-06-19-1-coord-empty-surface-fallback.md`` and bound
to this single resolver. (The sibling coord-*deleted* case stays a hard-fail —
:class:`CoordinationBranchDeleted`, #1848 — because a deleted branch carrying
unmerged status is data loss, not a degraded read.)

Coord-topology resolution happens **exactly once** (FR-036). The coord-aware
:func:`candidate_feature_dir_for_mission` resolver already returns the
coordination-worktree feature dir whenever that worktree is materialized on
disk; this module therefore never re-invokes that resolver on an
already-resolved root. The only remaining case it handles directly is the
transitional window where ``meta.json`` declares ``coordination_branch`` but
the coord worktree has not been materialized yet — there it composes the coord
path **once**, by hand, rather than resolving a second time. Re-running the
coord-aware resolver against a coord root nested
``.worktrees/<m>-coord/.worktrees/<m>-coord/…`` (the #1772 double-resolution
bug); building the path directly avoids that.
"""
from __future__ import annotations

import enum
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

from specify_cli.coordination.workspace import CoordinationWorkspace
from specify_cli.core.constants import KITTY_SPECS_DIR
from specify_cli.lanes.branch_naming import mid8_from_slug, resolve_mid8
from specify_cli.mission_metadata import load_meta
from specify_cli.missions._read_path_resolver import (
    CoordState,
    StatusReadPathNotFound,
    candidate_feature_dir_for_mission,
    coord_feature_dir,
    primary_feature_dir_for_mission,
    probe_coord_state,
)

__all__ = [
    "CoordinationBranchDeleted",
    "ResolvedStatusSurface",
    "WorktreeRegistryUnavailable",
    "WorktreeTopology",
    "classify_worktree_topology",
    "is_registered_coord_worktree",
    "is_under_worktrees_segment",
    "read_worktree_registry",
    "resolve_declared_mid8",
    "resolve_status_surface",
    "resolve_status_surface_with_anchor",
]

logger = logging.getLogger(__name__)

_WORKTREES_SEGMENT = ".worktrees"
_COORD_SUFFIX = "-coord"
_STATUS_EVENTS_FILENAME = "status.events.jsonl"

# Option B loud primary fallback (FR-001 / FR-003 / #1716): when the coordination
# worktree root is materialized but carries no mission dir, the resolver returns
# the PRIMARY checkout and emits this single ``logging.WARNING`` so the fallback
# is observable. The message names the stale-surface risk AND both operator
# recovery paths (flatten OR `spec-kitty agent worktree repair`); it is built once
# (paula C-warning-dup) and reuses the ADR recovery text. The ``{slug}`` /
# ``{coord_root}`` fields are filled at emit time.
_COORD_EMPTY_FALLBACK_WARNING = (
    "Coordination worktree for mission %(slug)r is materialized but carries no "
    "mission dir (coord root %(coord_root)s): falling back to the PRIMARY "
    "checkout, which may expose a stale, split-brain status surface. Recover by "
    "EITHER (a) flattening the mission — remove the `coordination_branch` key "
    "from meta.json so the primary checkout becomes authoritative — OR "
    "(b) recreating/populating the coordination worktree by running "
    "`spec-kitty agent worktree repair --mission %(slug)s`."
)


class WorktreeTopology(enum.Enum):
    """How a worktree path relates to a mission's commit destination.

    Produced ONLY by :func:`classify_worktree_topology`. No consumer may derive
    topology from path shape directly (C-SEAM-1): the ``-coord`` suffix and the
    ``.worktrees`` segment merely *propose*; the ``git worktree list
    --porcelain`` registry *disposes*.
    """

    PRIMARY = "primary"
    """The main checkout (not under a registered ``.worktrees`` entry)."""
    COORD_WORKTREE = "coord_worktree"
    """A registered ``<slug>-<mid8>-coord`` worktree."""
    LANE_WORKTREE = "lane_worktree"
    """A registered lane worktree (registered, but NOT coord)."""
    UNREGISTERED = "unregistered"
    """Under ``.worktrees`` but absent from the git registry (husk, F-005)."""


class WorktreeRegistryUnavailable(RuntimeError):
    """Raised when the git worktree registry cannot be read.

    Name proposes coord/lane topology; without the registry to dispose, the
    seam fails closed rather than guessing from path shape (NFR-003). Carries a
    stable ``error_code`` so callers route without string parsing.
    """

    error_code: str = "WORKTREE_REGISTRY_UNAVAILABLE"

    def __init__(self, *, repo_root: Path, detail: str) -> None:
        self.repo_root = repo_root
        self.detail = detail
        super().__init__(
            f"Could not read the git worktree registry at {repo_root}: {detail}. "
            "Topology cannot be determined from path shape alone; fail closed."
        )


# ``StatusReadPathNotFound`` resolves to ``Any`` under this project's mypy
# config because ``src/specify_cli/missions/`` is in the mypy ``exclude`` list
# (pyproject ``[tool.mypy] exclude``), so mypy cannot see the real base class
# and reports ``cannot subclass "Any"``. The subclass is correct and intended:
# every existing ``except StatusReadPathNotFound`` handler must keep catching
# R3 (fail-closed), while the distinct ``error_code`` lets callers route on the
# deleted-branch recovery. The mypy error is a config artifact, not a code
# defect — narrowly suppressed here with rationale per the project's
# suppression policy. The CI-authoritative invocation
# (``mypy --strict src/specify_cli src/charter src/doctrine``) resolves the base
# class normally, so ``[misc]`` does not fire there and would be reported as
# ``unused-ignore``; pairing both codes keeps the suppression silent under BOTH
# the single-file run (``[misc]``) and the full-package CI run (``[unused-ignore]``).
class CoordinationBranchDeleted(StatusReadPathNotFound):  # type: ignore[misc, unused-ignore]
    """#1889 row R3: ``coordination_branch`` is declared in ``meta.json`` but the
    branch no longer exists in git (deleted), and the coord worktree is absent.

    A deleted coord branch carrying unmerged status is *data loss*, not a
    degraded read — surfaced loudly with an actionable ``next_step`` and a
    distinct ``error_code`` so the resolver NEVER silently falls back to the
    primary checkout (composes with the #1848 status-transition carve-out).

    Subclasses :class:`StatusReadPathNotFound` so existing fail-closed handlers
    still catch it, while the distinct ``error_code`` / type lets callers that
    care surface the deleted-branch recovery path.
    """

    error_code: str = "COORDINATION_BRANCH_DELETED"

    def __init__(
        self,
        *,
        repo_root: Path,
        mission_slug: str,
        mid8: str,
        coordination_branch: str,
        coord_candidate: Path,
        primary_candidate: Path,
    ) -> None:
        self.coordination_branch = coordination_branch
        self.next_step = (
            f"The coordination branch {coordination_branch!r} declared in "
            f"meta.json no longer exists in git. Run `spec-kitty agent worktree "
            f"repair --mission {mission_slug}`, or flatten the mission by "
            f"removing the `coordination_branch` key from meta.json if the "
            f"coordination topology was intentionally torn down."
        )
        super().__init__(
            repo_root=repo_root,
            mission_slug=mission_slug,
            mid8=mid8,
            coord_candidate=coord_candidate,
            primary_candidate=primary_candidate,
        )

    def __str__(self) -> str:  # pragma: no cover - trivial formatting
        return (
            f"Coordination branch {self.coordination_branch!r} for mission "
            f"{self.mission_slug!r} is declared in meta.json but deleted from "
            f"git. {self.next_step}"
        )


def read_worktree_registry(repo_root: Path) -> frozenset[Path]:
    """Return resolved paths registered in ``git worktree list --porcelain``.

    The single authority for "is this path a registered worktree". Fails closed
    via :class:`WorktreeRegistryUnavailable` when git cannot be consulted —
    name-derived guessing is never substituted (NFR-003). Exemplar:
    ``cli/commands/doctor.py:~3063`` (the cache-once-per-pass pattern).

    Batch callers (dashboard scanner, status_service contract routing) read this
    once and pass the result as ``registry=`` to :func:`classify_worktree_topology`
    rather than re-shelling per path.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "worktree", "list", "--porcelain"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:  # git missing / not executable
        raise WorktreeRegistryUnavailable(repo_root=repo_root, detail=str(exc)) from exc
    if result.returncode != 0:
        detail = (
            result.stderr.strip()
            or result.stdout.strip()
            or f"exit {result.returncode}"
        )
        raise WorktreeRegistryUnavailable(repo_root=repo_root, detail=detail)
    registered: set[Path] = set()
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            raw = line[len("worktree ") :].strip()
            try:
                registered.add(Path(raw).resolve())
            except OSError:
                continue
    return frozenset(registered)


def is_under_worktrees_segment(path: Path) -> bool:
    """Return whether *path* lives under a ``.worktrees`` segment (shape only).

    The blessed home for the ``".worktrees" in parts`` idiom (C-SEAM-1). This is
    a pure *shape proposal* — it answers "does this path's layout look like a
    worktree path", NOT "is it a registered coord worktree". Contract-label
    consistency guards (status_service) use this; topology *routing* decisions
    must use :func:`is_registered_coord_worktree` / :func:`classify_worktree_topology`,
    which additionally consult the git registry so a husk cannot spoof the
    authority.
    """
    return _WORKTREES_SEGMENT in path.parts


def _enclosing_worktree_root(path: Path) -> Path | None:
    """Return the ``.worktrees/<name>`` ancestor of *path*, or ``None``.

    Walks the resolved path's parents looking for the first directory whose
    parent is the ``.worktrees`` segment. ``path`` itself is included so a
    worktree-root argument resolves to itself.
    """
    resolved = path.resolve(strict=False)
    for candidate in (resolved, *resolved.parents):
        if candidate.parent.name == _WORKTREES_SEGMENT:
            return candidate
    return None


def classify_worktree_topology(
    path: Path,
    *,
    repo_root: Path | None = None,
    registry: frozenset[Path] | None = None,
) -> WorktreeTopology:
    """Classify *path* against the git worktree registry (C-SEAM-1).

    The ``-coord`` suffix and ``.worktrees`` segment only *propose* topology;
    the registry *disposes*:

    * a path with no ``.worktrees`` ancestor → :attr:`WorktreeTopology.PRIMARY`;
    * a ``.worktrees/<name>`` ancestor that git registers and whose name ends in
      ``-coord`` → :attr:`WorktreeTopology.COORD_WORKTREE`;
    * a registered ``.worktrees`` ancestor that is NOT coord →
      :attr:`WorktreeTopology.LANE_WORKTREE`;
    * a ``.worktrees`` ancestor absent from the registry (husk, F-005) →
      :attr:`WorktreeTopology.UNREGISTERED`.

    Single git-registry read per call (or none when *registry* is injected).
    Callers that route many paths in one pass (status_service) MUST pass the
    cached *registry* set rather than re-shelling per path.

    Args:
        path: The path whose topology is classified.
        repo_root: Repo root for the registry read. Defaults to the first git
            checkout enclosing *path* — but injecting it (and *registry*) is
            preferred for batch callers.
        registry: An already-parsed porcelain set. When provided, NO git is
            consulted (the path is matched against it directly).

    Raises:
        WorktreeRegistryUnavailable: when *registry* is omitted and the git
            registry cannot be read — fail closed, never guess.
    """
    worktree_root = _enclosing_worktree_root(path)
    if worktree_root is None:
        return WorktreeTopology.PRIMARY

    if registry is None:
        root_for_registry = repo_root if repo_root is not None else path
        registry = read_worktree_registry(root_for_registry)

    if worktree_root not in registry:
        # Name proposes a worktree; the registry disposes: a husk (F-005).
        return WorktreeTopology.UNREGISTERED
    if worktree_root.name.endswith(_COORD_SUFFIX):
        return WorktreeTopology.COORD_WORKTREE
    return WorktreeTopology.LANE_WORKTREE


def is_registered_coord_worktree(
    path: Path,
    *,
    repo_root: Path | None = None,
    registry: frozenset[Path] | None = None,
) -> bool:
    """True iff *path* is inside a worktree that BOTH ends in ``-coord`` AND is
    registered in ``git worktree list --porcelain``.

    The ``-coord`` suffix only *proposes* coord topology; the porcelain registry
    *disposes*. A lane worktree, the primary checkout, or a husk (suffix
    present, not registered) returns ``False`` — killing the split-brain where a
    lane/husk path silently receives coord write-contract routing (#1589/#1821,
    F-005 husks).

    Convenience predicate over :func:`classify_worktree_topology`; see it for
    the ``repo_root`` / ``registry`` semantics and the fail-closed posture.
    """
    return (
        classify_worktree_topology(path, repo_root=repo_root, registry=registry)
        is WorktreeTopology.COORD_WORKTREE
    )


def _coord_branch_exists(repo_root: Path, coord_branch: str) -> bool:
    """Return whether *coord_branch* still exists in git (one rev-parse).

    Used to split #1889 row R2 (branch exists, worktree not yet materialized)
    from row R3 (branch DELETED). A registry read cannot tell these apart — only
    the ref existence does. Fails closed: when git is unreadable OR ``repo_root``
    is not a git repository at all, the branch is treated as present (R2/R2′
    path), because the materialization guard one level up still fail-closes; we
    never *invent* a deleted-branch error from a non-repo context.
    """
    try:
        inside = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--git-dir"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return True
    if inside.returncode != 0:
        # Not a git repository (e.g. an ad-hoc tmp dir): we cannot assert the
        # branch was deleted, so do not fire R3. Treat as present.
        return True
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--verify", "--quiet",
             f"refs/heads/{coord_branch}"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return True
    return result.returncode == 0


@dataclass(frozen=True)
class ResolvedStatusSurface:
    """Single-pass product of the canonical status-surface resolution.

    Carries both halves consumers need so neither re-derives the path (FR-005 /
    #1821):

    * ``surface_path`` — the canonical ``status.events.jsonl`` path (identical
      to :func:`resolve_status_surface`).
    * ``primary_anchor`` — the canonical primary feature-dir anchor
      (``candidate_feature_dir_for_mission``), the CWD-invariant authority the
      transaction-identity logic anchors on (#1737). Resolved exactly once and
      shared, so the historical validate-then-re-derive double resolution is
      gone.
    """

    surface_path: Path
    primary_anchor: Path

    @property
    def read_dir(self) -> Path:
        """Directory containing the resolved ``status.events.jsonl``."""
        return self.surface_path.parent


def resolve_declared_mid8(meta: dict[str, object], mission_slug: str) -> str:
    """Run the ONE sanctioned mid8 cascade; return ``""`` on exhaustion (no raise).

    This is the single canonical mid8-derivation seam (NFR-005, #1868): both
    :func:`_coord_mid8` and the orchestrator's ``_resolve_mission_dir`` consume it
    instead of re-deriving the tier logic. The *raise-on-exhaustion* decision is
    intentionally NOT made here — it belongs to each caller's topology gate (a
    coord-declared topology fails closed; a legacy non-coord mission keeps its
    primary-read path), so this helper returns ``""`` rather than raising.

    Cascade of declared sources (post-083 ``meta.json`` is authoritative):

    1. ``meta.mid8`` — an explicit declared disambiguator, used verbatim.
    2. :func:`resolve_mid8` keyed on the declared ``meta.mission_id`` — derives
       the mid8 from the declared identity (NOT a local ``[:8]`` slice, #1918) and
       trusts the slug's embedded tail only when it provably matches that declared
       identity.
    3. :func:`mid8_from_slug` — the seam's sanctioned best-effort heuristic, used
       ONLY as the final fallback once every *declared* source is exhausted. This
       layer fires for a mission whose canonical ``<slug>-<mid8>`` name embeds the
       real disambiguator but never persisted ``mid8`` / ``mission_id`` (e.g. a
       coord-only-with-tail topology).

    Returns:
        The 8-char mid8 when any tier resolves it, else ``""``.
    """
    raw_mid8 = meta.get("mid8")
    if raw_mid8:
        return str(raw_mid8)
    raw_mission_id = meta.get("mission_id")
    declared_mission_id = str(raw_mission_id) if raw_mission_id else None
    # Authoritative resolution: derive from the declared mission_id; declines a
    # coincidental slug tail when no declared identity confirms it.
    resolved: str = resolve_mid8(mission_slug, mission_id=declared_mission_id)
    if resolved:
        return resolved
    # Final fallback: no DECLARED source carries the disambiguator. The seam's
    # sanctioned heuristic reads the mid8 embedded in the canonical
    # ``<slug>-<mid8>`` name — the legitimate coord-topology mid8 for a mission
    # that declared a coordination_branch but never persisted mid8/mission_id.
    slug_mid8: str = mid8_from_slug(mission_slug)
    return slug_mid8


def _coord_mid8(meta: dict[str, object], mission_slug: str, repo_root: Path) -> str:
    """Derive the coord-worktree mid8 from declared authority, or fail closed.

    Runs the single sanctioned cascade (:func:`resolve_declared_mid8`) and applies
    THIS surface's own fail-closed contract: when every tier is exhausted the
    disambiguator is genuinely lost, and composing a coord path would mis-route to
    a wrong-but-plausible surface. Per the 3.x execution invariant ("raises rather
    than silently falling back on unresolvable context"; F-001), this raises
    :class:`StatusReadPathNotFound` instead of fabricating a mid8. (The
    orchestrator's read path makes its OWN topology-gated decision — see
    ``_resolve_mission_dir`` — so the raise lives here, not in the shared helper.)
    """
    mid8 = resolve_declared_mid8(meta, mission_slug)
    if mid8:
        return mid8
    # Cascade exhausted: no declared source carries the disambiguator. Fail
    # closed rather than fabricate a wrong-but-plausible mid8 (FR-005 / F-001).
    raise StatusReadPathNotFound(
        repo_root=repo_root,
        mission_slug=mission_slug,
        mid8="",
        coord_candidate=CoordinationWorkspace.worktree_path(
            repo_root, mission_slug, ""
        )
        / KITTY_SPECS_DIR
        / mission_slug,
        primary_candidate=repo_root / KITTY_SPECS_DIR / mission_slug,
    )


def resolve_status_surface(repo_root: Path, mission_slug: str) -> Path:
    """Return the canonical status.events.jsonl path for the given mission.

    Thin wrapper over :func:`resolve_status_surface_with_anchor` that discards
    the carried primary anchor. Retained as the canonical surface-path accessor;
    consumers that also need the CWD-invariant primary anchor (transaction
    identity, #1737) should call :func:`resolve_status_surface_with_anchor`
    instead of re-deriving it.

    Raises FileNotFoundError when meta.json is absent.
    Raises ValueError when meta.json is malformed.
    """
    return resolve_status_surface_with_anchor(repo_root, mission_slug).surface_path


def resolve_status_surface_with_anchor(
    repo_root: Path, mission_slug: str
) -> ResolvedStatusSurface:
    """Resolve the canonical status surface and primary anchor in one pass.

    Resolution is single-pass (FR-036): :func:`candidate_feature_dir_for_mission`
    — the coord-aware primitive that ``MissionStatus`` is also built on — is
    invoked **exactly once** and its result is carried as ``primary_anchor``.
    The surface path is derived from that same resolution:

    1. If the resolved dir is already inside a ``.worktrees/<m>-coord`` root, it
       is final — the surface lives there (never re-resolve; the #1772 nesting
       bug).
    2. Otherwise the resolver landed in the primary checkout. When that mission
       declares ``coordination_branch`` but the coord worktree is not yet
       materialized, compose the coord path **directly** (one derivation, via
       WP01's :func:`coord_feature_dir`). When the coord worktree root *is*
       materialized but lacks the mission dir (the coord-empty state), apply
       Option B: return the PRIMARY checkout surface and emit a single loud
       ``logging.WARNING`` (:data:`_COORD_EMPTY_FALLBACK_WARNING`) naming the
       stale-surface risk and both recovery paths (#1716 / FR-001 / FR-003). The
       coord-state decision routes through WP01's :func:`probe_coord_state`
       (adopted, not re-derived); the ``CoordState.DELETED`` case still hard-fails
       (:class:`CoordinationBranchDeleted`, #1848).

    Raises FileNotFoundError when meta.json is absent.
    Raises ValueError when meta.json is malformed.
    Raises CoordinationBranchDeleted when the coord worktree is absent AND the
        declared coordination branch has been deleted from git (#1848 data-loss
        carve-out — never a silent fallback).
    Raises StatusReadPathNotFound when the coord-worktree mid8 cannot be derived
        from any declared source (fail closed — never fabricate a mid8).
    """
    try:
        feature_dir: Path = candidate_feature_dir_for_mission(repo_root, mission_slug)
    except StatusReadPathNotFound as exc:
        # Option B (#1716 / FR-001 / FR-003): for the ``<slug>-<mid8>`` handle the
        # canonicalizer derives mid8 from the slug, so a coord-empty topology fails
        # closed HERE (``_resolve_not_found``) before the topology branch below runs
        # — unlike the bare-slug handle, which canonicalizes to primary and reaches
        # the branch directly. Recover by re-anchoring on the fail-closed
        # diagnostic's primary candidate (the primary checkout carries meta.json);
        # the loud coord-empty fallback then fires uniformly for BOTH handle forms.
        # Any non-coord-empty fail-closed (e.g. a genuinely missing mission) keeps
        # propagating, so the not-found behaviour for unresolvable handles is
        # unchanged.
        feature_dir = exc.primary_candidate
    # F-001: the candidate resolution above is the single canonicalization
    # point — a mid8 / ULID / numeric-prefix handle lands on the real mission
    # directory, whose NAME is the canonical mission-dir name. Every downstream
    # composition (the primary re-anchor, the coord-path assembly) consumes
    # that canonical name; re-anchoring on the raw operator handle is exactly
    # the wrong-but-plausible ``kitty-specs/<mid8>/`` surface this resolver
    # must never hand back. (For unresolvable handles the candidate's name
    # equals the raw handle, so the not-found behaviour is unchanged.)
    mission_slug = feature_dir.name
    meta = load_meta(feature_dir)

    # If the single coord-aware resolution already landed inside a coord
    # worktree that carries its own meta, it is final — never resolve again (the
    # #1772 nesting bug).
    if meta is not None and any(
        part == _WORKTREES_SEGMENT for part in feature_dir.parts
    ):
        return ResolvedStatusSurface(
            surface_path=feature_dir / _STATUS_EVENTS_FILENAME,
            primary_anchor=feature_dir,
        )

    # FR-003 cascade layer 1: config must be readable BEFORE topology can be
    # resolved. ``coordination_branch`` lives in the PRIMARY-checkout meta.json;
    # the coord worktree's mission dir has none. When ``candidate_feature_dir``
    # prefers a materialized coord worktree, ``load_meta`` above silently
    # returns None and the resolver historically handed back the coord path as
    # ``primary_anchor`` with no coord/primary distinction — losing the config
    # signal and flipping topology classification (the #1589/#1821 split-brain
    # the write path then inherits via ``_identity_for_request``). Re-anchor the
    # config read on the canonical primary dir so the surface authority is
    # config-determined, never topology-determined-then-config-lost.
    primary_dir: Path = primary_feature_dir_for_mission(repo_root, mission_slug)
    if meta is None:
        meta = load_meta(primary_dir)
    if meta is None:
        if primary_dir.exists():
            return ResolvedStatusSurface(
                surface_path=primary_dir / _STATUS_EVENTS_FILENAME,
                primary_anchor=primary_dir,
            )
        if feature_dir.exists():
            return ResolvedStatusSurface(
                surface_path=feature_dir / _STATUS_EVENTS_FILENAME,
                primary_anchor=feature_dir,
            )
        raise FileNotFoundError(
            f"meta.json not found for mission {mission_slug!r} at {feature_dir}"
        )

    # Config is now in hand. The canonical primary anchor is the topology-blind
    # primary dir (the create→first-write window authority the transaction
    # identity logic expects), not the coord-preferring candidate.
    feature_dir = primary_dir

    raw_coord = meta.get("coordination_branch")
    coord_branch: str | None = str(raw_coord) if raw_coord else None
    if coord_branch is None:
        return ResolvedStatusSurface(
            surface_path=feature_dir / _STATUS_EVENTS_FILENAME,
            primary_anchor=feature_dir,
        )

    # Coord branch declared: classify the coord-worktree topology state via WP01's
    # shared probe (paula C2) — never re-derive the root/mission-dir/branch checks
    # inline. The composed coord feature dir is built once via WP01's
    # ``coord_feature_dir`` (paula C1, single grammar). The primary anchor stays
    # the canonical primary candidate (the create→first-write window authority the
    # transaction-identity logic expects).
    mid8: str = _coord_mid8(meta, mission_slug, repo_root)
    composed_coord_dir: Path = coord_feature_dir(repo_root, mission_slug, mid8)
    coord_state = probe_coord_state(
        repo_root, mission_slug, mid8, coordination_branch=coord_branch
    )

    # #1889 row R3 / #1848: the coord worktree is absent AND the declared
    # coordination branch has been DELETED from git. A deleted coord branch with
    # unmerged status is data loss, not a degraded read — fail closed LOUDLY with
    # a distinct, actionable error rather than silently composing a coord path or
    # falling back to primary (FR-005 / FR-008). This stays a hard-fail (WP05).
    if coord_state is CoordState.DELETED:
        raise CoordinationBranchDeleted(
            repo_root=repo_root,
            mission_slug=mission_slug,
            mid8=mid8,
            coordination_branch=coord_branch,
            coord_candidate=composed_coord_dir,
            primary_candidate=feature_dir,
        )
    # Option B loud primary fallback (FR-001 / FR-003 / #1716): the coord worktree
    # root is materialized but its mission dir is absent (coord-empty). Reading the
    # primary checkout may expose a stale, split-brain status surface (#1589/#1821),
    # so emit a single loud ``logging.WARNING`` naming the risk AND both recovery
    # paths (flatten OR `spec-kitty agent worktree repair`) — making the fallback
    # observable so an operator/orchestrating agent can intervene — then return the
    # PRIMARY surface and proceed. Before materialization (``UNMATERIALIZED``) the
    # composed coord path is returned as-is; the create→first-write window keeps the
    # primary checkout authoritative one level up (the aggregate's not-yet-
    # materialized gate).
    if coord_state is CoordState.EMPTY:
        logger.warning(
            _COORD_EMPTY_FALLBACK_WARNING,
            {"slug": mission_slug, "coord_root": composed_coord_dir.parent.parent},
        )
        return ResolvedStatusSurface(
            surface_path=feature_dir / _STATUS_EVENTS_FILENAME,
            primary_anchor=feature_dir,
        )
    return ResolvedStatusSurface(
        surface_path=composed_coord_dir / _STATUS_EVENTS_FILENAME,
        primary_anchor=feature_dir,
    )
