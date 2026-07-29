"""Write-seam adoption helper (FR-007 core; FR-011 zero-write refusal; FR-012).

Not a new write resolver (ADR ``2026-06-24-1`` C-006 forbids a second one) --
this module composes the existing write authority
(:func:`mission_runtime.placement_seam` -> :meth:`~mission_runtime.PlacementSeam
.write_target`) with the existing commit materialiser
(:func:`~specify_cli.coordination.commit_router.commit_for_mission`) into ONE
reusable helper that the TRUE write-side bypasses
(``kitty-specs/write-side-seam-matrix-tracer-01KYP3MH/contracts/write-seam-
adoption.md``) converge onto. It never routes the seam's own engine
(``commit_router`` internals, ``write_target_degrade``, the
``status_transition:300`` FR-006 mirror, merge infra) -- doing so would be
circular.

FR-011 (zero-write refusal): when the seam cannot resolve a routable
destination for ``kind`` (missing coord surface, a deleted ``target_branch``,
or any other unroutable-mission condition), :func:`write_artifact` refuses --
it NEVER falls back to a hand-picked ref (e.g. ``main``), and it NEVER writes
anything. This mirrors -- but deliberately does NOT repeat -- the defect
latent in ``mission_runtime.write_target_degrade.resolve_write_target_or_
degrade``: that helper's ``degrade_ref`` fallback exists to serve callers
that explicitly opt into a fail-open policy (writing straight to a caller-
supplied ref on an unresolvable mission); THIS helper's callers never opt
into that -- an unroutable target is always a structured, recoverable
REFUSAL that discloses the deferred #3033 ``CONSOLIDATED``-surface decision,
never a silent (or loud) write to the wrong place, and never a consolidation
abort (``2026-07-23-2``).

FR-012 (idempotent, structured result): re-invoking with identical inputs is
a no-op. This is inherited directly from ``commit_for_mission``'s own
idempotence contract (a byte-identical artifact already committed at the
resolved placement returns ``"unchanged"``, never a duplicate empty commit)
-- this helper does not re-implement that logic, it only projects the
outcome into :class:`WriteSeamResult`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

from mission_runtime import ActionContextError, MissionArtifactKind, placement_seam
from specify_cli.coordination.commit_router import CommitRouterResult, commit_for_mission
from specify_cli.missions._read_path_resolver import StatusReadPathNotFound

# The exact caught set mission_runtime.write_target_degrade.resolve_write_target_or_degrade
# already established as "a genuine mission-resolution failure" (never a bare
# ``except Exception`` -- an unrelated bug surfacing inside the seam must still
# raise loudly, not be swallowed into a refusal). ``StatusReadPathNotFound``
# covers its subclass ``CoordinationBranchDeleted`` (a deleted coord branch),
# the literal FR-011 scenario named in the WP context.
_UNROUTABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    ActionContextError,
    StatusReadPathNotFound,
    FileNotFoundError,
)

_REFUSAL_DIAGNOSTIC_TEMPLATE = (
    "write_seam: refusing a zero-write on an unroutable target for mission "
    "{mission_slug!r} (kind={kind_value!r}); this is the deferred #3033 "
    "CONSOLIDATED-surface decision -- no fallback write, no consolidation "
    "abort. Original resolution failure: {cause}"
)

_STATUS_REFUSED: Literal["refused"] = "refused"


@runtime_checkable
class ProtectionPolicyLike(Protocol):
    """Structural protocol for the ``ProtectionPolicy`` duck-type this helper
    threads straight through to ``commit_for_mission``.

    Mirrors ``commit_router._ProtectionPolicyProtocol`` locally (rather than
    importing that private name across the module boundary) for the same
    reason it exists there: avoiding a hard import cycle while matching on
    structure, not on the concrete class.
    """

    def is_protected(self, ref: str) -> bool: ...


@dataclass(frozen=True)
class WriteSeamResult:
    """Structured, typed outcome of :func:`write_artifact` (FR-012).

    ``status`` mirrors :class:`~specify_cli.coordination.commit_router.
    CommitRouterResult` for the routed outcomes (``"committed"`` /
    ``"unchanged"`` / ``"no_op_wrong_surface"`` / ``"error"``), plus the
    FR-011 zero-write ``"refused"`` outcome this helper adds on top -- the
    ONE outcome ``commit_for_mission`` itself can never produce, because
    reaching ``"refused"`` means resolution never got far enough to call it.

    ``entry_id`` names the logical row/entry this write represents (e.g. an
    issue number, a WP id) so a caller can log/report which write an outcome
    belongs to without re-threading its own bookkeeping. ``destination_surface``
    is the resolved placement ref on every non-refused outcome, and ``None``
    on ``"refused"`` (there is no destination -- nothing was resolved).
    """

    status: Literal["committed", "unchanged", "no_op_wrong_surface", "error", "refused"]
    entry_id: str
    destination_surface: str | None
    commit_hash: str | None = None
    diagnostic: str | None = None


def _probe_write_target(
    repo_root: Path, mission_slug: str, kind: MissionArtifactKind
) -> Exception | None:
    """Probe routability via the seam; return the caught exception, or ``None``.

    A THIN probe -- it resolves via :meth:`~mission_runtime.PlacementSeam.
    write_target` (the same authority ``commit_for_mission`` itself calls
    internally) purely to detect an unroutable target BEFORE any write is
    attempted. It never inspects or reuses the resolved value: on success the
    caller proceeds straight to ``commit_for_mission``, which resolves again
    internally (C-006 -- this is the one seam, consulted twice for two
    different purposes: refusal detection and materialisation).
    """
    try:
        placement_seam(repo_root, mission_slug).write_target(kind)
    except _UNROUTABLE_EXCEPTIONS as exc:
        return exc
    return None


def write_artifact(
    *,
    repo_root: Path,
    mission_slug: str,
    kind: MissionArtifactKind,
    files: tuple[Path, ...],
    message: str,
    policy: ProtectionPolicyLike,
    entry_id: str,
    target_branch: str | None = None,
    primary_paths_created_this_invocation: frozenset[Path] | None = None,
) -> WriteSeamResult:
    """Write mission artifact ``files`` of ``kind`` through the ONE write seam.

    Resolves the destination via :meth:`~mission_runtime.PlacementSeam.
    write_target` and, when routable, materialises via
    :func:`~specify_cli.coordination.commit_router.commit_for_mission`. An
    unroutable target (missing coord surface, deleted ``target_branch``, or
    any other mission-resolution failure) is refused with a zero-write,
    structured result (FR-011) -- see the module docstring.

    Args:
        repo_root: Primary checkout root.
        mission_slug: Mission handle.
        kind: The :class:`~mission_runtime.MissionArtifactKind` being written.
        files: Absolute paths of artifacts to commit (mirrors
            ``commit_for_mission``'s own contract).
        message: Commit message.
        policy: A duck-typed ``is_protected(ref) -> bool`` policy object.
        entry_id: Caller-supplied identifier for the row/entry being written.
        target_branch: Optional short primary-branch name for the post-commit
            ff-advance (threaded straight through to ``commit_for_mission``).
        primary_paths_created_this_invocation: Threaded straight through to
            ``commit_for_mission`` (coord-residue cleanup eligibility, R6).

    Returns:
        A :class:`WriteSeamResult`.
    """
    unroutable = _probe_write_target(repo_root, mission_slug, kind)
    if unroutable is not None:
        return WriteSeamResult(
            status=_STATUS_REFUSED,
            entry_id=entry_id,
            destination_surface=None,
            diagnostic=_REFUSAL_DIAGNOSTIC_TEMPLATE.format(
                mission_slug=mission_slug, kind_value=kind.value, cause=unroutable
            ),
        )

    result: CommitRouterResult = commit_for_mission(
        repo_root,
        mission_slug,
        files,
        message,
        policy,
        kind=kind,
        primary_paths_created_this_invocation=primary_paths_created_this_invocation,
        target_branch=target_branch,
    )
    return WriteSeamResult(
        status=result.status,
        entry_id=entry_id,
        destination_surface=result.placement_ref,
        commit_hash=result.commit_hash,
        diagnostic=result.diagnostic,
    )
